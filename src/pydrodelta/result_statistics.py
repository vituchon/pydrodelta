import logging
from pandas import DataFrame
import math

class ResultStatistics:
    """Collection of statistic analysis results for the procedure"""
    def __init__(
        self,
        obs : list = list(),
        sim : list = list(),
        metadata: dict = None,
        calibration_period : list = None,
        group : str = "cal",
        compute : bool = False
        ):
        """Initiate collection of statistic analysis for the procedue
        
        Parameters:
        -----------
        obs : list of floats
            List of observed values

        sim : list of floats
            List of simulated values. Must be of the same length as obs
        
        metadata : dict or None
            Metadata of the node and the variable
        
        calibration_period : 2-length list  or None
            start and end date for splitting the data into calibration and validation periods
        
        group : str (defaults to 'cal')
            cal or val

        compute : bool (defaults to False)
            Compute statistical analysis
            """
        self.obs = list(obs) if obs is not None else list()
        """List of observed values"""
        self.sim = list(sim) if sim is not None else list()
        """List of simulated values. Must be of the same length as obs"""
        self.metadata = metadata
        """Metadata of the node and the variable (dict)"""
        self.calibration_period = [x.isoformat() for x in calibration_period] if calibration_period is not None else None
        """start and end date for splitting the data into calibration and validation periods"""
        self.group = group
        """cal or val"""
        self.errors = None
        """List of errors (difference between sim and obs)"""
        self.n = None
        """Number of observations"""
        self.mse = None
        """Mean squared error"""
        self.rmse = None
        """Root mean squared error"""
        self.bias =  None
        """Bias (mean error)"""
        self.mean_obs = None
        """Mean of obs"""
        self.mean_sim = None
        """Mean of sim"""
        self.stdev_obs = None
        """Standard deviation of obs"""
        self.stdev_sim = None
        """Standard deviation of sim"""
        self.stdev_diff = None
        """Difference of standard deviations"""
        self.nse = None
        """Nash-Sutcliffe efficiency coefficient"""
        self.var_obs = None
        """Observed variance"""
        self.var_sim = None
        """Simulated variance"""
        self.cov = None
        """Covariance of obs and sim"""
        self.r = None
        """Pearson's r correlation coefficient"""
        self.oneminusr = None
        """One minus Pearson's r correlation coefficient"""
        if compute:
            self.compute()

    def compute(self) -> None:
        """Compute the statistical analysis.
        
        Saves the results inplace (returns None)"""
        if not len(self.sim):
            logging.warn("No values found for statistics computation, skipping")
            return
        if len(self.obs) != len(self.sim):
            logging.warn("Length of obs and sim lists must be equal. No computation performed")
            return
        df = DataFrame({"obs":self.obs,"sim":self.sim})
        df = df.dropna()
        self.errors = [self.sim[i] - self.obs[i] for i in range(0,len(self.sim))]
        df["errors"] = df["sim"] - df["obs"]
        self.errors = [v for v in df["errors"]]
        self.n = len(df["errors"])
        if len(self.errors) == 0:
            logging.warn("No obs/sim pairs found for error calculation")
            return
        self.mse = sum([ e**2 for e in self.errors]) / len(self.errors)
        self.rmse = self.mse ** 0.5
        self.bias =  sum(self.errors) / self.n
        self.mean_obs = sum(df["obs"]) / self.n
        self.mean_sim = sum(df["sim"]) / self.n
        self.stdev_obs = sum([(x - self.mean_obs)**2 for x in df["obs"]]) / self.n
        self.stdev_sim = sum([(x - self.mean_sim)**2 for x in df["sim"]]) / self.n
        self.var_obs = self.stdev_obs ** 0.5
        self.var_sim = self.stdev_sim ** 0.5
        self.stdev_diff = self.stdev_sim - self.stdev_obs
        self.obs = [v for v in df["obs"]]
        self.sim = [v for v in df["sim"]]
        self.nse = 1 - self.mse / self.stdev_obs if self.stdev_obs != 0 else None
        self.cov = sum([ (self.obs[i] - self.mean_obs) * (self.sim[i] - self.mean_sim) for i in range(len(self.obs))]) / self.n
        self.r = self.cov / self.var_obs / self.var_sim if self.var_obs != 0 and self.var_sim != 0 else None
        self.oneminusr = 1 - self.r if self.r is not None else None
    def toDict(self) -> dict:
        """Convert result statistics into dict
        
        Returns:
        --------
        dict"""
        dict = self.__dict__
        # dict["obs"] = [v  if not math.isnan(v) else None for v in dict["obs"]]
        # dict["sim"] = [v  if not math.isnan(v) else None for v in dict["sim"]]
        return dict