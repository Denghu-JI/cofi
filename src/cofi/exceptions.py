from typing import Any, List, Tuple, Union


GITHUB_ISSUE = "https://github.com/inlab-geo/cofi/issues"


class CofiError(Exception):
    """Base class for all CoFI errors"""
    def _form_str(self, super_msg, msg):
        if super_msg:
            return msg + "\n\n" + super_msg
        else:
            return msg 


class InvalidOptionError(CofiError, ValueError):
    r"""Raised when user passes an invalid option into our methods / functions

    This is a subclass of :exc:`CofiError` and :exc:`ValueError`.

    Parameters
    ----------
    *args : Any
        passed on directly to :exc:`ValueError`
    name: str
        name of the item that tries to take the invalid option
    invalid_option : Any
        the invalid option entered
    valid_options : list or str
        a list of valid options to choose from, or a string describing valid options
    """
    def __init__(self, *args, name: str, invalid_option: Any, valid_options: Union[List, str]):
        super().__init__(*args)
        self._name = name
        self._invalid_option = invalid_option
        self._valid_options = valid_options

    def __str__(self) -> str:
        super_msg = super().__str__()
        msg = f"the {self._name} you've entered ('{self._invalid_option}') is " \
              f"invalid, please choose from the following: {self._valid_options}.\n\n" \
              f"If you find it valuable to have '{self._invalid_option}' in CoFI, "\
              f"please create an issue here: {GITHUB_ISSUE}"
        return self._form_str(super_msg, msg) 


class DimensionMismatchError(CofiError, ValueError):
    r"""Raised when model or data shape doesn't match existing problem settings
    
    This is a subclass of :exc:`CofiError` and :exc:`ValueError`.

    Parameters 
    ---------- 
    *args : Any
        passed on directly to :exc:`ValueError`
    entered_dimension : tuple 
        dimension entered that conflicts with existing one
    entered_name : str
        name of the item, the dimension of which is entered
    expected_dimension : tuple
        dimension expected based on existing information
    expected_source : str
        name of an existing component that infers ``expected_dimension``
    """
    def __init__(
        self, 
        *args, 
        entered_dimenion: Tuple, 
        entered_name: str, 
        expected_dimension: Tuple, 
        expected_source: str,
    ) -> None:
        super().__init__(*args)
        self._entered_dimension = entered_dimenion
        self._entered_name = entered_name 
        self._expected_dimension = expected_dimension
        self._expected_source = expected_source

    def __str__(self) -> str:
        super_msg = super().__str__()
        msg = f"the {self._entered_name} you've provided {self._entered_dimension}" \
              f" doesn't match and cannot be reshaped into the dimension you've set" \
              f" for {self._expected_source} which is {self._expected_dimension}" 
        return self._form_str(super_msg, msg) 


class InsufficientInfoError(CofiError, RuntimeError):
    r"""Raised when insufficient information is supplied to perform operations at hand
    
    This is a subclass of :exc:`CofiError` and :exc:`RuntimeError`.

    Parameters
    ----------
    *args : Any
        passed on directly to :exc:`RuntimeError`
    needs : list or str 
        a list of information required to perform the operation, or a string describing
        them
    needed_for : str
        name of the operation to perform or the item to calculate 
    """ 
    def __init__(self, *args, needs: Union[List, str], needed_for: str):
        super().__init__(*args)
        self._needs = needs
        self._needed_for = needed_for
    
    def __str__(self) -> str:
        super_msg = super().__str__()
        msg = f"insufficient information supplied to calculate {self._needed_for}, " \
              f"needs: {self._needs}"
        return self._form_str(super_msg, msg)
