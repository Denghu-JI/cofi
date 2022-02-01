from cofi import BaseSolver
from cofi.cofi_objective import LeastSquareObjective, Model

import numpy as np
from ._utils import warn_normal_equation


class LRNormalEquation(BaseSolver):
    def __init__(self, objective: LeastSquareObjective):
        self.objective = objective

    def solve(self) -> Model:
        warn_normal_equation()

        G = self.objective.design_matrix()
        Y = self.objective.data_y()
        # TODO regularisation handling? prior model? (ref: inverseionCourse.curveFitting)
        # TODO return posterior covariance? (ref: inverseionCourse.curveFitting)
        res = np.linalg.inv(G.T @ G) @ (G.T @ Y)
        model = Model(
            **dict([("p" + str(index[0]), val) for (index, val) in np.ndenumerate(res)])
        )
        return model