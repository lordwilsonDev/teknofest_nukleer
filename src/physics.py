"""
physics.py — TEKNOFEST Nükleer Enerji Simülasyonu Fizik Motoru
==============================================================
SMR/MMR reaktörü için ileri düzey nötronik ve termal-hidrolik hesaplamalar.

Kapsam:
  • Nokta kinetiği (6 gecikmeli nötron grubu)
  • Xe-135 / I-135 zehirlenmesi (Bateman denklemleri)
  • Sm-149 / Pm-149 zehirlenmesi
  • Doppler sıcaklık geri bildirimi (negatif katsayı)
  • Boşluk reaktivitesi (void coefficient)
  • Pasif soğutma / doğal sirkülasyon modeli
  • Yakıt tükenmesi (burnup) tahmini
"""

import math


class PointKinetics:
    """
    6 gecikmeli nötron grubu ile tam nokta kinetiği modeli.
    Referans: Keepin (1965) gecikmeli nötron verileri.
    """
    # Gecikmeli nötron grubu parametreleri [β_i, λ_i (s⁻¹)]
    # U-235 termal fisyon için standart 6-grup verisi
    DELAYED_GROUPS = [
        (0.000215, 0.0124),   # Grup 1 — En uzun ömürlü
        (0.001424, 0.0305),   # Grup 2
        (0.001274, 0.111),    # Grup 3
        (0.002568, 0.301),    # Grup 4
        (0.000748, 1.14),     # Grup 5
        (0.000273, 3.01),     # Grup 6 — En kısa ömürlü
    ]

    BETA_TOTAL = sum(b for b, _ in DELAYED_GROUPS)  # Toplam β ≈ 0.00650
    NEUTRON_GENERATION_TIME = 5.0e-5  # Λ (saniye) — termal PWR için tipik

    def __init__(self):
        # Her grup için gecikmeli nötron öncüsü konsantrasyonu
        self.C = [0.0] * 6

    def initialize_at_power(self, flux: float):
        """
        Kritik durumda (k_eff = 1) denge konsantrasyonlarını hesapla.
        C_i^eq = (β_i / λ_i) * (Φ / Λ)
        """
        for i, (beta_i, lambda_i) in enumerate(self.DELAYED_GROUPS):
            self.C[i] = (beta_i / lambda_i) * (flux / self.NEUTRON_GENERATION_TIME)

    def step(self, flux: float, rho: float, dt: float = 1.0) -> float:
        """
        Nokta kinetiği denklemini çözer, yeni akıyı döndürür.
        dN/dt = [(ρ - β)/Λ] * N + Σ λ_i * C_i
        dC_i/dt = (β_i/Λ) * N - λ_i * C_i
        """
        N = flux
        delayed_source = sum(lam * c for (_, lam), c in zip(self.DELAYED_GROUPS, self.C))

        # Akı değişimi
        dN_dt = ((rho - self.BETA_TOTAL) / self.NEUTRON_GENERATION_TIME) * N + delayed_source
        new_N = max(1.0e6, N + dN_dt * dt)

        # Öncü güncelleme
        for i, ((beta_i, lambda_i), c) in enumerate(zip(self.DELAYED_GROUPS, self.C)):
            dC_dt = (beta_i / self.NEUTRON_GENERATION_TIME) * N - lambda_i * c
            self.C[i] = max(0.0, c + dC_dt * dt)

        return new_N


class XenonPoisoning:
    """
    I-135 → Xe-135 geçişi için tam Bateman denklemleri.
    Xe-135, gücün kesilmesi sonrası 6-8 saat içinde zirveye ulaşır (Xe-pit).
    """
    SIGMA_A_XE135 = 2.6e6    # Mikroskopik absorpsiyon tesir kesiti (barn)
    LAMBDA_I135   = 2.87e-5  # I-135 bozunma sabiti (s⁻¹)  T½ ≈ 6.7 saat
    LAMBDA_XE135  = 2.09e-5  # Xe-135 bozunma sabiti (s⁻¹) T½ ≈ 9.2 saat
    YIELD_I135    = 0.0639   # Fisyon verimi (U-235)
    YIELD_XE135   = 0.0023   # Doğrudan fisyon verimi

    def __init__(self):
        self.iodine   = 0.0   # I-135 konsantrasyonu (atom/cm³)
        self.xenon    = 0.0   # Xe-135 konsantrasyonu (atom/cm³)

    def initialize_equilibrium(self, flux: float):
        """Steady-state Xe-135 ve I-135 denge değerlerini hesapla."""
        sigma_phi = self.SIGMA_A_XE135 * flux
        self.iodine = (self.YIELD_I135 * flux) / self.LAMBDA_I135
        self.xenon  = ((self.YIELD_XE135 + self.YIELD_I135) * flux) / \
                      (self.LAMBDA_XE135 + sigma_phi)

    def step(self, flux: float, dt: float = 1.0) -> float:
        """
        Diferansiyel denklemleri çöz, reaktivite cezasını döndür (Δk/k).
        """
        dI = self.YIELD_I135 * flux - self.LAMBDA_I135 * self.iodine
        self.iodine = max(0.0, self.iodine + dI * dt)

        dXe = (self.YIELD_XE135 * flux
               + self.LAMBDA_I135 * self.iodine
               - self.LAMBDA_XE135 * self.xenon
               - self.SIGMA_A_XE135 * flux * self.xenon)
        self.xenon = max(0.0, self.xenon + dXe * dt)

        # Lineer reaktivite modeli: ρ_Xe = -σ_a * Xe / Σ_f (normalize)
        rho_xe = -(self.SIGMA_A_XE135 * self.xenon) / 5.0e19
        return max(-0.10, rho_xe)   # Fiziksel sınır: en fazla -10000 pcm


