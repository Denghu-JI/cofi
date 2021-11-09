from cofi.cofi_inverse import BaseInverser
from .lib import rjmcmc


class ReversibleJumpMCMC(BaseInverser):
    def __init__(self, x, y, error, lambda_min=None, lambda_max=None, lambda_std=None):
        """
        error: a error value per data point and can be thought as a weighting
           as to how well the fit will attempt to fit anindividual point.
           If the value is low, then the fit will be tight and
           conversely if the value is high then the fit will be loose.

        Note:
        x, y, and error must be of the same length
        """
        self.set_data(x, y, error, lambda_min, lambda_max, lambda_std)

    def set_data(self, x, y, error, lambda_min=None, lambda_max=None, lambda_std=None):
        # TODO - type validation / conversion (e.g. for numpy ndarray)
        self.x = x
        self.y = y
        self.error = error

        # lambda is defined as the ratio of the estimated noise to the real noise
        # this is set to perform hierarchical Bayesian sampling
        self.lambda_min = lambda_min
        self.lambda_max = lambda_max
        self.lambda_std = lambda_std

        if not (len(self.x) == len(self.y) and len(self.x) == len(self.error)):
            raise ValueError("Input lists must be of same length")

        self.data = rjmcmc.dataset1d(self.x, self.y, self.error)

        if lambda_min:
            self.data.set_lambda_range(self.lambda_min, self.lambda_max)
            self.data.set_lambda_std(self.lambda_std)

    def solve(
        self,
        burnin=10000,
        total=50000,
        max_order=5,
        sampler=None,
        multi_partition=False,
        partition_move_std=None,
    ):
        """
        On completion of solving, self.results is assigned a resultset1d object
        which contains various results and diagnostics about the analysis
        (Check ./lib/rjmcmc.py for inferface details)

        multi_partition: set to True when the data have discontinuities

        """

        if multi_partition:
            if partition_move_std is None:
                raise ValueError(
                    "partition_move_std is required for multiple partition regression"
                )
            self.results = rjmcmc.regression_part1d(
                self.data,
            )

        # user's own sampler takes 3 input arguments: x, y and i and returns a boolean
        # sample results are recorded in self.sample_x and self.sample_curves
        if sampler:
            self.sample_x = None
            self.sample_curves = []
            self.sample_i = 0

            def sampler_callback(x, y):
                if self.sample_x is None:
                    self.sample_x = x
                if sampler(x, y, self.sample_i):
                    self.sample_curves.append(y)
                self.sample_i += 1

            self.results = rjmcmc.regression_single1d_sampled(
                self.data, sampler_callback, burnin, total, max_order
            )

        # solve without user's own sampling method (by default)
        else:
            self.results = rjmcmc.regression_single1d(
                self.data, burnin, total, max_order
            )

    def order_historgram(self):
        if self.results is None:
            self.solve()
        return self.results.order_histogram()

    # TODO - determine whether to write a framework for results (if it's common for other approaches)
    #        or to write wrappter functions for all the functions of resultset1d (like above order_histogram)
    #        functions include: proposed, acceptance, partitions, order_histogram, partition_histogram,
    #                           partition_location_histogram, x, y, mean, median, mode,
    #                           credible_max, misfit, lambda_history, histogram
