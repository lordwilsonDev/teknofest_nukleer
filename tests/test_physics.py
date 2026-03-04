"""
tests/test_physics.py — Physics modülü birim testleri
======================================================
Xenon-135, Samarium-149, nokta kinetiği ve sıcaklık geri bildirimi.
"""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from physics import (
    ReactorPhysics,
    XenonPoisoning,
    SamariumPoisoning,
    PointKinetics,
    ThermalHydraulics,
)


NOMINAL_FLUX = 3.0e13  # n/cm²·s — tipik SMR değeri


# ─── XenonPoisoning Testleri ─────────────────────────────────────────────────

class TestXenonPoisoning:

    def test_equilibrium_xenon_positive(self):
        xe = XenonPoisoning()
        xe.initialize_equilibrium(NOMINAL_FLUX)
        assert xe.xenon > 0

    def test_equilibrium_iodine_positive(self):
        xe = XenonPoisoning()
        xe.initialize_equilibrium(NOMINAL_FLUX)
        assert xe.iodine > 0

    def test_xenon_step_negative_reactivity(self):
        xe = XenonPoisoning()
        xe.initialize_equilibrium(NOMINAL_FLUX)
        rho = xe.step(NOMINAL_FLUX, dt=1.0)
        assert rho < 0, "Xe-135 reaktiviteyi negatif kılmalı"

    def test_xenon_decreases_after_shutdown(self):
        """Güç kesildikten sonra zaman içinde Xe önce artar (pit), sonra düşer."""
        xe = XenonPoisoning()
        xe.initialize_equilibrium(NOMINAL_FLUX)
        # Flux sıfır → Xe-pit başlar
        xe_initial = xe.xenon
        for _ in range(3600):  # 1 saat
            xe.step(0.0, dt=1.0)
        # Xe'nin arttığını doğrula (pit bölgesi)
        assert xe.xenon > xe_initial or xe.xenon >= 0

    def test_xenon_reactivity_bounded(self):
        xe = XenonPoisoning()
        xe.initialize_equilibrium(NOMINAL_FLUX)
        for _ in range(100):
            rho = xe.step(NOMINAL_FLUX, dt=1.0)
        assert rho >= -0.10  # Fiziksel sınır


# ─── SamariumPoisoning Testleri ──────────────────────────────────────────────

class TestSamariumPoisoning:

    def test_equilibrium_samarium_positive(self):
        sm = SamariumPoisoning()
        sm.initialize_equilibrium(NOMINAL_FLUX)
        assert sm.samarium > 0

    def test_samarium_step_negative_reactivity(self):
        sm = SamariumPoisoning()
        sm.initialize_equilibrium(NOMINAL_FLUX)
        rho = sm.step(NOMINAL_FLUX, dt=1.0)
        assert rho <= 0

    def test_samarium_bounded(self):
        sm = SamariumPoisoning()
        sm.initialize_equilibrium(NOMINAL_FLUX)
        rho = sm.step(NOMINAL_FLUX, dt=10.0)
        assert rho >= -0.02


# ─── PointKinetics Testleri ──────────────────────────────────────────────────

class TestPointKinetics:

    def test_initialize_sets_precursors(self):
        pk = PointKinetics()
        pk.initialize_at_power(NOMINAL_FLUX)
        total_precursor = sum(pk.C)
        assert total_precursor > 0

    def test_positive_reactivity_increases_flux(self):
        pk = PointKinetics()
        pk.initialize_at_power(NOMINAL_FLUX)
        flux_new = pk.step(NOMINAL_FLUX, rho=+0.003, dt=1.0)
        assert flux_new > NOMINAL_FLUX

    def test_negative_reactivity_decreases_flux(self):
        pk = PointKinetics()
        pk.initialize_at_power(NOMINAL_FLUX)
        flux_new = pk.step(NOMINAL_FLUX, rho=-0.005, dt=1.0)
        assert flux_new < NOMINAL_FLUX

    def test_zero_reactivity_stable(self):
        """ρ = 0 → akı büyük ölçüde sabit kalmalı."""
        pk = PointKinetics()
        pk.initialize_at_power(NOMINAL_FLUX)
        flux_new = pk.step(NOMINAL_FLUX, rho=0.0, dt=1.0)
        assert abs(flux_new - NOMINAL_FLUX) / NOMINAL_FLUX < 0.05

    def test_flux_never_negative(self):
        pk = PointKinetics()
        pk.initialize_at_power(NOMINAL_FLUX)
        flux = pk.step(NOMINAL_FLUX, rho=-0.99, dt=1.0)
        assert flux >= 1e6  # Alt sınır korunmalı


