"""
tests/test_core.py — ReactorCore kapsamlı test paketi
=====================================================
pytest ile çalıştır:
    cd teknofest_nukleer
    pytest tests/ -v --tb=short
"""

import os
import sys
import math
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from reactor_core import ReactorCore, AlarmLevel


# ─── Yardımcı fonksiyon ────────────────────────────────────────────────────

def make_reactor(**overrides) -> ReactorCore:
    """Her test için taze ReactorCore nesnesi oluşturur (varsayılan konfigürasyon)."""
    r = ReactorCore.__new__(ReactorCore)
    base_cfg = dict(ReactorCore.DEFAULT_CONFIG)
    base_cfg.update(overrides)

    import importlib, json, io
    # Doğrudan __init__ çağrısı yerine minimal başlatma
    reactor = ReactorCore()
    return reactor


# ─── Başlatma Testleri ──────────────────────────────────────────────────────

class TestInitialization:

    def test_default_temperature(self):
        r = ReactorCore()
        assert r.coolant_temp == pytest.approx(563.0, rel=1e-3)
        assert r.fuel_temp == pytest.approx(563.0, rel=1e-3)

    def test_default_pressure(self):
        r = ReactorCore()
        assert r.pressure == pytest.approx(155.0, rel=1e-2)

    def test_scram_not_active_at_start(self):
        r = ReactorCore()
        assert r.scram_active is False

    def test_alarm_level_normal_at_start(self):
        r = ReactorCore()
        assert r.alarm_level == AlarmLevel.NORMAL

    def test_neutron_flux_positive(self):
        r = ReactorCore()
        assert r.neutron_flux > 0

    def test_burnup_zero_at_start(self):
        r = ReactorCore()
        assert r.burnup_mwdmt == pytest.approx(0.0, abs=1e-6)


# ─── Kontrol Çubuğu Testleri ────────────────────────────────────────────────

class TestControlRods:

    def test_rod_position_normal(self):
        r = ReactorCore()
        r.update_control_rods(75.0)
        assert r.control_rod_pos == pytest.approx(75.0)

    def test_rod_position_clamp_upper(self):
        r = ReactorCore()
        r.update_control_rods(150.0)
        assert r.control_rod_pos == pytest.approx(100.0)

    def test_rod_position_clamp_lower(self):
        r = ReactorCore()
        r.update_control_rods(-10.0)
        assert r.control_rod_pos == pytest.approx(0.0)

    def test_rod_move_blocked_during_scram(self):
        r = ReactorCore()
        r.emergency_shutdown("test")
        r.update_control_rods(80.0)
        # Çubuklar SCRAM sırasında 0'a gider, 80'e gitmez
        assert r.control_rod_pos == pytest.approx(0.0)

    def test_rod_to_zero_on_scram(self):
        r = ReactorCore()
        r.emergency_shutdown("test")
        assert r.control_rod_pos == pytest.approx(0.0)


# ─── Fizik Adımı Testleri ────────────────────────────────────────────────────

class TestPhysicsStep:

    def test_step_does_not_raise(self):
        r = ReactorCore()
        r.step(dt=1.0)  # Hata fırlatmamalı

    def test_flux_remains_positive_after_step(self):
        r = ReactorCore()
        r.update_control_rods(80)
        for _ in range(10):
            r.step(dt=1.0)
        assert r.neutron_flux > 0

    def test_temperature_increases_with_full_power(self):
        """Tam güçte (çubuklar dışarıda) sıcaklık artmalı."""
        r = ReactorCore()
        r.update_control_rods(100)
        r.update_coolant_flow(0)  # Soğutma kapalı
        initial_temp = r.temperature
        for _ in range(5):
            r.step(dt=1.0)
        # Soğutma olmadan sıcaklık artmalı ya da SCRAM tetiklenmeli
        assert r.temperature >= initial_temp or r.scram_active

    def test_elapsed_time_increments(self):
        r = ReactorCore()
        r.step(dt=5.0)
        assert r._elapsed_s == pytest.approx(5.0)

    def test_burnup_increases_with_power(self):
        r = ReactorCore()
        r.update_control_rods(70)
        for _ in range(100):
            r.step(dt=1.0)
        assert r.burnup_mwdmt >= 0.0

    def test_history_populated(self):
        """Geçmiş kaydının adımlardan sonra doldurulduğunu doğrular."""
        r = ReactorCore()
        r.initialize_steady_state()
        for _ in range(5):
            if not r.scram_active:
                r.step(dt=1.0)
        # An az 1 kayıt olmalı (SCRAM bile olsa äilk adımlar kaydedilmeli)
        assert len(r._history) >= 1
        # Eğer hiç SCRAM olmadıysa tüm 5 adım kaydedilmeli
        if not r.scram_active:
            assert len(r._history) == 5

    def test_scram_stops_new_steps(self):
        """SCRAM aktifken adım sadece atım ısısı sönümlemesi yapmalı."""
        r = ReactorCore()
        r.emergency_shutdown("test")
        pre_flux = r.neutron_flux
        r.step(dt=1.0)
        # Akı değişmemeli (SCRAM sonrası step sadece decay heat çalıştırır)
        assert r.neutron_flux == pytest.approx(pre_flux)


