from petsc4py.PETSc import PETSc
from cofi.cofi_solvers import TAOSolver
from cofi.cofi_objective import ExpDecay

import numpy as np
import matplotlib.pyplot as plt


# ---------- generate data --------------------------------------------------
def predict(x, t):
    yhat = np.zeros_like(t)
    for i in range(int(np.shape(x)[0] / 2)):
        yhat += x[i * 2] * np.exp(-x[i * 2 + 1] * t)
    return yhat


x = np.array([1, 0.1])
t = np.linspace(0, 10)
y = predict(x, t)
x0 = np.array([2, 0.2])
y0 = predict(x0, t)

plt.plot(t, y)
plt.plot(t, y0)
# plt.show()


# ---------- define problem -------------------------------------------------
exp_decay_objective = ExpDecay(t, y, x0)
tao_solver = TAOSolver(exp_decay_objective)


# ---------- start solving --------------------------------------------------
# some of the methods available in PETSc
# https://petsc.org/main/docs/manualpages/Tao/TaoSetType.html
methods = ["nm", "lmvm", "nls", "ntr", "cg", "blmvm", "tron"]

for method in methods:
    model = tao_solver.solve(method)


# ---------- Levenberg-Marquardt optimizer ----------------------------------
x = np.array([1, 0.1, 2, 0.2, 3, 0.3])
t = np.linspace(0, 10)
y = predict(x, t)
x0 = np.array([2, 0.2, 3, 0.3, 4, 0.1])
y0 = predict(x0, t)
plt.plot(t, y)
plt.plot(t, y0)


exp_decay_objective_for_BRGN = ExpDecay(t, y, x0)
exp_decay_objective_for_BRGN.gradient = None
exp_decay_objective_for_BRGN.hessian = None
tao_solver = TAOSolver(exp_decay_objective_for_BRGN)
tao_solver.solve("brgn", "-tao_brgn_regularization_type lm")


# ---------- MPI ----------------------------------
# set data as np array, -> will be translated into petsc objects later
# all processes see the following
x_ = np.array([1, 0.1, 2, 0.2, 3, 0.3])
t_ = np.linspace(0, 10)
y_ = predict(x_, t_)
x0_ = np.array([2, 0.2, 3, 0.3, 4, 0.1])
y0_ = predict(x0_, t_)

exp_decay_objective_for_mpi = ExpDecay(t_, y_, x0_)
tao_solver_mpi = TAOSolver(exp_decay_objective_for_mpi, True)
tao_solver_mpi.set_options("-tao_monitor -tao_brgn_regularization_type lm")
tao_solver_mpi.solve('brgn')

