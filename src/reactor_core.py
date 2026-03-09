"""
reactor_core.py — TEKNOFEST Nükleer Enerji Simülasyonu Reaktör Çekirdeği
=========================================================================
SMR/iPWR reaktörü için ana kontrol ve durum yönetimi modülü.

Özellikler:
  • Fizik motoruyla entegre nokta kinetiği simülasyonu
  • Çok kademeli güvenlik sistemi (uyarı → yüksek alarm → SCRAM)
  • Yakıt tükenmesi (burnup) takibi
  • Reaktör güç geçmişi (time-series) kaydı
  • Kapsamlı JSON tabanlı konfigürasyon
  • Context manager desteği
"""

import random
import json
import os
import logging
import math
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

# Otomasyon ve Veritabanı
from automation import PIDController
from database import ReactorDatabase

# Göreli içe aktarma yerine doğrudan modül
try:
    from physics import ReactorPhysics
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from physics import ReactorPhysics


# ─── Veri Sınıfları ──────────────────────────────────────────────────────────

@dataclass
class ReactorState:
    """Anlık reaktör durumunu taşıyan değer nesnesi (immutable snapshot)."""
    timestamp:        float = 0.0
    temperature_k:    float = 563.0
    pressure_bar:     float = 155.0
    neutron_flux:     float = 3.0e13
    power_mwth:       float = 0.0
    control_rod_pos:  float = 60.0
    coolant_flow_pct: float = 80.0
    fuel_temp_k:      float = 563.0
    xenon_conc:       float = 0.0
    samarium_conc:    float = 0.0
    burnup_mwdmt:     float = 0.0
    reactivity_pcm:   float = 0.0
    scram_active:     bool  = False
    alarm_level:      int   = 0   # 0=Normal, 1=Uyarı, 2=Yüksek Alarm, 3=SCRAM

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReactorEvent:
    """Olay kaydı — tarih, tip ve mesaj."""
    timestamp_iso: str
    elapsed_s:     float
    level:         str    # INFO / WARNING / ALARM / CRITICAL
    message: str


class Telemetry:
    """Reaktör verilerini tamponlayan ve analiz eden sınıf."""
    def __init__(self, max_points: int = 1000):
        self.data: list[ReactorState] = []
        self.max_points = max_points

    def record(self, state: ReactorState):
        self.data.append(state)
        if len(self.data) > self.max_points:
            self.data.pop(0)

    def get_trend(self, key: str) -> list[float]:
        """Belirli bir parametrenin (örn. 'temperature_k') geçmişini döndürür."""
        return [getattr(s, key) for s in self.data if hasattr(s, key)]

    def average(self, key: str) -> float:
        trend = self.get_trend(key)
        return sum(trend) / len(trend) if trend else 0.0


# ─── Alarm Seviyeleri ─────────────────────────────────────────────────────────

class AlarmLevel:
    NORMAL  = 0
    WARNING = 1
    HIGH    = 2
    SCRAM   = 3


# ─── Ana Sınıf ───────────────────────────────────────────────────────────────

