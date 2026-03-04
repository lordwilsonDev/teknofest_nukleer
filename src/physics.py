import math

class ReactorPhysics:
    """
    Advanced physics calculations for the nuclear reactor simulation.
    Includes Xenon-135 poisoning, temperature feedback, and reactivity models.
    """
    
    # Constants
    SIGMA_A_XE = 2.6e6  # Microscopic absorption cross-section of Xe-135 (barns)
    LAMBDA_I = 2.87e-5  # Decay constant for Iodine-135 (s^-1)
    LAMBDA_XE = 2.09e-5 # Decay constant for Xenon-135 (s^-1)
    YIELD_I = 0.0639    # Fission yield of Iodine-135
    YIELD_XE = 0.0023   # Fission yield of Xenon-135
    
    def __init__(self):
        self.iodine_conc = 0.0
        self.xenon_conc = 0.0
        self.reactivity_feedback = 0.0
        
    def calculate_xenon_poisoning(self, flux, dt=1.0):
        """
        Updates Iodine and Xenon concentrations based on neutron flux.
        Xenon poisoning reduces reactivity.
        """
        # Iodine production from fission and decay
        di = (self.YIELD_I * flux) - (self.LAMBDA_I * self.iodine_conc)
        self.iodine_conc += di * dt
        
        # Xenon production from fission, I-135 decay, and removal (decay + absorption)
        dxe = (self.YIELD_XE * flux) + (self.LAMBDA_I * self.iodine_conc) - \
              (self.LAMBDA_XE * self.xenon_conc) - (self.SIGMA_A_XE * flux * self.xenon_conc)
        self.xenon_conc += dxe * dt
        
        # Reactivity penalty (simplified linear model)
        # Higher Xenon conc = lower reactivity
        xenon_penalty = - (self.xenon_conc / 1e15) * 0.05 
        return xenon_penalty

    def calculate_temp_feedback(self, current_temp, reference_temp=300.0):
        """
        Doppler feedback (Negative temperature coefficient).
        As temperature increases, reactivity decreases.
        """
        alpha_t = -0.00015 # Reactivity change per Kelvin
        feedback = alpha_t * (current_temp - reference_temp)
        return feedback

    def calculate_reactivity(self, rod_pos, temp, flux, dt=1.0):
        """
        Combines rod position, temperature feedback, and Xenon poisoning
        to calculate total reactivity.
        rod_pos: 0 (In) to 100 (Out)
        """
        # Base reactivity from rods (0 to 100 range)
        base_rho = (rod_pos - 50) / 500.0 
        
        # Feedbacks
        temp_rho = self.calculate_temp_feedback(temp)
        xe_rho = self.calculate_xenon_poisoning(flux, dt)
        
        total_rho = base_rho + temp_rho + xe_rho
        return total_rho
