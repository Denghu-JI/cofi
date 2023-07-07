import numpy as np

from cofi.tools import CoFISimpleNewton
from cofi import BaseProblem, InversionOptions, Inversion


inv_problem = BaseProblem()
inv_problem.set_objective(lambda x: (x - 3) ** 2)
inv_problem.set_initial_model(30)
inv_problem.set_gradient(lambda x: 2 * x - 6)
inv_problem.set_hessian(lambda x: 2)
inv_options = InversionOptions()
inv_options.set_params(num_iterations=4)
inv_options.set_tool("cofi.simple_newton")


def test_run():
    solver = CoFISimpleNewton(inv_problem, inv_options)
    res = solver()
    assert res["model"] == 3.0
    assert inv_problem.initial_model == 30


def test_inv_run():
    inv = Inversion(inv_problem, inv_options)
    res = inv.run()
    res.summary()
    assert res.success
    assert res.model == 3.0
    assert inv_problem.initial_model == 30


def test_not_inplace():
    inv_problem.set_initial_model(np.array([[30.0]]))
    solver = CoFISimpleNewton(inv_problem, inv_options)
    res = solver()
    assert res["model"] == 3.0
    assert inv_problem.initial_model == 30.0
    assert res["n_obj_evaluations"] == 4
    assert res["n_grad_evaluations"] == 4
    assert res["n_hess_evaluations"] == 4

def test_symmetric_hessian():
    inv_options.set_params(hessian_is_symmetric=True)
    inv_problem.set_initial_model(np.array([[30.0]]))
    solver = CoFISimpleNewton(inv_problem, inv_options)
    solver()