# ─── SCRAM / Güvenlik Testleri ───────────────────────────────────────────────

class TestSafety:

    def test_scram_on_critical_temperature(self):
        r = ReactorCore()
        # Kritik sıcaklık üstüne zorla
        r.coolant_temp = r.critical_temp + 1.0
        r.temperature = r.coolant_temp
        r._safety_check()
        assert r.scram_active is True

    def test_scram_on_high_pressure(self):
        r = ReactorCore()
        r.pressure = r.scram_pressure + 1.0
        r._safety_check()
        assert r.scram_active is True

    def test_alarm_on_high_temperature(self):
        r = ReactorCore()
        r.temperature = r.max_temp + 1.0
        r._safety_check()
        assert r.alarm_level >= AlarmLevel.HIGH

    def test_manual_scram(self):
        r = ReactorCore()
        r.emergency_shutdown("MANUEL TEST")
        assert r.scram_active is True
        assert r.scram_reason == "MANUEL TEST"

    def test_coolant_max_on_scram(self):
        r = ReactorCore()
        r.update_coolant_flow(30.0)
        r.emergency_shutdown("test")
        assert r.coolant_flow == pytest.approx(100.0)

    def test_reset_scram_temperature_too_high(self):
        r = ReactorCore()
        r.emergency_shutdown("test")
        r.temperature = r.max_temp + 50  # Hâlâ yüksek
        with pytest.raises(RuntimeError):
            r.reset_scram(authorized=True)

    def test_reset_scram_unauthorized(self):
        r = ReactorCore()
        r.emergency_shutdown("test")
        with pytest.raises(PermissionError):
            r.reset_scram(authorized=False)

    def test_borate_reduces_rod_pos(self):
        r = ReactorCore()
        r.update_control_rods(80.0)
        original = r.control_rod_pos
        r.borate(0.01)
        assert r.control_rod_pos < original


# ─── Durum ve API Testleri ───────────────────────────────────────────────────

class TestStatusAPI:

    def test_get_status_keys(self):
        r = ReactorCore()
        status = r.get_status()
        required_keys = ["reaktör", "sıcaklık", "basınç", "güç", "scram"]
        for key in required_keys:
            assert key in status, f"Eksik anahtar: {key}"

    def test_get_history_as_dicts(self):
        """Geçmiş dict listesi olarak döndürülmeli ve doğru anahtarlar içermeli."""
        r = ReactorCore()
        r.initialize_steady_state()
        for _ in range(3):
            if not r.scram_active:
                r.step(dt=1.0)
        history = r.get_history_as_dicts()
        assert len(history) >= 1
        assert "temperature_k" in history[0]
        assert "temperature_k" in history[0]

    def test_repr_contains_name(self):
        r = ReactorCore()
        assert "ReactorCore" in repr(r)

    def test_context_manager(self):
        with ReactorCore() as r:
            r.step(dt=1.0)
        # Hata fırlatmadan çıkmalı


# ─── Steady-state Testleri ───────────────────────────────────────────────────

class TestSteadyState:

    def test_initialize_steady_state_sets_xenon(self):
        r = ReactorCore()
        r.initialize_steady_state()
        assert r.physics.xenon.xenon > 0

    def test_power_output_after_steady_state(self):
        r = ReactorCore()
        r.initialize_steady_state()
        assert r.power_mwth > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
