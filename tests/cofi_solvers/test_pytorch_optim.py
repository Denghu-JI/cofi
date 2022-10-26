import numpy as np
import pytest

from cofi.solvers import PyTorchOptim
from cofi import BaseProblem, InversionOptions


inv_problem1 = BaseProblem()
inv_problem1.set_objective(lambda: 3)
inv_problem1.set_gradient(lambda: 3)
inv_problem1.set_initial_model(1)
inv_options1 = InversionOptions()
inv_options1.set_params(algorithm="Adam", num_iterations=10)

def test_invalid_algorithm():
    inv_options1.set_params(algorithm="Adamm")
    with pytest.raises(ValueError, match=r".*algorithm.*is invalid.*"):
        PyTorchOptim(inv_problem1, inv_options1)
    inv_options1.set_params(algorithm="Adam")

def test_torch_init_tensor_nativetype():
    import torch
    inv_problem1.set_initial_model(torch.tensor(1))
    PyTorchOptim(inv_problem1, inv_options1)

def test_torch_init_tensor_error():
    inv_problem1.set_initial_model([[1,2],[3]])
    with pytest.raises(RuntimeError, match=r".*error ocurred in converting.*"):
        PyTorchOptim(inv_problem1, inv_options1)
    inv_problem1.set_initial_model(1)

def test_torch_optimizer_error():
    inv_options1.set_params(algorithm="SGD")
    with pytest.raises(RuntimeError, match=r".*creating PyTorch Optimizer 'SGD'.*"):
        PyTorchOptim(inv_problem1, inv_options1)

def test_run_simple_obj():
    inv_problem = BaseProblem()
    inv_problem.set_objective(lambda x: (x-3)**2)
    inv_problem.set_initial_model(30)
    inv_problem.set_gradient(lambda x: 2*x - 6)
    inv_problem.set_hessian(lambda x: 2)
    learning_rates = [1000, 10, 1, 1, 1, 2, 0.1, 1, 2, 0.1, 10, 10, 0.1]
    for i, alg in enumerate(PyTorchOptim.available_algs):
        print(alg)
        if alg == "SparseAdam":
            continue
        inv_options = InversionOptions()
        if alg == "RAdam":
            inv_options.set_params(
                algorithm=alg,
                verbose=False,
                lr=learning_rates[i],
                num_iterations=400
            )
        else:
            inv_options.set_params(
                algorithm=alg, 
                verbose=False, 
                lr=learning_rates[i], 
                num_iterations=100
            )
        solver = PyTorchOptim(inv_problem, inv_options)
        res = solver()
        print(res["model"])
        assert pytest.approx(res["model"], abs=1) == 3

def test_callback():
    inv_problem = BaseProblem()
    inv_problem.set_objective(lambda x: (x-3)**2)
    inv_problem.set_initial_model(30)
    inv_problem.set_gradient(lambda x: 2*x - 6)
    inv_problem.set_hessian(lambda x: 2)
    inv_options = InversionOptions()
    callback_x = []
    inv_options.set_params(
        algorithm="Adam", 
        verbose=False, 
        lr=0.1, 
        num_iterations=100,
        callback=lambda x: callback_x.append(x)
    )
    solver = PyTorchOptim(inv_problem, inv_options)
    solver()
    assert len(callback_x) == 100
    assert "torch.Tensor" in str(type(callback_x[-1]))

def test_run_lin_regression():
    # problem setup code
    nparams = 4
    G = lambda x: np.array([x**i for i in range(4)]).T
    _m_true = np.array([-6,-5,2,1])
    sample_size = 20
    x = np.random.choice(np.linspace(-3.5,2.5), size=sample_size)
    forward = lambda m: G(x).dot(m)
    y_obs = forward(_m_true) + np.random.normal(0,1,sample_size)
    objective = lambda m: np.sum(np.square(y_obs - forward(m)))
    objective_grad = lambda m: - 2 * np.expand_dims(y_obs - forward(m),1) * G(x)
    # BaseProblem definition
    inv_problem = BaseProblem()
    inv_problem.set_objective(objective)
    inv_problem.set_gradient(objective_grad)
    inv_problem.set_initial_model(np.zeros(nparams))
    # InversionOptions definition
    inv_options = InversionOptions()
    inv_options.set_params(algorithm="Adam", num_iterations=200, lr=0.1)
    # solve
    solver = PyTorchOptim(inv_problem, inv_options)
    res = solver()
    for i in range(nparams):
        assert pytest.approx(res["model"][i], abs=2) == _m_true[i]
