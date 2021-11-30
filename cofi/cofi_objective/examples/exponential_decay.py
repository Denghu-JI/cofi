from cofi.cofi_objective import BaseObjective, Model

import numpy as np
from typing import Union


class ExpDecay(BaseObjective):
    def __init__(self, x, y, m0):
        self.x = np.asanyarray(x)
        self.y = np.asanyarray(y)
        self.m0 = np.asanyarray(m0)
        self.n_params = m0.shape[0]

        if self.n_params % 2 != 0:
            raise ValueError(f"Exponential decay sums need to have an even number of parameters, but got ${self.n_params} instead")

        self._last_validated_model = None


    def _forward(self, model: Union[Model, np.array], ret_model=False):
        model = self.validate_model(model)
    
        yhat = np.zeros_like(self.x)
        for i in range(int(self.n_params/2)):
            yhat += model[i*2] * np.exp(-model[i+1] * self.x)
        return (yhat, model) if ret_model else yhat


    def objective(self, model: Union[Model, np.array]):
        yhat, model = self._forward(model, True)
        residuals = yhat - self.y
        res = residuals @ residuals
        return res

    
    def jacobian(self, model: Union[Model, np.array]):
        model = self.validate_model(model)
        
        jac = np.zeros([np.shape(self.x)[0], self.n_params])
        for i in range(int(self.n_params/2)):
            for j in range(len(self.x)):
                jac[j,i*2] = np.exp(-model[i*2+1]*self.x[j])
                jac[j,i*2+1] = -model[i*2] * self.x[j] * np.exp(-model[i*2+1]*self.x[j])
        return jac

    
    def gradient(self, model: Union[Model, np.array]):
        yhat, model = self._forward(model, True)
        jac = self.jacobian(model)
        return jac.T @ (yhat - self.y)


    def hessian(self, model: Union[Model, np.array]):
        # using the standard approximation (J^T J)
        jac = self.jacobian(model)
        hessian = jac.T @ jac
        return hessian


    def validate_model(self, model: Union[Model, np.array]) -> np.array:
        if model is self._last_validated_model:   # validated already (and converted if needed)
            return model

        if isinstance(model, Model):
            n_params = model.length()
            model = np.asanyarray(model.values())
        else:
            model = np.asanyarray(model)
            n_params = model.shape[0]
        
        if n_params != self.n_params:
            raise ValueError(f"Model length doesn't match initialisation, expected %{self.n_params} parameters but got ${model.length()} instead")
        
        self._last_validated_model = model
        return model