class SamariumPoisoning:
    """
    Pm-149 → Sm-149 zehirlenmesi. Kararlı izotop; flux düştüğünde birikim.
    """
    LAMBDA_PM149  = 3.63e-6  # Pm-149 bozunma sabiti (s⁻¹) T½ ≈ 53.1 saat
    SIGMA_A_SM149 = 4.1e4    # Sm-149 absorpsiyon tesir kesiti (barn)
    YIELD_PM149   = 0.0113   # Fisyon verimi

    def __init__(self):
        self.promethium = 0.0
        self.samarium   = 0.0

    def initialize_equilibrium(self, flux: float):
        self.promethium = (self.YIELD_PM149 * flux) / self.LAMBDA_PM149
        self.samarium   = (self.YIELD_PM149 * flux) / (self.SIGMA_A_SM149 * flux + 1e-12)

    def step(self, flux: float, dt: float = 1.0) -> float:
        dPm = self.YIELD_PM149 * flux - self.LAMBDA_PM149 * self.promethium
        self.promethium = max(0.0, self.promethium + dPm * dt)

        dSm = (self.LAMBDA_PM149 * self.promethium
               - self.SIGMA_A_SM149 * flux * self.samarium)
        self.samarium = max(0.0, self.samarium + dSm * dt)

        rho_sm = -(self.SIGMA_A_SM149 * self.samarium) / 5.0e19
        return max(-0.02, rho_sm)


class ThermalHydraulics:
    """
    Pasif soğutma ve doğal sirkülasyon modeli.
    Reaktör çekirdeği için lumped-parameter (topparametre) yaklaşımı.
    """
    RHO_COOLANT   = 750.0   # Soğutucu yoğunluğu (kg/m³, su-buharlı karışım tahmini)
    CP_COOLANT    = 4200.0  # Özgül ısı kapasitesi (J/kg·K)
    HA_CORE       = 3.5e6   # Çekirdek ısı transfer katsayısı × alan (W/K)
    PASSIVE_UA    = 8.0e4   # Pasif soğutucu UApassif (W/K) — doğal sirkülasyon
    T_SINK        = 300.0   # Nihai ısı havuzu sıcaklığı (K) — çevre

    def fuel_to_coolant(self, T_fuel: float, T_cool: float, power_mw: float, dt: float = 1.0):
        """
        Yakıttan soğutucuya ısı transferi.
        Q_gen = power_mw (termal)
        Q_cool = HA * (T_cool - T_sink) — doğal sirkülasyon
        """
        Q_gen    = power_mw * 1.0e6           # W
        Q_remove = self.PASSIVE_UA * (T_cool - self.T_SINK)
        Q_net    = Q_gen - Q_remove
        dT_cool  = Q_net / (self.RHO_COOLANT * self.CP_COOLANT * 1.0) * dt
        return max(self.T_SINK, T_cool + dT_cool)

    def passive_cooling_available(self, T_cool: float) -> bool:
        """Pasif soğutma yeterli mi? (Havuz sıcaklığı < 90°C üstü = aktif)"""
        return (T_cool - self.T_SINK) > 5.0


