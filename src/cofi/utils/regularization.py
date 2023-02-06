from numbers import Number
from abc import abstractmethod, ABCMeta
from typing import Union
from functools import reduce
import numpy as np

from ..exceptions import DimensionMismatchError


REG_TYPES = {
    "damping": 0,
    "flattening": 1,
    "roughening": 1,
    "smoothing": 2,
}


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
    def model_size(self) -> Number:
        """the number of unknowns that current regularization function accepts"""
        raise NotImplementedError

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
        >>> reg1 = QuadraticReg(factor=1, model_size=3, reg_type="damping")
        >>> reg2 = QuadraticReg(factor=2, model_size=3, reg_type="smoothing")
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
        tmp_model_size = self.model_size
        tmp_reg = self.reg
        tmp_grad = self.gradient
        tmp_hess = self.hessian

        class NewRegularization(BaseRegularization):
            @property
            def model_size(self):
                return tmp_model_size

            def reg(self, model):
                return tmp_reg(model) + other_reg(model)

            def gradient(self, model):
                return tmp_grad(model) + other_reg.gradient(model)

            def hessian(self, model):
                return tmp_hess(model) + other_reg.hessian(model)

        return NewRegularization()


class QuadraticReg(BaseRegularization):
    r"""CoFI's utility class to calculate damping, flattening (roughening), and
    smoothing regularization

    .. tip::

        The regularization term is generally calculated in the form of:
        :math:`\text{factor}\times||D(m-m_0)||_2^2`, hence called ``QuadraticReg``.
        Where:
        
        - :math:`\text{factor}` is a coefficient of the regularization term 
        - :math:`D` is a weighting matrix depending on what type of regularization 
          you've specified (details :ref:`below <details_reg_type>`), and can also be a 
          "bring-your-own" matrix fed by the ``byo_matrix`` parameter
        - :math:`m_0` is a reference matrix only used in the ``damping`` case


    .. _details_reg_type:

    Now we explain what is the ``reg_type``, and how it changes the ``matrix`` (i.e.
    :math:`D` in the generic formula above).
    The terms "damping", "flattening" and "smoothing" correspond to the zeroth order,
    first order and second order Tikhonov regularization approaches respectively.

    - If ``reg_type == "damping"``, then

      .. toggle::

        - :meth:`reg` produces :math:`\text{reg}=\text{factor}\times||m-m_0||_2^2`
        - :meth:`gradient` produces
          :math:`\frac{\partial\text{reg}}{\partial m}=2\times\text{factor}\times(m-m_0)`
        - :meth:`hessian` produces
          :math:`\frac{\partial^2\text{reg}}{\partial m}=2\times\text{factor}\times I`
        - :attr:`matrix` is the identity matrix of size :math:`(M,M)`
        - where

          - :math:`m_0` is a reference model that you can specify in ``ref_model`` argument
            (default to zero)
          - :math:`M` is the number of model parameters

    - If ``reg_type == "roughening"`` (or equivalently ``"flattening"``),
      then

      .. toggle::

        - :meth:`reg` produces :math:`\text{reg}=\text{factor}\times||Dm||_2^2`
        - :meth:`gradient` produces
          :math:`\frac{\partial\text{reg}}{\partial m}=2\times\text{factor}\times D^TDm`
        - :meth:`hessian` produces
          :math:`\frac{\partial^2\text{reg}}{\partial m}=2\times\text{factor}\times D^TD`
        - :attr:`matrix` is :math:`D`
        - where

          - :math:`D` matrix helps calculate the first order derivative of :math:`m`.
            For 1D problems, it looks like

            :math:`\begin{pmatrix}-1.5&2&-0.5&&&\\-0.5&&0.5&&&&&\\&-0.5&&0.5&&&&\\&&...&&...&&&\\&&&-0.5&&0.5&&\\&&&&-0.5&&0.5&\\&&&&&0.5&-2&1.5\end{pmatrix}`

            .. :math:`\begin{pmatrix}-1&1&&&&\\&-1&1&&&\\&&...&...&&\\&&&-1&1&\\&&&&&-1&1\end{pmatrix}`

            While for higher dimension problems, by default it's a flattened version of
            an N-D array. The actual ordering of model parameters in higher dimensions
            is controlled by :class:`findiff.operators.FinDiff`.

    - If ``reg_type == "smoothing"``, then

      .. toggle::

        - :meth:`reg` produces :math:`\text{reg}=\text{factor}\times||Dm||_2^2`
        - :meth:`gradient` produces
          :math:`\frac{\partial\text{reg}}{\partial m}=2\times\text{factor}\times D^TDm`
        - :meth:`hessian` produces
          :math:`\frac{\partial^2\text{reg}}{\partial m}=2\times\text{factor}\times D^TD`
        - :attr:`matrix` is :math:`D`
        - where

          - :math:`D` matrix helps calculate the second order derivatives of :math:`m`.
            For 1D problems, it looks like

            :math:`\begin{pmatrix}2&-5&4&-1&&&\\1&-2&1&&&&\\&1&-2&1&&&\\&&...&...&...&&\\&&&1&-2&1&\\&&&&1&-2&1\\&&&-1&4&-5&2\end{pmatrix}`

            .. :math:`\begin{pmatrix}1&-2&1&&&&\\&1&-2&1&&&\\&&...&...&...&&\\&&&1&-2&1&\\&&&&1&-2&1\end{pmatrix}`

            While for higher dimension problems, by default it's a flattened version of
            an N-D array. The actual ordering of model parameters in higher dimensions
            is controlled by :class:`findiff.operators.FinDiff`.

    - If ``reg_type == None``, then we assume you want to use the argument
      ``byo_matrix``,

      .. toggle::

        - :meth:`reg` produces :math:`\text{reg}=\text{factor}\times||Dm||_2^2`
        - :meth:`gradient` produces
          :math:`\frac{\partial\text{reg}}{\partial m}=2\times\text{factor}\times D^TDm`
        - :meth:`hessian` produces
          :math:`\frac{\partial^2\text{reg}}{\partial m}=2\times\text{factor}\times D^TD`
        - :attr:`matrix` is :math:`D`
        - where

          - :math:`D` matrix is ``byo_matrix`` from the arguments (or identity matrix
            if ``byo_matrix is None``)

    Parameters
    ----------
    factor : Number
        the scale for the regularization term
    model_size : Number
        the number or shape of elements in an inference model
    reg_type : str
        specify what kind of regularization is to be calculated, by default
        ``"damping"``
    ref_model : np.ndarray
        reference model used only when ``reg_type == "damping"``,
        by default None (if this is None, then reference model is assumed to be zero)
    byo_matrix : np.ndarray
        bring-your-own matrix, used only when ``reg_type == None``

    Raises
    ------
    ValueError
        when input arguments don't conform to the standards described above. Check
        error message for details.

    Examples
    --------

    Generate a quadratic damping regularization matrix for model of size 3:

    >>> from cofi.utils import QuadraticReg
    >>> reg = QuadraticReg(factor=1, model_size=3)
    >>> reg(np.array([1,2,3]))
    3.0

    To use together with :class:`cofi.BaseProblem`:

    >>> from cofi import BaseProblem
    >>> from cofi.utils import QuadraticReg
    >>> reg = QuadraticReg(factor=1, model_size=3)
    >>> my_problem = BaseProblem()
    >>> my_problem.set_regularization(reg)

    You may also combine two regularization terms:

    >>> from cofi import BaseProblem
    >>> from cofi.utils import QuadraticReg
    >>> reg1 = QuadraticReg(factor=1, model_size=3, reg_type="damping")
    >>> reg2 = QuadraticReg(factor=2, model_size=5, reg_type="smoothing")
    >>> my_problem = BaseProblem()
    >>> my_problem.set_regularization(reg1 + reg2)
    """

    def __init__(
        self,
        factor: Number,
        model_size: Union[Number, np.ndarray],
        reg_type: str = "damping",
        ref_model: np.ndarray = None,
        byo_matrix: np.ndarray = None,
    ):
        super().__init__()
        self._factor = self._validate_factor(factor)
        self._model_size = model_size
        self._reg_type = self._validate_reg_type(reg_type)
        self._ref_model = ref_model
        self._byo_matrix = byo_matrix
        self._generate_matrix()

    @property
    def model_size(self) -> Number:
        """the number of model parameters

        This is always a number describing number of unknowns
        """
        if np.ndim(self._model_size):
            return reduce(lambda a, b: a * b, np.array(self._model_size), 1)
        return self._model_size

    @property
    def matrix(self) -> np.ndarray:
        """the regularization matrix

        This is either an identity matrix, or first/second order difference matrix
        (generated by Python package ``findiff``), or a custom matrix brought on your
        own.
        """
        return self._D

    def reg(self, model: np.ndarray) -> Number:
        flat_m = self._validate_model(model)
        if self._reg_type == "damping":
            if self._ref_model is None:
                return self._factor * flat_m.T @ flat_m
            diff_ref = flat_m - self._ref_model
            return self._factor * diff_ref.T @ diff_ref
        else:
            flat_m = self._validate_model(model)
            weighted_m = self.matrix @ flat_m
            return self._factor * weighted_m.T @ weighted_m

    def gradient(self, model: np.ndarray) -> np.ndarray:
        flat_m = self._validate_model(model)
        if self._reg_type == "damping":
            if self._ref_model is None:
                return 2 * self._factor * flat_m
            return 2 * self._factor * (flat_m - self._ref_model)
        else:
            return 2 * self._factor * self.matrix.T @ self.matrix @ flat_m

    def hessian(self, model: np.ndarray) -> np.ndarray:
        if self._reg_type == "damping":
            return 2 * self._factor * np.eye(self._model_size)
        else:
            return 2 * self._factor * self.matrix.T @ self.matrix

    @staticmethod
    def _validate_factor(factor):
        if not isinstance(factor, Number):
            raise ValueError("the regularization factor must be a number")
        elif factor < 0:
            raise ValueError("the regularization factor must be non-negative")
        return factor

    @staticmethod
    def _validate_reg_type(reg_type):
        if reg_type is not None and (
            not isinstance(reg_type, str) or reg_type not in REG_TYPES
        ):
            raise ValueError(
                "Please choose a valid regularization type. `damping`, "
                "`flattening` and `smoothing` are supported."
            )
        return reg_type

    def _generate_matrix(self):
        import findiff

        if self._reg_type == "damping":
            if not isinstance(self._model_size, Number):
                raise ValueError("model_size must be a number when damping is selected")
            self._D = np.identity(self._model_size)
        elif self._reg_type in REG_TYPES:  # 1st/2nd order Tikhonov
            # 1D model
            if np.size(self._model_size) == 1:
                order = REG_TYPES[self._reg_type]
                if self._model_size < order + 2:
                    raise ValueError(
                        f"the model_size needs to be at least >={order+2} "
                        f"for regularization type '{self._reg_type}'"
                    )
                d_dx = findiff.FinDiff(0, 1, order)
                self._D = d_dx.matrix((self._model_size,)).toarray()
            # 2D model
            elif np.size(self._model_size) == 2 and np.ndim(self._model_size) == 1:
                nx = self._model_size[0]
                ny = self._model_size[1]
                order = REG_TYPES[self._reg_type]
                if nx < order + 2 or ny < order + 2:
                    raise ValueError(
                        f"the model_size needs to be at least (>={order+2},"
                        f" >={order+2}) for regularization type '{self._reg_type}'"
                    )
                d_dx = findiff.FinDiff(0, 1, order)  # x direction
                d_dy = findiff.FinDiff(1, 1, order)  # y direction
                matx = d_dx.matrix((nx, ny))  # scipy sparse matrix
                maty = d_dy.matrix((nx, ny))  # scipy sparse matrix
                self._D = np.vstack((matx.toarray(), maty.toarray()))  # combine above
            else:
                raise NotImplementedError("only 1D and 2D derivative operators implemented")
        elif self._reg_type is None:
            if not isinstance(self._model_size, Number):
                raise ValueError(
                    "please provide a number for 'model_size' when bringing your "
                    "own weighting matrix"
                )
            if self._byo_matrix is None:
                self._D = np.identity(self._model_size)
            else:
                self._D = self._byo_matrix
            if len(self._D.shape) != 2:
                raise ValueError(
                    "the bring-your-own regularization matrix must be 2-dimensional"
                )
            elif self._D.shape[1] != self._model_size:
                raise ValueError(
                    "the bring-your-own regularization matrix must be in shape (_, M) "
                    "where M is the model size"
                )

    def _validate_model(self, model):
        flat_m = np.ravel(model)
        if flat_m.size != self.model_size:
            raise DimensionMismatchError(
                    entered_name="model",
                    entered_dimension=model.shape,
                    expected_source="model_size",
                    expected_dimension=self._model_size,
                )
        return flat_m
