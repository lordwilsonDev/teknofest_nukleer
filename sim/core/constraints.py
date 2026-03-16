"""
Reactor Design Constraints: Safety & Optimization logic for TEKNOFEST 2025-2026.
Enforces hard-coded safety boundaries for iterative design scripts.
"""

from typing import Dict, Any, Union
from enum import Enum, auto

class SafetyStatus(Enum):
    SAFE = auto()
    WARNING = auto()
    VIOLATION = auto()

class ReactorConstraints:
    # TEKNOFEST Safety Parameters (Target Values)
    PEAK_CLADDING_TEMP_LIMIT = 1200.0  # Celsius (Standard Zircaloy limit for MMRs)
    FUEL_MELTING_TEMP_LIMIT = 2800.0    # Celsius (UO2)
    MIN_SHUTDOWN_MARGIN = 0.05          # delta k/k
    MAX_REACTIVITY_COEFFICIENT = 0.0    # Must be negative for inherent safety
    
    def __init__(self):
        self.last_state = {}

    def validate_state(self, state: Dict[str, float]) -> Dict[str, Any]:
        """
        Validates the instantaneous state of the reactor against hard-coded safety boundaries.
        :param state: Dictionary containing current simulation parameters.
        :return: Analysis dictionary with safety status.
        """
        results = {
            "status": SafetyStatus.SAFE,
            "violations": [],
            "warnings": []
        }
        
        # 1. Thermal-Hydraulic Bounds
        if state.get("pct", 0) > self.PEAK_CLADDING_TEMP_LIMIT:
            results["status"] = SafetyStatus.VIOLATION
            results["violations"].append(f"PCT Exceeded: {state['pct']}°C > {self.PEAK_CLADDING_TEMP_LIMIT}°C")
            
        # 2. Neutronic Bounds
        if state.get("reactivity_coeff", 0.1) >= self.MAX_REACTIVITY_COEFFICIENT:
            results["status"] = SafetyStatus.VIOLATION
            results["violations"].append(f"Positive Reactivity Coefficient detected: {state['reactivity_coeff']}")

        if state.get("shutdown_margin", 1.0) < self.MIN_SHUTDOWN_MARGIN:
            results["status"] = SafetyStatus.VIOLATION
            results["violations"].append(f"Insufficient Shutdown Margin: {state['shutdown_margin']} < {self.MIN_SHUTDOWN_MARGIN}")

        # 3. Warning Thresholds (90% of limit)
        if state.get("pct", 0) > (self.PEAK_CLADDING_TEMP_LIMIT * 0.9) and results["status"] != SafetyStatus.VIOLATION:
            results["status"] = SafetyStatus.WARNING
            results["warnings"].append("Approaching PCT limit.")

        return results

    def enforce_failsafe(self, state: Dict[str, float]):
        """
        Logic for 'Fail-Safe' Sovereign operation.
        If a violation is detected, the simulation must halt or trigger automatic SCRAM logic.
        """
        validation = self.validate_state(state)
        if validation["status"] == SafetyStatus.VIOLATION:
            print("🛑 SOVEREIGN SAFETY INTERVENTION: SCRAM TRIGGERED.")
            for v in validation["violations"]:
                print(f"   Reason: {v}")
            # In a production stack, this would raise a custom exception that halts the solver coupling.
            raise RuntimeError("Reactor Safety Violation: Simulation halted.")
        
        return True
