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
    message:       str


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
            "control_rod_pos": 60,
            "coolant_flow":    80.0,
            "burnup_mwdmt":    0.0
        },
        "thresholds": {
            "max_temp":        610.0,
            "scram_temp":      623.0,
            "critical_temp":   673.0,
            "max_pressure":    175.0,
            "scram_pressure":  180.0,
            "min_coolant_flow": 10.0,
            "max_power_mw":    160.0
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

        # Durum değişkenleri
        self.temperature      = float(cfg_state["temperature"])
        self.pressure         = float(cfg_state["pressure"])
        self.neutron_flux     = float(cfg_state["neutron_flux"])
        self.control_rod_pos  = float(cfg_state["control_rod_pos"])
        self.coolant_flow     = float(cfg_state["coolant_flow"])
        self.burnup_mwdmt     = float(cfg_state.get("burnup_mwdmt", 0.0))
        self.power_mwth       = 0.0
        self.scram_active     = False
        self.alarm_level      = AlarmLevel.NORMAL
        self.scram_reason     = ""

        # Eşik değerleri
        self.max_temp         = float(cfg_thresh["max_temp"])
        self.scram_temp       = float(cfg_thresh.get("scram_temp", cfg_thresh["critical_temp"]))
        self.critical_temp    = float(cfg_thresh["critical_temp"])
        self.max_pressure     = float(cfg_thresh["max_pressure"])
        self.scram_pressure   = float(cfg_thresh.get("scram_pressure", cfg_thresh["max_pressure"] * 1.1))
        self.max_power        = float(cfg_thresh.get("max_power_mw", 160.0))

        # Yakıt parametreleri
        self._fuel_mass_kg    = float(cfg_fuel.get("initial_heavy_metal_kg", 2000.0))
        self._max_burnup      = float(cfg_fuel.get("max_burnup_mwdmt", 55000.0))

        # Gürültü parametreleri
        self._noise_flux      = float(cfg_sim.get("noise_flux_amplitude", 1.0e9))
        self._noise_temp      = float(cfg_sim.get("noise_temp_amplitude", 0.05))

        # Fizik motoru
        self.physics = ReactorPhysics()

        # Logger
        self._setup_logger()
        self._log(logging.INFO, f"Reaktör başlatıldı: {self.config['reactor_name']}")

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
        Xe-135/Sm-149 denge konsantrasyonlarını hesaplar.
        """
        self.physics.initialize_steady_state(self.neutron_flux)
        design_mwth = float(self.config.get("design_power_mwth", 150.0))
        self.power_mwth = design_mwth
        self._log(logging.INFO, "Steady-state başlangıç koşulları uygulandı.")

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
            self.temperature,
            self.neutron_flux,
            dt
        )

        # 2. Nötron akısı (nokta kinetiği üzerinden)
        new_flux = self.physics.kinetics.step(self.neutron_flux, rho, dt)
        noise    = random.gauss(0, self._noise_flux)
        self.neutron_flux = max(1.0e6, new_flux + noise)

        # 3. Termal güç (akı → güç dönüşümü)
        # 150 MWth reaktör için 3×10¹³ n/cm²·s tipik akı → ölçeklendirme
        design_flux    = 3.0e13
        design_mwth    = float(self.config.get("design_power_mwth", 150.0))
        self.power_mwth = (self.neutron_flux / design_flux) * design_mwth
        self.power_mwth = max(0.0, min(self.power_mwth, self.max_power * 1.2))

        # 4. Sıcaklık — enerji dengesi
        # Nominal: 150 MWth güç, 80% akış → T = 563 K kararlı
        # heat_gen ΔT → güç / referans_güç ile normalize
        nominal_mw   = float(self.config.get("design_power_mwth", 150.0))
        heat_gen     = (self.power_mwth / nominal_mw) * 3.0   # Max +3 K/s etkisi
        cooling_eff  = (self.coolant_flow / 100.0)
        cool_cap     = cooling_eff * 3.5 * (self.temperature / 563.0) ** 1.5
        delta_T      = (heat_gen - cool_cap) * dt
        noise_T      = random.gauss(0, self._noise_temp)
        self.temperature = max(280.0, self.temperature + delta_T + noise_T)


        # 5. Basınç — ideal gaz yaklaşımı (P ∝ T)
        T_ref          = self.config["initial_state"]["pressure"]  # 155 bar ref
        self.pressure  = (self.temperature / self.config["initial_state"]["temperature"]) \
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
        self.temperature += net_heat * dt * 0.01
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
            print(f"\n[⚠️  ALARM L{level}] {msg}")

    def emergency_shutdown(self, reason: str = "MANUAL SCRAM"):
        """SCRAM — çubukları tam içeri it, soğutucuyu maksimuma çek."""
        if not self.scram_active:
            self.scram_active    = True
            self.scram_reason    = reason
            self.alarm_level     = AlarmLevel.SCRAM
            self.control_rod_pos = 0.0
            self.coolant_flow    = 100.0
            self._log(logging.CRITICAL, f"☢️  SCRAM AKTİF: {reason}")
            print(f"\n[🚨 SCRAM] {reason}")

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
            xenon_conc       = self.physics.xenon_conc,
            samarium_conc    = self.physics.samarium.samarium,
            burnup_mwdmt     = self.burnup_mwdmt,
            reactivity_pcm   = self.physics.xe_reactivity_pcm + self.physics.sm_reactivity_pcm,
            scram_active     = self.scram_active,
            alarm_level      = self.alarm_level,
        )
        self._history.append(snap)
        if len(self._history) > self._history_max:
            self._history.pop(0)

    def get_status(self) -> dict:
        """Mevcut reaktör durumunu okunabilir sözlük olarak döndür."""
        return {
            "reaktör":         self.config["reactor_name"],
            "süre_s":          f"{self._elapsed_s:.1f}",
            "sıcaklık":        f"{self.temperature:.2f} K ({self.temperature - 273.15:.1f} °C)",
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
