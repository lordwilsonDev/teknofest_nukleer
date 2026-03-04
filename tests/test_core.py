import os
import sys
import unittest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from reactor_core import ReactorCore

class TestReactorCore(unittest.TestCase):
    def setUp(self):
        # Create a temp config for testing if needed or use defaults
        self.reactor = ReactorCore()

    def test_initialization(self):
        self.assertEqual(self.reactor.temperature, 300)
        self.assertFalse(self.reactor.scram_active)

    def test_scram_trigger(self):
        # Force high temperature
        self.reactor.temperature = 1000 
        self.reactor.step()
        self.assertTrue(self.reactor.scram_active)

    def test_rod_adjustment(self):
        self.reactor.update_control_rods(80)
        self.assertEqual(self.reactor.control_rod_pos, 80)
        
        # Test bounds
        self.reactor.update_control_rods(150)
        self.assertEqual(self.reactor.control_rod_pos, 100)
        
    def test_physics_step(self):
        initial_flux = self.reactor.neutron_flux
        self.reactor.update_control_rods(100) # Full power
        self.reactor.step()
        # Flux should increase when rods are out
        self.assertGreater(self.reactor.neutron_flux, 1e6) 

if __name__ == '__main__':
    unittest.main()
