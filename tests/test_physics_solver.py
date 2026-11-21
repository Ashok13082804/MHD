"""
Unit Tests for Coupled BTMS Physics Solver (Subpart A2)
"""

import unittest
import numpy as np
from part_a_without_ml.A2_physics_solver import CoupledBTMSSolver


class TestPhysicsSolver(unittest.TestCase):

    def setUp(self):
        # Lightweight grid for fast testing
        self.solver = CoupledBTMSSolver(
            Nx=20, Ny_f=10, Ny_b=10,
            U_in=0.05, T_in=298.15, B0=0.5, k_perm=1.0e-7,
            phi1=0.02, phi2=0.01, c_rate=1.0
        )

    def test_grid_initialization(self):
        self.assertEqual(self.solver.u.shape, (20, 20))
        self.assertEqual(self.solver.T.shape, (20, 20))
        self.assertEqual(len(self.solver.x), 20)
        self.assertEqual(len(self.solver.y), 20)

    def test_hydrodynamic_solution(self):
        self.solver.solve_hydrodynamics()
        # Wall velocity at bottom y=0 must be zero
        self.assertEqual(self.solver.u[0, 0], 0.0)
        # Fluid velocity inside channel must be positive
        self.assertGreater(np.mean(self.solver.u[:, :self.solver.Ny_f]), 0.0)
        # Solid battery velocity must be exactly zero
        self.assertEqual(np.max(self.solver.u[:, self.solver.Ny_f:]), 0.0)

    def test_conjugate_energy_solution(self):
        self.solver.solve_hydrodynamics()
        # Run a few SOR iterations
        residuals = self.solver.solve_energy_conjugate(max_iter=300, tol=1.0e-4)
        self.assertGreater(len(residuals), 0)
        metrics = self.solver.compute_thermal_performance()
        # Battery temperature should be higher than inlet coolant
        self.assertGreater(metrics["T_max_battery"], self.solver.T_in)
        self.assertGreater(metrics["Nu_avg"], 0.0)


if __name__ == "__main__":
    unittest.main()
