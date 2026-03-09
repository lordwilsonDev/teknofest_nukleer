"""
automation.py — TEKNOFEST Nükleer Enerji Simülasyonu Otomasyon Modülü
======================================================================
Reaktör gücü kontrolü için PID algoritması.
"""

class PIDController:
    """
    Basit PID (Proportional-Integral-Derivative) kontrolcü sınıfı.
    Reaktör gücünü hedef MWth değerinde tutmak için kontrol çubuklarını ayarlar.
    """
    def __init__(self, Kp: float, Ki: float, Kd: float, setpoint: float = 0.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        
        self._prev_error = 0.0
        self._integral = 0.0
        self.enabled = False

    def reset(self):
        self._prev_error = 0.0
        self._integral = 0.0

    def compute(self, current_value: float, dt: float) -> float:
        """
        Gerekli kontrol çıkışını hesapla.
        Çıkış: Kontrol çubuğu pozisyon değişimi veya mutlak pozisyon (reaktöre göre ayarlanır).
        """
        if not self.enabled or dt <= 0:
            return 0.0

        error = self.setpoint - current_value
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt
        
        # Rüzgar yukarı (windup) önleme
        self._integral = max(-50.0, min(50.0, self._integral))

        output = (self.Kp * error) + (self.Ki * self._integral) + (self.Kd * derivative)
        self._prev_error = error
        
        return output