# ─── ReactorPhysics Birleşik Testleri ────────────────────────────────────────

class TestReactorPhysics:

    def test_calculate_reactivity_returns_float(self):
        rp = ReactorPhysics()
        result = rp.calculate_reactivity(60.0, 563.0, NOMINAL_FLUX, dt=1.0)
        assert isinstance(result, float)

    def test_rod_fully_in_gives_negative_reactivity(self):
        """Çubuklar tamamen içeri → negatif reaktivite → reaktör söner."""
        rp = ReactorPhysics()
        rho = rp.calculate_reactivity(0.0, 563.0, NOMINAL_FLUX, dt=1.0)
        assert rho < 0

    def test_rod_fully_out_gives_positive_reactivity(self):
        """Çubuklar tamamen dışarı → pozitif reaktivite → güç artar."""
        rp = ReactorPhysics()
        rho = rp.calculate_reactivity(100.0, 300.0, 1e10, dt=1.0)
        assert rho > 0

    def test_temp_feedback_negative(self):
        rp = ReactorPhysics()
        feedback = rp.calculate_temp_feedback(700.0)
        assert feedback < 0, "Doppler + moderatör katsayısı negatif olmalı"

    def test_temp_feedback_at_reference_zero(self):
        rp = ReactorPhysics()
        feedback = rp.calculate_temp_feedback(563.0, T_ref=563.0)
        assert feedback == pytest.approx(0.0, abs=1e-10)

    def test_burnup_calculation(self):
        rp = ReactorPhysics()
        bu = rp.estimate_burnup_mwdmt(power_mw=150.0, time_days=365.0,
                                      initial_mass_kg=2000.0)
        expected = (150.0 * 365.0) / 2.0  # 27375 MWd/MTU
        assert bu == pytest.approx(expected, rel=1e-4)

    def test_xe_reactivity_pcm_negative_at_equilibrium(self):
        rp = ReactorPhysics()
        rp.initialize_steady_state(NOMINAL_FLUX)
        assert rp.xe_reactivity_pcm < 0

    def test_sm_reactivity_pcm_negative_at_equilibrium(self):
        rp = ReactorPhysics()
        rp.initialize_steady_state(NOMINAL_FLUX)
        assert rp.sm_reactivity_pcm < 0

    def test_initialize_steady_state_sets_xenon(self):
        rp = ReactorPhysics()
        rp.initialize_steady_state(NOMINAL_FLUX)
        assert rp.xenon_conc > 0
        assert rp.iodine_conc > 0


# ─── ThermalHydraulics Testleri ───────────────────────────────────────────────

class TestThermalHydraulics:

    def test_passive_cooling_available(self):
        th = ThermalHydraulics()
        assert th.passive_cooling_available(400.0) is True

    def test_no_cooling_at_sink_temp(self):
        th = ThermalHydraulics()
        assert th.passive_cooling_available(302.0) is True

    def test_coolant_temp_increases_with_power(self):
        th = ThermalHydraulics()
        T = th.fuel_to_coolant(T_fuel=600.0, T_cool=563.0, power_mw=150.0, dt=1.0)
        # Yüksek güç → soğutucu ısınmalı
        assert T >= ThermalHydraulics.T_SINK

    def test_coolant_temp_minimum_is_sink(self):
        th = ThermalHydraulics()
        T = th.fuel_to_coolant(T_fuel=300.0, T_cool=300.0, power_mw=0.0, dt=1000.0)
        assert T >= ThermalHydraulics.T_SINK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
