from cofi.cofi_objective import LinearFittingObjective
from cofi.cofi_objective import PolynomialFittingFwd
import cofi.cofi_solvers as solvers

import numpy as np
import matplotlib.pyplot as plt


# ------------ #0 generate data -----------------------------------------
true_model = [3, 2, 5]
npts = 25
xpts = np.random.uniform(0, 1, npts)
forward = PolynomialFittingFwd(2)
ypts = forward.solve(true_model, xpts) + np.random.normal(0, 0.5, size=npts)

print(f"--> ground truth model: {np.array(true_model)}\n")

plot = False
if plot:
    plt.figure(figsize=(10, 8))
    plt.plot(xpts, ypts, "x")
    plt.plot(np.linspace(0, 1, 100), forward.solve(true_model, np.linspace(0, 1, 100)))
    plt.show()


# ------------ #1.1 define objective from pre-defined forward ------------
objective_1 = LinearFittingObjective(xpts, ypts, forward.model_dimension(), forward=forward)


# ------------ #1.2 pure Python solver -----------------------------------
solver_1_pure = solvers.LRNormalEquation(objective_1)
model_1_pure = solver_1_pure.solve()
print(f"--> model predicted by pure Python solver: {model_1_pure.values()}\n")

ypts_predicted = forward.solve(model_1_pure, xpts)
# plot = True
if plot:
    plt.figure(figsize=(10, 8))
    plt.plot(xpts, ypts, "x", label="Data")
    plt.plot(
        np.linspace(0, 1, 100),
        forward.solve(true_model, np.linspace(0, 1, 100)),
        label="Input",
    )
    plt.plot(
        np.linspace(0, 1, 100),
        forward.solve(model_1_pure, np.linspace(0, 1, 100)),
        label="Predicted",
    )
    plt.legend()
    plt.show()


# ------------ #1.3 scipy.optimize.minimize solver -----------------------------------
solver_1_scipy_minimize = solvers.ScipyOptimizerSolver(objective_1)
model_1_scipy_minimize = solver_1_scipy_minimize.solve()
print(
    "--> model predicted by scipy.optimize.minimize:"
    f" {model_1_scipy_minimize.values()}\n"
)


# ------------ #1.4 scipy.optimize.least_squares solver -----------------------------------
solver_1_scipy_ls = solvers.ScipyOptimizerLSSolver(objective_1)
model_1_scipy_ls = solver_1_scipy_ls.solve()
print(
    "--> model predicted by scipy.optimize.least_squares:"
    f" {model_1_scipy_ls.values()}\n"
)


# ------------ #1.5 TAO "nm" solver -----------------------------------
solver_1_tao_nm = solvers.TAOSolver(objective_1)
model_1_tao_nm = solver_1_tao_nm.solve()
print(f"--> model predicted by TAO 'nm': {model_1_tao_nm.values()}\n")


# ------------ #1.6 TAO "brgn" solver -----------------------------------
solver_1_tao_brgn = solvers.TAOSolver(objective_1)
model_1_tao_brgn = solver_1_tao_brgn.solve("brgn")
print(f"--> model predicted by TAO 'brgn': {model_1_tao_brgn.values()}\n")


# ------------ #2.1 define objective another way ---------------------------
params_count = 3
design_matrix = lambda x: np.array([x ** o for o in range(params_count)]).T
objective_2 = LinearFittingObjective(xpts, ypts, params_count, design_matrix)
print("--------- objective defined another way -------------------")


# ------------ #2.2 pure Python solver -----------------------------------
solver_2_pure = solvers.LRNormalEquation(objective_2)
model_2_pure = solver_2_pure.solve()
print(f"--> model predicted by pure Python solver: {model_2_pure.values()}\n")
# plot = True
if plot:
    plt.figure(figsize=(10, 8))
    plt.plot(xpts, ypts, "x", label="Data")
    plt.plot(
        np.linspace(0, 1, 100),
        forward.solve(true_model, np.linspace(0, 1, 100)),
        label="Input",
    )
    plt.plot(
        np.linspace(0, 1, 100),
        forward.solve(model_1_pure, np.linspace(0, 1, 100)),
        label="Predicted 1",
        linewidth=3,
    )
    plt.plot(
        np.linspace(0, 1, 100),
        forward.solve(model_2_pure, np.linspace(0, 1, 100)),
        label="Predicted 2",
    )
    plt.legend()
    plt.show()


# ------------ #2.2 C solver -----------------------------------
solver_2_c = solvers.LRNormalEquationC(objective_2)
model_2_c = solver_2_c.solve()
print(f"--> model predicted by C/Cython solver: {model_2_c.values()}\n")


# ------------ #2.3 C++ solver -----------------------------------
solver_2_cpp = solvers.LRNormalEquationCpp(objective_2)
model_2_cpp = solver_2_cpp.solve()
print(f"--> model predicted by C++/PyBind11 solver: {model_2_cpp.values()}\n")


# ------------ #2.4 Fortran 77 solver -----------------------------------
solver_2_f77 = solvers.LRNormalEquationF77(objective_2)
model_2_f77 = solver_2_f77.solve()
print(f"--> model predicted by Fortran77/f2py solver: {model_2_f77.values()}\n")


# ------------ #2.5 Fortran 90 solver -----------------------------------
solver_2_f90 = solvers.LRNormalEquationF90(objective_2)
model_2_f90 = solver_2_f90.solve()
print(f"--> model predicted by Fortran90/f2py solver: {model_2_f90.values()}\n")