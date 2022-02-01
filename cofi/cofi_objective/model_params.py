import numpy as np
from numbers import Number
from dataclasses import dataclass
from typing import Union
from scipy import stats
import yaml


@dataclass
class Parameter:
    """general class for holding a CoFI model parameter"""

    name: str
    value: Union[Number, np.ndarray] = None
    pdf: Union[stats.rv_continuous, np.ndarray] = None
    # continuous distributions in https://docs.scipy.org/doc/scipy/reference/stats.html

    def __post_init__(self):
        if self.value is None and self.pdf is None:
            raise ValueError(
                f"Specified parameter {self.name} has no initial value AND no"
                " distribution. You must either specify a value or a"
                " range/distribution for each parameter"
            )

        # if pdfs are specified, check they are done correctly.
        if self.pdf is not None:
            if self.value is not None:
                if isinstance(self.value, Number):
                    if not hasattr(self.pdf, "dist") or not isinstance(self.pdf.dist, stats.rv_continuous):
                        raise ValueError(
                            f"Specified PDF for parameter {self.name} id not a"
                            " continuous distribution! It is instead a"
                            f" {type(self.pdf)} which is not allowed"
                        )
                    if self.pdf.pdf(self.value) == 0.0:
                        raise ValueError(
                            f"Initial value {self.value} for parameter {self.name} has"
                            " zero density in specified pdf"
                        )
                elif isinstance(self.value, np.ndarray):
                    # so pdf should be same shape as value and should be all pdfs
                    if not isinstance(self.pdf, np.ndarray):
                        raise ValueError(
                            f"Specified PDF for parameter {self.name} must be an array"
                            " of PDFs"
                        )
                    elif self.pdf.shape != self.value.shape:
                        raise ValueError(
                            f"Specified PDF for parameter {self.name} must be an array"
                            f" of PDFs with same shape as {self.name}, but"
                            f" {self.name} was shape {self.value.shape} and pdf was"
                            f" shape {self.pdf.shape}"
                        )
                    # OK, so its an array of the right shape. Check the type
                    pdfs = self.pdf.ravel()
                    for i, pdf in enumerate(pdfs):
                        if not hasattr(pdf, "dist") or not isinstance(pdf.dist, stats.rv_continuous):
                            raise ValueError(
                                f"Specified PDF at index {i} for parameter {self.name} id not a"
                                " continuous distribution! It is instead a"
                                f" {type(self.pdf)} which is not allowed"
                            )
                    values = self.value.ravel()
                    for i, v in enumerate(values):
                        if pdfs[i].pdf(v) == 0.0:
                            raise ValueError(
                                f"Initial value at index {i} for parameter"
                                f" {self.name} has zero density in specified pdf"
                            )
            else:  # value is None, so we need to initialize it from pdf
                if isinstance(self.pdf, np.ndarray):
                    self.value = np.array(
                        [item.rvs() for item in self.pdf.ravel()]
                    ).reshape(self.pdf.shape)
                elif hasattr(self.pdf, "dist") and isinstance(self.pdf.dist, stats.rv_continuous):
                    self.value = self.pdf.rvs()
                else:
                    raise ValueError(
                        f"specified PDF for parameter {self.name} not a continuous distribution!"
                        f" It is instead of {type(self.pdf)} which is not allowed"
                    )
        else:  # PDF is None, but value is specified. This is fine, we dont need to do anything
            pass

    def __repr__(self) -> str:
        print(self.asdict())
        return yaml.safe_dump(self.asdict())

    # utility method to convert this to a dictionary that can be turned into a dictionary, for writing to yaml
    def asdict(self) -> dict:
        res = dict(name=self.name)
        if self.value is not None:
            if isinstance(self.value, np.ndarray):
                res["value"] = self.value.tolist()
            elif isinstance(self.value, np.generic):
                res["value"] = self.value.item()
            else:
                res["value"] = self.value
        if self.pdf is not None:
            if isinstance(self.pdf, np.ndarray):
                pdfa = np.empty(self.pdf.shape, dtype=object).flatten()
                for i, item in enumerate(self.pdf.ravel()):
                    pdfa[i] = f"{item.dist.name} {' '.join(map(str, item.args))}"
                res["pdf"] = pdfa.reshape(self.pdf.shape).tolist()
            elif hasattr(self.pdf, "dist") and isinstance(self.pdf.dist, stats.rv_continuous):
                res["pdf"] = f"{self.pdf.dist.name} {' '.join(map(str, self.pdf.args))}"
        return res


@dataclass
class Model:
    """general class for holding a CoFI model"""

    def __init__(self, **kwargs):
        self.params = []

        for nm, item in kwargs.items():
            if isinstance(item, tuple):
                val, pdf = item
            else:
                val, pdf = item, None
            val = np.asanyarray(val) if isinstance(val, list) else val
            self.params.append(Parameter(name=nm, value=val, pdf=pdf))

    def values(self) -> np.ndarray:
        return np.array([p.value if p.value else 0 for p in self.params])

    def length(self) -> int:
        return len(self.params)

    def to_yamlizable(self):
        return [p.asdict() for p in self.params]

    @staticmethod
    def init_from_yaml(yamldict: dict):
        if "parameters" not in yamldict:
            raise ValueError(
                f"Model specification in YML file *must* contain 'parameters'"
                f" information for your model"
            )

        # parameters should be a list of dictionaries
        if not isinstance(yamldict["parameters"], list):
            raise ValueError(
                f"In your YML file, you must specify 'parameters' for your model as a"
                f" list"
            )
        args = {}
        for p in yamldict["parameters"]:
            if not isinstance(p, dict):
                raise ValueError(
                    f"each paramater in model in YML file must be (key, value) pairs"
                )
            if "name" not in p or not isinstance(p["name"], str):
                raise ValueError(f"Each parameter must have a 'name' of string type")
            nm = p["name"]
            val = p["value"] if "value" in p else None
            pdf = p["bounds"] if "bounds" in p else None

            def parsepdf(toparse: str) -> stats.rv_continuous:
                bits = toparse.split()
                if bits[0] not in dir(stats):
                    raise ValueError(f"Unknown distribution specified: {bits[0]}")
                pdfstr = f"stats.{bits[0]}({','.join(bits[1:])})"
                return eval(pdfstr)

            if pdf is not None:
                if isinstance(pdf, list):
                    pdf = np.asarray(pdf)
                    pdf = np.array([parsepdf(item) for item in pdf.ravel()]).reshape(
                        pdf.shape
                    )
                else:
                    pdf = parsepdf(pdf)
            args[nm] = (val, pdf)
        return Model(**args)
