from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np
import piqp
import scipy.sparse as sp
from line_profiler.explicit_profiler import profile

from giskardpy.qp.exceptions import InfeasibleException
from giskardpy.qp.qp_data import QPDataExplicit
from giskardpy.qp.solvers.qp_solver import QPSolver


@dataclass
class QPSolverPIQP(QPSolver[QPDataExplicit]):
    """
    min_x 0.5 x^T P x + c^T x
    s.t.  Ax = b
          Gx <= h
          lb <= x <= ub
    """

    @profile
    def solver_call_explicit_interface(self, qp_data: QPDataExplicit) -> np.ndarray:
        H = sp.diags(qp_data.quadratic_weights, offsets=0, format="csc")
        solver = piqp.SparseSolver()
        # solver.settings.eps_abs = 1e-3
        # solver.settings.eps_rel = 1e-4
        # solver.settings.eps_duality_gap_rel = 5e-7
        # solver.settings.iterative_refinement_always_enabled = True
        # solver.settings.delta_init = 7e-3
        # solver.settings.preconditioner_scale_cost = True
        solver.settings.eps_abs = 1e-6  # Relaxed from 1e-8
        solver.settings.eps_rel = 1e-7  # Relaxed from 1e-9
        solver.settings.eps_duality_gap_abs = 1e-4  # Add this
        solver.settings.eps_duality_gap_rel = 1e-5  # Add this
        # solver.settings.verbose = True
        # solver.settings.preconditioner_scale_cost = True  # Enable this
        if len(qp_data.neq_upper_bounds) == 0:
            solver.setup(
                P=H,
                c=qp_data.linear_weights,
                A=qp_data.eq_matrix,
                b=qp_data.eq_bounds,
                x_l=qp_data.box_lower_constraints,
                x_u=qp_data.box_upper_constraints,
            )
        else:
            solver.setup(
                P=H,
                c=qp_data.linear_weights,
                A=qp_data.eq_matrix,
                b=qp_data.eq_bounds,
                G=qp_data.neq_matrix,
                h_l=qp_data.neq_lower_bounds,
                h_u=qp_data.neq_upper_bounds,
                x_l=qp_data.box_lower_constraints,
                x_u=qp_data.box_upper_constraints,
            )

        status = solver.solve()
        if status.value != piqp.PIQP_SOLVED:
            raise InfeasibleException(f"Solver status: {status.value}")
        # print(f"Solver status: {solver.result.info.iter}")
        return solver.result.x

    solver_call = solver_call_explicit_interface