class ReactorPhysics:
    """
    Ana fizik motoru — tüm alt modülleri birleştiren arayüz sınıfı.
    ReactorCore tarafından her zaman adımında çağrılır.
    """

    # Sıcaklık geri bildirim katsayıları (negatif = güvenli)
    ALPHA_DOPPLER  = -3.8e-5   # Dk/k per K — Doppler katsayısı (yakıt)
    ALPHA_MODERATOR = -1.5e-5  # Dk/k per K — moderatör sıcaklık katsayısı
    ALPHA_VOID      = -0.05    # Dk/k per % void — geçerli PWR için negatif

    def __init__(self):
        self.kinetics  = PointKinetics()
        self.xenon     = XenonPoisoning()
        self.samarium  = SamariumPoisoning()
        self.thermo    = ThermalHydraulics()

        # Geriye dönük uyumluluk
        self.iodine_conc  = 0.0
        self.xenon_conc   = 0.0

    def initialize_steady_state(self, flux: float):
        """
        Tam güçte steady-state başlangıç koşullarını ayarla.
        Tüm zehirlerin denge değerlerini hesaplar.
        """
        self.kinetics.initialize_at_power(flux)
        self.xenon.initialize_equilibrium(flux)
        self.samarium.initialize_equilibrium(flux)
        # Geriye dönük uyumluluk güncelleme
        self.iodine_conc = self.xenon.iodine
        self.xenon_conc  = self.xenon.xenon

    def calculate_temp_feedback(self, T_fuel: float, T_ref: float = 563.0) -> float:
        """
        Birleşik Doppler + moderatör sıcaklık geri bildirimi.
        T_ref = 563 K (290°C) — tipik PWR çalışma sıcaklığı referansı
        """
        rho_doppler    = self.ALPHA_DOPPLER   * (T_fuel - T_ref)
        rho_moderator  = self.ALPHA_MODERATOR * (T_fuel - T_ref)
        return rho_doppler + rho_moderator

    def calculate_xenon_poisoning(self, flux: float, dt: float = 1.0) -> float:
        """Geriye dönük uyumluluk wrapper'ı."""
        rho_xe = self.xenon.step(flux, dt)
        self.iodine_conc = self.xenon.iodine
        self.xenon_conc  = self.xenon.xenon
        return rho_xe

    def calculate_reactivity(self, rod_pos: float, temp: float,
                             flux: float, dt: float = 1.0) -> float:
        """
        Toplam reaktivite hesabı (Δk/k).

        ρ_tot = ρ_rod + ρ_Doppler + ρ_Xe135 + ρ_Sm149

        rod_pos : 0 (tam içeri) → 100 (tam dışarı) [%]
        """
        # Kontrol çubuğu reaktivitesi
        # Nötron değerini simüle etmek için sigmoid eğrisi
        rod_worth_total = 0.12  # Toplam çubuk değeri ≈ 12% Δk/k (tipik PWR)
        rod_fraction    = rod_pos / 100.0
        # S-eğrisi: çubukların ortadaki hareketi daha etkili
        rod_factor      = (math.sin(math.pi * rod_fraction) * 0.4
                           + rod_fraction * 0.6)
        rho_rod = rod_worth_total * (rod_factor - 0.5)

        # Sıcaklık geri bildirimi
        rho_temp = self.calculate_temp_feedback(temp)

        # Zehir reaktiviteleri
        rho_xe = self.xenon.step(flux, dt)
        rho_sm = self.samarium.step(flux, dt)

        # Güncelle uyumluluk değişkenleri
        self.iodine_conc = self.xenon.iodine
        self.xenon_conc  = self.xenon.xenon

        total_rho = rho_rod + rho_temp + rho_xe + rho_sm
        return total_rho

    def estimate_burnup_mwdmt(self, power_mw: float, time_days: float,
                              initial_mass_kg: float = 1200.0) -> float:
        """
        Yakıt tükenmesini MW·d/MTU cinsinden tahmin eder.
        power_mw       : Termal güç (MWth)
        time_days      : İşletme süresi (gün)
        initial_mass_kg: İlk ağır metal kütlesi (U) — tipik SMR ≈ 1÷5 ton
        """
        mass_mt = initial_mass_kg / 1000.0  # kg → metrik ton
        return (power_mw * time_days) / mass_mt

    @property
    def xe_reactivity_pcm(self) -> float:
        """Mevcut Xe-135 reaktivite cezasını pcm cinsinden döndür."""
        rho_xe = -(self.xenon.SIGMA_A_XE135 * self.xenon.xenon) / 5.0e19
        return rho_xe * 1e5  # pcm = 10⁻⁵ × Δk/k

    @property
    def sm_reactivity_pcm(self) -> float:
        """Mevcut Sm-149 reaktivite cezasını pcm cinsinden döndür."""
        rho_sm = -(self.samarium.SIGMA_A_SM149 * self.samarium.samarium) / 5.0e19
        return rho_sm * 1e5
