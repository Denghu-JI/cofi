from abc import abstractmethod, ABCMeta
from numbers import Number
from functools import reduce
import numpy as np

from .._exceptions import DimensionMismatchError


class BaseRegularization(metaclass=ABCMeta):
    r"""Base class for a regularization term

    Check :class:`QuadraticReg` for a concrete example.

    .. rubric:: Basic interface

    The basic properties / methods for a regularization term in ``cofi.utils``
    include the following:

    .. autosummary::
        BaseRegularization.model_size
        BaseRegularization.reg
        BaseRegularization.gradient
        BaseRegularization.hessian
        BaseRegularization.__call__

    .. rubric:: Adding two terms

    Two instances of ``BaseRegularization`` can also be added together using the ``+``
    operator:

    .. autosummary::
        BaseRegularization.__add__

    """

    def __init__(
        self,
    ):
        pass

    @property
    @abstractmethod
    def model_shape(self) -> tuple:
        """the shape of models that current regularization function accepts"""
        raise NotImplementedError

    @property
    def model_size(self) -> Number:
        """the number of unknowns that current regularization function accepts"""
        return reduce(lambda a, b: a * b, np.array(self.model_shape), 1)

    def __call__(self, model: np.ndarray) -> Number:
        r"""a class instance itself can also be called as a function

        It works exactly the same as :meth:`reg`.

        In other words, the following two usages are exactly the same::

        >>> my_reg = QuadraticReg(factor=1, model_size=3)
        >>> my_reg_value = my_reg(np.array([1,2,3]))            # usage 1
        >>> my_reg_value = my_reg.reg(np.array([1,2,3]))        # usage 2
        """
        return self.reg(model)

    @abstractmethod
    def reg(self, model: np.ndarray) -> Number:
        """the regularization function value given a model to evaluate"""
        raise NotImplementedError

    @abstractmethod
    def gradient(self, model: np.ndarray) -> np.ndarray:
        """the gradient of regularization function with respect to model given a model

        The usual size for the gradient is :math:`(M,)` where :math:`M` is the number
        of model parameters
        """
        raise NotImplementedError

    @abstractmethod
    def hessian(self, model: np.ndarray) -> np.ndarray:
        """the hessian of regularization function with respect to model given a model

        The usual size for the Hessian is :math:`(M,M)` where :math:`M` is the number
        of model parameters
        """
        raise NotImplementedError

    def __add__(self, other_reg):
        r"""Adds two regularization terms

        Parameters
        ----------
        other_reg : BaseRegularization
            the second argument of "+" operator; must also be a
            :class:`BaseRegularization` instance

        Returns
        -------
        BaseRegularization
            a regularization term ``resRegularization`` such that:

            - :math:`\text{resRegularization.reg}(m)=\text{self.reg}(m)+\text{other_reg.reg}(m)`
            - :math:`\text{resRegularization.gradient}(m)=\text{self.gradient}(m)+\text{other_reg.gradient}(m)`
            - :math:`\text{resRegularization.hessian}(m)=\text{self.hessian}(m)+\text{other_reg.hessian}(m)`

        Raises
        ------
        TypeError
            when the ``other_reg`` is not a regularization term generated by CoFI Utils
        DimensionMismatchError
            when the ``other_reg`` doesn't accept model_size that matches the one of
            ``self``

        Examples
        --------

        >>> from cofi import BaseProblem
        >>> from cofi.utils import QuadraticReg
        >>> reg1 = QuadraticReg(model_shape=(3,), weighting_matrix="damping")
        >>> reg2 = QuadraticReg(model_shape=(3,), weighting_matrix="smoothing")
        >>> my_problem = BaseProblem()
        >>> my_problem.set_regularization(reg1 + reg2)

        """
        if not isinstance(other_reg, BaseRegularization):
            raise TypeError(
                f"unsupported operand type(s) for +: '{self.__class__.__name__}' "
                f"and '{other_reg.__class__.__name__}"
            )
        if self.model_size != other_reg.model_size:
            raise DimensionMismatchError(
                entered_name="the second regularization term",
                entered_dimension=other_reg.model_size,
                expected_source="the first regularization term",
                expected_dimension=self.model_size,
            )

        return CompositeRegularization(self, other=other_reg)

    def __rmul__(self, coefficient):
        r"""Multiply a regularization term with a constant number

        Parameters
        ----------
        coefficient : Number
            the first argument of "*" operator; must be a Number

        Returns
        -------
        BaseRegularization
            a regularization term ``resRegularization`` such that:

            - :math:`\text{resRegularization.reg}(m)=\text{coefficient}\times\text{self.reg}(m)`
            - :math:`\text{resRegularization.gradient}(m)=\text{coefficient}\times\text{self.gradient}(m)`
            - :math:`\text{resRegularization.hessian}(m)=\text{coefficient}\times\text{self.hessian}(m)`

        Raises
        ------
        TypeError
            when the ``coefficient`` is not of a python Number type

        Examples
        --------

        >>> from cofi import BaseProblem
        >>> from cofi.utils import QuadraticReg
        >>> reg = QuadraticReg(model_shape=(3,), weighting_matrix="damping")
        >>> my_problem = BaseProblem()
        >>> my_problem.set_regularization(10 * reg)

        """
        if not isinstance(coefficient, Number):
            raise TypeError(
                f"unsupported operand type(s) for *: '{coefficient.__class__.__name__}'"
                f" and '{self.__class__.__name__}"
            )
        return CompositeRegularization(self, coefficient=coefficient)


class CompositeRegularization(BaseRegularization):
    def __init__(self, base, other=None, coefficient=None):
        self.base = base
        self.other = other
        self.coefficient = coefficient

    @property
    def model_shape(self):
        return self.base.model_shape

    def reg(self, model):
        if self.other:
            return self.base.reg(model) + self.other.reg(model)
        elif self.coefficient is not None:
            return self.coefficient * self.base.reg(model)

    def gradient(self, model):
        if self.other:
            return self.base.gradient(model) + self.other.gradient(model)
        elif self.coefficient is not None:
            return self.coefficient * self.base.gradient(model)

    def hessian(self, model):
        if self.other:
            return self.base.hessian(model) + self.other.hessian(model)
        elif self.coefficient is not None:
            return self.coefficient * self.base.hessian(model)
