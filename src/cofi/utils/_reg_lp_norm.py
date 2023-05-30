from typing import Union
from numbers import Number
from functools import reduce
import numpy as np
import scipy

from ._reg_base import BaseRegularization
from .._exceptions import DimensionMismatchError


REG_TYPES = {
    "damping": 0,
    "flattening": 1,
    "roughening": 1,
    "smoothing": 2,
}


class LpNormRegularization(BaseRegularization):
    r"""CoFI's utility class to calculate Lp-norm regularization, given the p value
    (default to 2), an optional weighting matrix and an optional reference value

    :math:`L(p, W, m_0) = ||W(m-m_0)||_p^p = \sum_i |W(m-m_0)_i|^p`

    Parameters
    ----------
    p : Number
        order value (p in the formula above), default to 2
    weighting_matrix: str or np.ndarray
        regularization type (one of {:code:`"damping"`, :code:`"flattening"`
        :code:`"smoothing"`}), or a bring-your-own weighting matrix, default to
        "damping" (identity matrix for weighting)
    model_shape: tuple
        shape of the model, must be supplied if the :code:`reference_model` is not
        given
    reference_model: np.ndarray
        :math:`m_0` in the formula above

    Raises
    ------
    ValueError
        if neither :code:`model_size` nor :code:`reference_model` is given
    DimensionMismatchError
        if both :code:`model_size` and :code:`reference_model` are given but they don't
        match in dimension
    """

    def __init__(
        self,
        p: Number = 2,
        weighting_matrix: Union[str, np.ndarray] = "damping",
        model_shape: tuple = None,
        reference_model: np.ndarray = None,
    ):
        self._order = self._validate_p(p)
        self._weighting_matrix = weighting_matrix
        self._model_shape = self._validate_shape(model_shape, reference_model)
        self._reference_model = reference_model
        self._generate_matrix()

    def reg(self, model: np.ndarray) -> Number:
        flat_m = self._validate_model(model)
        diff_m = self._model_diff_to_ref(flat_m)
        weighted_diff_m = self._weighting_matrix @ diff_m
        return self._lp_norm(weighted_diff_m)

    def gradient(self, model: np.ndarray) -> np.ndarray:
        flat_m = self._validate_model(model)
        diff_m = self._model_diff_to_ref(flat_m)
        weighted_diff_m = self._weighting_matrix @ diff_m
        grad_lp_norm = self._lp_norm_gradient(weighted_diff_m)
        return self.matrix.T @ grad_lp_norm

    def hessian(self, model: np.ndarray) -> np.ndarray:
        W = self._weighting_matrix
        flat_m = self._validate_model(model)
        diff_m = self._model_diff_to_ref(flat_m)
        weighted_diff_m = W @ diff_m
        hess_lp_norm = self._lp_norm_hessian(weighted_diff_m)
        return W.T @ np.diag(hess_lp_norm) @ W

    @property
    def model_shape(self) -> tuple:
        return self._model_shape

    @property
    def matrix(self) -> scipy.sparse.csr_matrix:
        """the regularization matrix

        This is either an identity matrix, or first/second order difference matrix
        (generated by Python package ``findiff``), or a custom matrix brought on your
        own.
        """
        return self._weighting_matrix

    def _generate_matrix(self):
        import findiff

        if (
            isinstance(self._weighting_matrix, str)
            and self._weighting_matrix in REG_TYPES
        ) or self._weighting_matrix is None:
            _reg_type = self._weighting_matrix
            if _reg_type == "damping" or _reg_type is None:  # 0th order difference
                self._weighting_matrix = scipy.sparse.identity(
                    self.model_size, format="csr"
                )
            elif _reg_type in REG_TYPES:  # 1st/2nd order difference
                if np.size(self.model_shape) == 1:  # 1D model
                    order = REG_TYPES[_reg_type]
                    if self.model_size < order + 2:
                        raise ValueError(
                            f"the model_size needs to be at least >={order+2} "
                            f"for regularization type '{self._reg_type}'"
                        )
                    d_dx = findiff.FinDiff(0, 1, order)
                    self._weighting_matrix = d_dx.matrix((self.model_size,))
                elif (
                    np.size(self.model_shape) == 2 and np.ndim(self.model_shape) == 1
                ):  # 2D model
                    nx = self.model_shape[0]
                    ny = self.model_shape[1]
                    order = REG_TYPES[_reg_type]
                    if nx > order + 2 or ny < order + 2:
                        raise ValueError(
                            f"the model_size needs to be at least (>={order+2},"
                            f" >={order+2}) for regularization type '{self._reg_type}'"
                        )
                    d_dx = findiff.FinDiff(0, 1, order)  # x direction
                    d_dy = findiff.FinDiff(1, 1, order)  # y direction
                    matx = d_dx.matrix((nx, ny))  # scipy sparse matrix
                    maty = d_dy.matrix((nx, ny))  # scipy sparse matrix
                    self._weighting_matrix = np.vstack(
                        (matx.toarray(), maty.toarray())
                    )  # combine above
                else:
                    raise NotImplementedError(
                        "only 1D and 2D derivative operators implemented"
                    )
        elif is_matrix_like(self._weighting_matrix):  # byo matrix
            if len(self._weighting_matrix.shape) != 2:
                raise ValueError(
                    "the bring-your-own regularization matrix must be 2-dimensional"
                )
            elif self._weighting_matrix.shape[1] != self.model_size:
                raise ValueError(
                    "the bring-your-own regularization matrix must be in shape (_, M) "
                    "where M is the model size"
                )
            self._weighting_matrix = scipy.sparse.csr_matrix(self._weighting_matrix)
        else:
            raise ValueError(
                "please specify the weighting matrix either via a string among "
                "\{`damping`, `flattening`, `smoothing`\}, or bringing your own matrix"
            )

    @staticmethod
    def _validate_p(p):
        if not isinstance(p, Number):
            raise ValueError(
                f"number expected for argument `p` but got {p} of type {type(p)}"
            )
        elif p <= 0:
            raise ValueError(f"positive number expected for argument `p` but got {p}")
        return p

    @staticmethod
    def _validate_shape(model_shape, reference_model):
        if model_shape is None and reference_model is None:
            raise ValueError("please provide the model shape")
        elif model_shape is None and reference_model is not None:
            return reference_model.shape
        elif model_shape is not None and reference_model is None:
            return model_shape
        else:
            if reference_model.shape != model_shape:
                raise DimensionMismatchError(
                    entered_dimension=reference_model.shape,
                    entered_name="reference_model",
                    expected_dimension=model_shape,
                    expected_source="model_shape",
                )
            return model_shape

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

    def _model_diff_to_ref(self, model):
        if self._reference_model is None:
            return model
        else:
            return model - np.ravel(self._reference_model)

    def _lp_norm(self, mat):
        return np.sum(np.abs(mat) ** self._order)

    def _lp_norm_gradient(self, mat):
        return self._order * np.abs(mat) ** (self._order - 1) * np.sign(mat)

    def _lp_norm_hessian(self, mat):
        p = self._order
        return p * (p - 1) * np.abs(mat) ** (p - 2)


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
    def model_shape(self) -> tuple:
        return self._model_size

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
                raise NotImplementedError(
                    "only 1D and 2D derivative operators implemented"
                )
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


matrix_like_classes = [np.ndarray] + [
    getattr(scipy.sparse, name)
    for name in scipy.sparse.__all__
    if name.endswith("_matrix")
]


def is_matrix_like(obj):
    return any(isinstance(obj, cls) for cls in matrix_like_classes)
