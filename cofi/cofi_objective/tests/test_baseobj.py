from cofi.cofi_objective import BaseObjective, LeastSquareObjective

import numpy as np
import pytest
from cofi.cofi_objective.base_objective import LinearFittingObjective

from cofi.cofi_objective.model_params import Model


def test_base_obj():
    objective_func = lambda model: np.sum(model)
    base_obj = BaseObjective(objective_func)
    assert base_obj.misfit(np.array([1, 2, 3])) == 6

    dumb_model = np.array([1, 2, 3])
    pytest.raises(NotImplementedError, base_obj.gradient, dumb_model)
    pytest.raises(NotImplementedError, base_obj.hessian, dumb_model)
    pytest.raises(NotImplementedError, base_obj.residual, dumb_model)
    pytest.raises(NotImplementedError, base_obj.jacobian, dumb_model)
    pytest.raises(NotImplementedError, base_obj.log_posterior, dumb_model)
    pytest.raises(NotImplementedError, base_obj.data_x)
    pytest.raises(NotImplementedError, base_obj.data_y)
    pytest.raises(NotImplementedError, base_obj.initial_model)
    pytest.raises(NotImplementedError, base_obj.params_size)


def test_ls_obj_wrong_dim():
    X = np.array([[1, 2, 3]])
    Y = np.array([[1], [2]])
    dumb_fwd = lambda model, X: (X @ np.expand_dims(model, axis=1))[0]
    with pytest.raises(ValueError):
        ls_obj = LeastSquareObjective(X, Y, dumb_fwd)


def test_ls_obj_pass_func():
    X = np.array([[1, 2, 3]])
    Y = np.array([6])
    forward = lambda model, X: (X @ np.expand_dims(model, axis=1))[0]
    ls_obj = LeastSquareObjective(X, Y, forward, [2, 2, 2])


def test_ls_obj_model_input_types():
    X = np.array([[1, 2, 3]])
    Y = np.array([6])
    forward = lambda model, X: (X @ np.expand_dims(model, axis=1))[0]
    initial_model_list = [2, 2, 2]
    initial_model_nparray = np.array(initial_model_list)
    initial_model = Model(m1=2, m2=2, m3=2)
    ls_obj_1 = LeastSquareObjective(X, Y, forward, initial_model_list)
    ls_obj_2 = LeastSquareObjective(X, Y, forward, initial_model_nparray)
    ls_obj_3 = LeastSquareObjective(X, Y, forward, initial_model)
    residual_1 = ls_obj_1.residual(initial_model)
    residual_2 = ls_obj_2.residual(initial_model_list)
    residual_3 = ls_obj_3.residual(initial_model_nparray)
    assert residual_1 == residual_2 == residual_3


def test_linear_obj_none_specified():
    X = np.array([[1, 2, 3]])
    Y = np.array([6])
    with pytest.raises(ValueError):
        linear_obj = LinearFittingObjective(X, Y, 3)