class ReactorCore:
    """
    Reaktör çekirdeği kontrol ve simülasyon sınıfı.

    Kullanım:
        reactor = ReactorCore("config.json")
        reactor.initialize_steady_state()
        for _ in range(3600):
            reactor.step(dt=1.0)
        print(reactor.get_status())
    """

    DEFAULT_CONFIG = {
        "reactor_name":     "TEKNOFEST-TX1",
        "reactor_type":     "SMR-iPWR",
        "design_power_mwth": 150.0,
        "initial_state": {
            "temperature":     563.0,
            "pressure":        155.0,
            "neutron_flux":    3.0e13,
            "control_rod_pos": 50,
            "coolant_flow":    80.0,
            "burnup_mwdmt":    0.0
        },
        "thresholds": {
            "max_temp":        750.0,
            "scram_temp":      800.0,
            "critical_temp":   900.0,
            "max_pressure":    175.0,
            "scram_pressure":  180.0,
            "min_coolant_flow": 10.0,
            "max_power_mw":    300.0
        },
        "fuel": {
            "initial_heavy_metal_kg": 2000.0,
            "max_burnup_mwdmt": 55000.0
        },
        "simulation": {
            "dt": 1.0,
            "noise_flux_amplitude": 1.0e9,
            "noise_temp_amplitude": 0.05
        }
    }

    # ─── Başlatma ──────────────────────────────────────────────────────────

    def __init__(self, config_path: str = "config.json"):
        self._start_time = datetime.now()
        self._elapsed_s  = 0.0
        self._step_count = 0
        self._events: list[ReactorEvent] = []
        self._history: list[ReactorState] = []
        self._history_max = 86400   # 24 saatlik veri saklama (saniye başına)

        self.config = self._load_config(config_path)
        cfg_state   = self.config["initial_state"]
        cfg_thresh  = self.config["thresholds"]
        cfg_sim     = self.config.get("simulation", {})
        cfg_fuel    = self.config.get("fuel", {})

        # Durum değişkenleri (2-Düğümlü TH)
        self.coolant_temp     = float(cfg_state["temperature"])
        self.fuel_temp        = float(cfg_state["temperature"])
        self.temperature      = self.coolant_temp # Geriye dönük uyumluluk
        self.pressure         = float(cfg_state["pressure"])
        self.neutron_flux     = float(cfg_state["neutron_flux"])
        self.control_rod_pos  = float(cfg_state["control_rod_pos"])
        self.coolant_flow     = float(cfg_state.get("coolant_flow", 80.0))
        self.burnup_mwdmt     = float(cfg_state.get("burnup_mwdmt", 0.0))
        self.power_mwth       = 0.0
        self.scram_active     = False
        self.alarm_level      = AlarmLevel.NORMAL
        self.scram_reason     = ""

        # Eşik değerleri
        self.max_temp         = float(cfg_thresh["max_temp"])
        self.scram_temp       = float(cfg_thresh.get("scram_temp", 800.0))
        self.critical_temp    = float(cfg_thresh["critical_temp"])
        self.max_pressure     = float(cfg_thresh["max_pressure"])
        self.scram_pressure   = float(cfg_thresh.get("scram_pressure", self.max_pressure * 1.1))
        self.max_power        = float(cfg_thresh.get("max_power_mw", 300.0))

        # Yakıt parametreleri
        self._fuel_mass_kg    = float(cfg_fuel.get("initial_heavy_metal_kg", 2000.0))
        self._max_burnup      = float(cfg_fuel.get("max_burnup_mwdmt", 55000.0))

        # Gürültü parametreleri
        self._noise_flux      = float(cfg_sim.get("noise_flux_amplitude", 1.0e9))
        self._noise_temp      = float(cfg_sim.get("noise_temp_amplitude", 0.05))

        # Fizik motoru
        self.physics = ReactorPhysics()

        # Telemetri
        self.telemetry = Telemetry(max_points=self._history_max)

        # Doğrulama
        self._validate_config()

        # Otomasyon (PID) — Güç kontrolü için
        # Parametreler: Kp, Ki, Kd, Setpoint (MWth)
        design_mwth = float(self.config.get("design_power_mwth", 150.0))
        self.pid = PIDController(Kp=0.5, Ki=0.1, Kd=0.05, setpoint=design_mwth)
        self.auto_pilot = False

        # Veritabanı
        self.db = ReactorDatabase()

        # Logger
        self._setup_logger()
        self._log(logging.INFO, f"Reaktör başlatıldı: {self.config['reactor_name']}")

    def _validate_config(self):
        """Konfigürasyonun bütünlüğünü kontrol eder."""
        required_keys = ["reactor_name", "initial_state", "thresholds"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Eksik konfigürasyon anahtar²: {key}")
        
        state_keys = ["temperature", "pressure", "neutron_flux", "control_rod_pos"]
        for key in state_keys:
            if key not in self.config["initial_state"]:
                raise ValueError(f"Eksik initial_state anahtar²: {key}")

    def _load_config(self, path: str) -> dict:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fp:
                return json.load(fp)
        self._log_fallback(f"Konfigürasyon bulunamadı: {path} — varsayılanlar kullanılıyor.")
        return dict(self.DEFAULT_CONFIG)

    def _setup_logger(self):
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "reactor.log")

        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _log(self, level: int, msg: str):
        self.logger.log(level, msg)
        level_str = logging.getLevelName(level)
        self._events.append(ReactorEvent(
            timestamp_iso=datetime.now().isoformat(timespec="seconds"),
            elapsed_s=self._elapsed_s,
            level=level_str,
            message=msg
        ))

    @staticmethod
    def _log_fallback(msg: str):
        print(f"[ReactorCore] {msg}")

    # ─── İlk Koşul Başlatma ────────────────────────────────────────────────

    def initialize_steady_state(self):
        """
        Reaktörü tam güçte ve kimyasal/nötronik dengedeki başlangıç durumuna koyar.
        Xe-135/Sm-149 ve Termal-Hidrolik (Fuel-Coolant deltaT) dengelerini hesaplar.
        Kontrol çubuklarını kritik konuma ayarlar (ρ_tot ≈ 0).
        """
        self.physics.initialize_steady_state(self.neutron_flux)
        design_mwth = float(self.config.get("design_power_mwth", 150.0))
        self.power_mwth = design_mwth

        # Termal denge: Q = HA * (Tf - Tc) => Tf = Tc + Q/HA
        q_watts = self.power_mwth * 1.0e6
        ha = self.physics.thermo.HA_CORE
        self.fuel_temp = self.coolant_temp + (q_watts / ha)

        # Kontrol çubuğu kritik konumu bul (binary search, ρ_tot = 0)
        # Önce Xe+Sm+burnup+temp poisons'larını hesapla 
        rho_xe_eq = self.physics.xenon.step(self.neutron_flux, 1e-9)
        rho_sm_eq = self.physics.samarium.step(self.neutron_flux, 1e-9)
        rho_temp = (self.physics.ALPHA_DOPPLER * (self.fuel_temp - 563.0)
                    + self.physics.ALPHA_MODERATOR * (self.coolant_temp - 563.0))
        rho_burnup = -(self.burnup_mwdmt / 55000.0) * 0.05
        rho_poison = rho_xe_eq + rho_sm_eq + rho_temp + rho_burnup

        # Çözüm: rho_rod = -rho_poison  =>  rod_worth * (rod_factor - 0.5) = -rho_poison
        import math
        rod_worth_total = 0.12
        target_rod_factor = 0.5 + (-rho_poison / rod_worth_total)
        # Kısıt: rod_factor = sin(pi*f)*0.4 + f*0.6, f=rod_pos/100 in [0,1]
        # Newton-Raphson ile kritik rod_pos bul
        f = 0.5  # başlangıç tahmini
        for _ in range(30):
            ff = math.sin(math.pi * f) * 0.4 + f * 0.6
            dfdf = math.pi * math.cos(math.pi * f) * 0.4 + 0.6
            delta = (ff - target_rod_factor) / max(1e-10, dfdf)
            f -= delta
            f = max(0.0, min(1.0, f))
            if abs(delta) < 1e-8:
                break
        self.control_rod_pos = f * 100.0

        self._log(logging.INFO,
                  f"Steady-state başlatıldı. Krit. çubuk: {self.control_rod_pos:.1f}% "
                  f"Tf={self.fuel_temp:.1f}K Tc={self.coolant_temp:.1f}K")

    # ─── Kontrol Arayüzleri ───────────────────────────────────────────────

    def update_control_rods(self, position: float):
        """Kontrol çubuğu konumunu güncelle. [0-100]%"""
        if self.scram_active:
            self._log(logging.WARNING, "SCRAM aktif — çubuk hareketi engellendi.")
            return
        old_pos = self.control_rod_pos
        self.control_rod_pos = max(0.0, min(100.0, float(position)))
        self._log(logging.INFO,
                  f"Kontrol çubukları: {old_pos:.1f}% → {self.control_rod_pos:.1f}%")

    def update_coolant_flow(self, flow_percent: float):
        """Soğutucu akış hızını güncelle. [0-100]%"""
        self.coolant_flow = max(0.0, min(100.0, float(flow_percent)))
        self._log(logging.INFO, f"Soğutucu akış: {self.coolant_flow:.1f}%")

    def borate(self, delta_rho: float = 0.02):
        """
        Acil borlama — reaktiviteyi anlık olarak azaltır.
        delta_rho: Azaltılacak reaktivite miktarı (pozitif = reaktivite azaltma)
        """
        # Bor etkisi kontrol çubuklarına eşdeğer reaktivite açısından simüle edilir
        effective_rod_change = delta_rho * 1000.0
        new_pos = max(0.0, self.control_rod_pos - effective_rod_change)
        self.control_rod_pos = new_pos
        self._log(logging.WARNING,
                  f"ACİL BORLAMA uygulandı: Δρ = -{delta_rho*1e5:.0f} pcm")

    # ─── Zaman Adımı ─────────────────────────────────────────────────────

    def step(self, dt: float = 1.0):
        """
        Reaktörü dt saniye ilerlet.
        Sırasıyla: reaktivite → nötron akısı → güç → ısı → basınç → güvenlik.
        """
        if self.scram_active:
            # SCRAM sonrası atım ısısı sönümlemesi
            self._scram_decay_heat(dt)
            return

        self._step_count += 1
        self._elapsed_s  += dt

        # 1. Reaktivite
        rho = self.physics.calculate_reactivity(
            self.control_rod_pos,
            self.fuel_temp,
            self.coolant_temp,
            self.neutron_flux,
            dt,
            burnup=self.burnup_mwdmt
        )

        # 2. Nötron akısı (nokta kinetiği üzerinden)
        new_flux = self.physics.kinetics.step(self.neutron_flux, rho, dt)
        noise    = random.gauss(0, self._noise_flux)
        self.neutron_flux = max(1.0e6, new_flux + noise)

        # 3. Termal güç (akı → güç dönüşümü)
        design_flux    = 3.0e13
        design_mwth    = float(self.config.get("design_power_mwth", 150.0))
        self.power_mwth = (self.neutron_flux / design_flux) * design_mwth
        self.power_mwth = max(0.0, min(self.power_mwth, self.max_power * 1.2))

        # 4. PID Otomasyon (Auto-Pilot aktifse)
        if self.auto_pilot and not self.scram_active:
            adjustment = self.pid.compute(self.power_mwth, dt)
            # Çıktı rod pozisyonuna eklenir (0-100 arasına çekilir)
            self.control_rod_pos = max(0.0, min(100.0, self.control_rod_pos + adjustment))

        # 5. Sıcaklık — 2-Düğümlü Isı Dengesi
        self.fuel_temp, self.coolant_temp = self.physics.thermo.fuel_and_coolant_dynamic(
            self.fuel_temp, self.coolant_temp, self.power_mwth, dt
        )
        self.temperature = self.coolant_temp # Uyumluluk

        # 6. Basınç — ideal gaz yaklaşımı (P ∝ T_cool)
        T_ref          = self.config["initial_state"]["pressure"]
        self.pressure  = (self.coolant_temp / self.config["initial_state"]["temperature"]) \
                         * T_ref + random.gauss(0, 0.05)

        # 6. Burnup güncelleme (gün bazlı)
        dt_days           = dt / 86400.0
        mass_mt           = self._fuel_mass_kg / 1000.0
        self.burnup_mwdmt += (self.power_mwth * dt_days) / mass_mt

        # 7. Güvenlik kontrolleri
        self._safety_check()

        # 8. Anlık durum geçmişe ekle
        self._append_history()

    def _scram_decay_heat(self, dt: float):
        """SCRAM sonrası atım ısısı — ANS-5.1 azalma eğrisi (basitleştirilmiş)."""
        decay_fraction = 0.065 * (self._elapsed_s + 1.0) ** (-0.2)
        decay_power    = float(self.config.get("design_power_mwth", 150.0)) * decay_fraction
        # Pasif soğutma
        passive_cap    = 15.0  # MW — pasif soğutma kapasitesi
        net_heat       = max(0.0, decay_power - passive_cap)
        self.fuel_temp += net_heat * dt * 0.01
        self.coolant_temp += (self.fuel_temp - self.coolant_temp) * 0.01 * dt # Basit transfer
        self.temperature = self.coolant_temp
        self._elapsed_s  += dt

    # ─── Güvenlik Sistemi ─────────────────────────────────────────────────

    def _safety_check(self):
        """Çok kademeli alarm ve SCRAM mantığı."""
        # Sıcaklık alarmları
        if self.temperature > self.critical_temp:
            self.emergency_shutdown("KRİTİK SICAKLIK AŞILDI")
        elif self.temperature > self.scram_temp:
            self.emergency_shutdown("SCRAM SICAKLIK SINIRI")
        elif self.temperature > self.max_temp:
            self._raise_alarm(AlarmLevel.HIGH, f"Yüksek sıcaklık alarmı: {self.temperature:.1f} K")
        elif self.temperature > self.max_temp * 0.95:
            self._raise_alarm(AlarmLevel.WARNING, f"Sıcaklık uyarısı: {self.temperature:.1f} K")

        # Basınç alarmları
        if self.pressure > self.scram_pressure:
            self.emergency_shutdown("AŞIRI BASINÇ — SCRAM")
        elif self.pressure > self.max_pressure:
            self._raise_alarm(AlarmLevel.HIGH, f"Yüksek basınç alarmı: {self.pressure:.1f} bar")

        # Güç alarmı
        if self.power_mwth > self.max_power:
            self._raise_alarm(AlarmLevel.HIGH,
                              f"Aşırı güç: {self.power_mwth:.1f} MWth > {self.max_power} MWth")

        # Soğutucu kaybı
        if self.coolant_flow < self.config["thresholds"].get("min_coolant_flow", 10.0):
            self._raise_alarm(AlarmLevel.HIGH, f"Soğutucu akışı düşük: {self.coolant_flow:.1f}%")

        # Yakıt ömrü
        if self.burnup_mwdmt > self._max_burnup * 0.95:
            self._raise_alarm(AlarmLevel.WARNING,
                              f"Yakıt ömrü kritik: {self.burnup_mwdmt:.0f} MWd/MTU")

        # Xe-pit uyarısı
        if self.physics.xe_reactivity_pcm < self.config.get(
                "thresholds", {}).get("xe_pit_threshold_pcm", -3000.0):
            self._raise_alarm(AlarmLevel.WARNING,
                              f"Xenon-pit bölgesi: {self.physics.xe_reactivity_pcm:.0f} pcm")

        # Normal durum sıfırlama
        if (self.alarm_level < AlarmLevel.HIGH
                and self.temperature < self.max_temp * 0.9
                and self.pressure < self.max_pressure * 0.9):
            self.alarm_level = AlarmLevel.NORMAL

    def _raise_alarm(self, level: int, msg: str):
        if level > self.alarm_level:
            self.alarm_level = level
            log_level = logging.WARNING if level <= AlarmLevel.HIGH else logging.CRITICAL
            self._log(log_level, f"[ALARM L{level}] {msg}")
            try:
                print(f"\n[⚠️  ALARM L{level}] {msg}")
            except UnicodeEncodeError:
                print(f"\n[! ALARM L{level}] {msg}")

    def emergency_shutdown(self, reason: str = "MANUAL SCRAM"):
        """SCRAM — çubukları tam içeri it, soğutucuyu maksimuma çek."""
        if not self.scram_active:
            self.scram_active    = True
            self.scram_reason    = reason
            self.alarm_level     = AlarmLevel.SCRAM
            self.control_rod_pos = 0.0
            self.coolant_flow    = 100.0
            self._log(logging.CRITICAL, f"☢️  SCRAM AKTİF: {reason}")
            try:
                print(f"\n[🚨 SCRAM] {reason}")
            except UnicodeEncodeError:
                print(f"\n[!!! SCRAM] {reason}")

    def reset_scram(self, authorized: bool = False):
        """SCRAM sıfırlama — yalnızca yetkili personel."""
        if not authorized:
            raise PermissionError("SCRAM sıfırlaması yetkili personel gerektirir.")
        if self.temperature < self.max_temp * 0.7 and self.pressure < self.max_pressure * 0.7:
            self.scram_active = False
            self.alarm_level  = AlarmLevel.NORMAL
            self.scram_reason = ""
            self._log(logging.INFO, "SCRAM sıfırlandı — kontrol yetkiliye devredildi.")
        else:
            raise RuntimeError("Reaktif güvenli aralığa çekilmeden SCRAM sıfırlanamaz.")

    # ─── Geçmiş ve Durum ──────────────────────────────────────────────────

    def _append_history(self):
        snap = ReactorState(
            timestamp        = self._elapsed_s,
            temperature_k    = self.temperature,
            pressure_bar     = self.pressure,
            neutron_flux     = self.neutron_flux,
            power_mwth       = self.power_mwth,
            control_rod_pos  = self.control_rod_pos,
            coolant_flow_pct = self.coolant_flow,
            fuel_temp_k      = self.fuel_temp,
            xenon_conc       = self.physics.xenon_conc,
            samarium_conc    = self.physics.samarium.samarium,
            burnup_mwdmt     = self.burnup_mwdmt,
            reactivity_pcm   = self.physics.xe_reactivity_pcm + self.physics.sm_reactivity_pcm,
            scram_active     = self.scram_active,
            alarm_level      = self.alarm_level,
        )
        self._history.append(snap)
        self.telemetry.record(snap)
        
        # Veritabanına kaydet (her 10 adımda bir veya önemli olayda)
        if self._step_count % 10 == 0:
            self.db.save_state(snap)
        if len(self._history) > self._history_max:
            self._history.pop(0)

    def get_status(self) -> dict:
        """Mevcut reaktör durumunu okunabilir sözlük olarak döndür."""
        return {
            "reaktör":         self.config["reactor_name"],
            "süre_s":          f"{self._elapsed_s:.1f}",
            "sıcaklık_yakıt":  f"{self.fuel_temp:.2f} K",
            "sıcaklık_soğutucu": f"{self.coolant_temp:.2f} K",
            "sıcaklık":        f"{self.coolant_temp:.2f} K ({self.coolant_temp - 273.15:.1f} °C)",
            "basınç":          f"{self.pressure:.2f} bar",
            "nötron_akısı":    f"{self.neutron_flux:.3e} n/cm²·s",
            "güç":             f"{self.power_mwth:.2f} MWth",
            "kontrol_çubukları": f"{self.control_rod_pos:.1f}%",
            "soğutucu_akış":   f"{self.coolant_flow:.1f}%",
            "xe135_pcm":       f"{self.physics.xe_reactivity_pcm:.1f} pcm",
            "sm149_pcm":       f"{self.physics.sm_reactivity_pcm:.1f} pcm",
            "burnup":          f"{self.burnup_mwdmt:.1f} MWd/MTU",
            "alarm_seviyesi":  self.alarm_level,
            "scram":           "AKTİF ⚠️" if self.scram_active else "NORMAL ✅",
            "scram_nedeni":    self.scram_reason or "—",
        }

    def get_history_as_dicts(self) -> list[dict]:
        """Tüm geçmişi serileştirilebilir dict listesi olarak döndür."""
        return [s.to_dict() for s in self._history]

    def get_last_events(self, n: int = 20) -> list[dict]:
        """Son n olayı döndür."""
        return [vars(e) for e in self._events[-n:]]

    # ─── Context Manager ──────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._log(logging.INFO, "Reaktör simülasyon oturumu kapatıldı.")
        return False

    def __repr__(self) -> str:
        return (f"ReactorCore(name={self.config['reactor_name']!r}, "
                f"T={self.temperature:.1f}K, P={self.power_mwth:.1f}MWth, "
                f"scram={self.scram_active})")
