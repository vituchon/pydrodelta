from datetime import timedelta, datetime 
import pydrodelta.util as util
import os
import logging
from .a5 import createEmptyObsDataFrame, observacionesListToDataFrame, Crud
from pandas import isna, DataFrame
from .config import config
from typing import Union, List, Tuple
from .types.tvp import TVP
from .types.series_dict import SeriesDict
from .types.series_prono_dict import SeriesPronoDict
from .descriptors.int_descriptor import IntDescriptor
from .descriptors.string_descriptor import StringDescriptor
from .descriptors.float_descriptor import FloatDescriptor
from .descriptors.duration_descriptor import DurationDescriptor
from .descriptors.duration_descriptor_default_none import DurationDescriptorDefaultNone
from .descriptors.dict_descriptor import DictDescriptor
from .descriptors.dataframe_descriptor import DataFrameDescriptor

input_crud = Crud(**config["input_api"])
# output_crud = Crud(**config["output_api"])

class NodeSerie():
    """Represents a timestamped series of observed or simulated values for a variable in a node. """
    
    series_id = IntDescriptor()
    """Identifier of the series. If csv_file is set, reads the column identified in the header with this id. Else, unless observations is set, retrieves the identified series from the input api"""
    
    type = StringDescriptor()
    """Type of the series (only for retrieval from input api). One of 'puntual', 'areal', 'raster'"""
    
    @property
    def lim_outliers(self) -> Tuple[float,float]:
        """Minimum and maximum values for outliers removal (2-tuple of float)"""
        return self._lim_outliers
    @lim_outliers.setter
    def lim_outliers(
        self,
        values : Tuple[float,float]
        ) -> None:
        if values is None:
            self._lim_outliers = None
        elif isinstance(values,(tuple, list)):
            if len(values) < 2:
                raise ValueError("lim_outliers must be of length 2")
            else:
                self._lim_outliers = (values[0],values[1])
        else:
            raise ValueError("lim_outliers must be a 2-tuple of floats")
    
    lim_jump = FloatDescriptor()
    """Maximum absolute value for jump detection"""
    
    x_offset = DurationDescriptor()
    """Time offset applied to the timestamps of the input data on import"""
    
    y_offset = FloatDescriptor()
    """Offset applied to the values of the input data on import"""
    
    moving_average = DurationDescriptorDefaultNone()
    """Size of the time window used to compute a moving average to the input data"""
    
    data = DataFrameDescriptor()
    """DataFrame containing the timestamped values. Index is the time (with time zone), column 'valor' contains the values (floats) and column 'tag' contains the tag indicating the origin of the value (one of: observed, simulated, interpolated, moving_average, extrapolated, derived)"""
    
    metadata = DictDescriptor()
    """Metadata of the series"""
    
    outliers_data = DataFrameDescriptor()
    """Data rows containing removed outliers"""
    
    jumps_data = DataFrameDescriptor()
    """Data rows containing detected jumps"""
    
    csv_file = StringDescriptor()
    """Read data from this csv file. The csv file must have one column for the timestamps called 'timestart' and one column per series of data with the series_id in the header"""
    
    @property
    def observations(self) -> List[TVP]:
        """Time-value pairs of data. List of dicts {'timestart':datetime, 'valor':float}, or list of 2-tuples (datetime,float)"""
        return self._observations
    @observations.setter
    def observations(
        self,
        values : List[TVP]
        ) -> None:
        self._observations = util.parseObservations(values) if values is not None else None
    
    save_post = StringDescriptor()
    """Save upload payload into this file"""
    
    comment = StringDescriptor()
    """Comment about this series"""
    
    name = StringDescriptor()
    """Series name"""
    
    def __init__(
        self,
        series_id : int,
        tipo : str = "puntual",
        lim_outliers : Tuple[float,float] = None,
        lim_jump : float = None,
        x_offset : timedelta = timedelta(seconds=0),
        y_offset : float = 0,
        moving_average : timedelta = None,
        csv_file : str = None,
        observations : Union[List[TVP],List[Tuple[datetime,float]]] = None,
        save_post : str = None,
        comment : str = None,
        name : str = None
        ):
        """
        Parameters:
        -----------
        series_id : int
            Identifier of the series. If csv_file is set, reads the column identified in the header with this id. Else, unless observations is set, retrieves the identified series from the input api
        
        tipo : str = "puntual"
            Type of the series (only for retrieval from input api). One of 'puntual', 'areal', 'raster'
        
        lim_outliers : Tuple[float,float] = None
            Minimum and maximum values for outliers removal (2-tuple of float)

        lim_jump : float = None
            Maximum absolute value for jump detection

        x_offset : timedelta = timedelta(seconds=0)
            Apply this time offset to the timestamps of the input data

        y_offset : float = 0
            Apply this offset to the values of the input data

        moving_average : timedelta = None
            Compute a moving average using a time window of this size to the input data
         
        csv_file : str = None
            Read data from this csv file. The csv file must have one column for the timestamps called 'timestart' and one column per series of data with the series_id in the header

        observations : Union[List[TVP],List[Tuple[datetime,float]]] = None
            Time-value pairs of data. List of dicts {'timestart':datetime, 'valor':float}, or list of 2-tuples (datetime,float)

        save_post : str = None
            Save upload payload into this file"""
        self.series_id = series_id
        self.type = tipo
        self.lim_outliers : Tuple[float,float] = lim_outliers
        self.lim_jump = lim_jump
        self.x_offset = x_offset # util.interval2timedelta(x_offset) if isinstance(x_offset,dict) else x_offset # shift_by
        self.y_offset = y_offset # bias
        self.moving_average = util.interval2timedelta(moving_average) if moving_average is not None else None
        self.data = None
        self.metadata = None
        self.outliers_data = None
        self.jumps_data = None
        self.csv_file = "%s/%s" % (os.environ["PYDRODELTA_DIR"],csv_file) if csv_file is not None else None
        self.observations = observations
        self.save_post = save_post
        self.comment = comment
        self.name = name
    
    def __repr__(self):
        return "NodeSerie(type: %s, series_id: %i, count: %i)" % (self.type, self.series_id, len(self.data) if self.data is not None else 0)
    
    def toDict(self) -> dict:
        """Convert series to dict"""
        return {
            "series_id": self.series_id,
            "type": self.type,
            "lim_outliers": self.lim_outliers,
            "lim_jump": self.lim_jump,
            "x_offset": self.x_offset,
            "y_offset": self.y_offset,
            "moving_average": self.moving_average,
            "data": self.data.reset_index().values.tolist() if self.data is not None else None,
            "metadata": self.metadata,
            "outliers_data": self.outliers_data,
            "jumps_data": self.jumps_data
        }
    
    def loadData(
        self,
        timestart : datetime,
        timeend : datetime,
        input_api_config : dict = None
        ) -> None:
        """Load data from source according to configuration. 
        
        Priority is in this order: 
        - if .observations is set, loads time-value pairs from there, 
        - else if .csv_file is set, loads data from said csv file, 
        - else loads from input api the series of id .series_id and of type .type
        
        Parameters:
        -----------
        timestart : datetime
            Begin time of the timeseries
        
        timeend : datetime
            End time of the timeseries
        
        input_api_config : dict
            Api connection parameters. Overrides global config.input_api
            
            Properties:
            - url : str
            - token : str
            - proxy_dict : dict
        """
        timestart = util.tryParseAndLocalizeDate(timestart)
        timeend = util.tryParseAndLocalizeDate(timeend)
        if(self.observations is not None):
            logging.debug("Load data for series_id: %i from configuration" % (self.series_id))
            data = observacionesListToDataFrame(self.observations,tag="obs")
            self.data = data[(data.index >= timestart) & (data.index <= timeend)]
            self.metadata = {"id": self.series_id, "tipo": self.type}
        elif(self.csv_file is not None):
            logging.debug("Load data for series_id: %i from file %s" % (self.series_id, self.csv_file))
            data = util.readDataFromCsvFile(self.csv_file,self.series_id,timestart,timeend)
            self.data = observacionesListToDataFrame(data,tag="obs")
            self.metadata = {"id": self.series_id, "tipo": self.type}
        else:
            logging.debug("Load data for series_id: %i [%s to %s] from a5 api" % (self.series_id,timestart.isoformat(),timeend.isoformat()))
            crud = Crud(**input_api_config) if input_api_config is not None else input_crud
            self.metadata = crud.readSerie(self.series_id,timestart,timeend,tipo=self.type)
            if len(self.metadata["observaciones"]):
                self.data = observacionesListToDataFrame(self.metadata["observaciones"],tag="obs")
            else:
                logging.warning("No data found for series_id=%i" % self.series_id)
                self.data = createEmptyObsDataFrame(extra_columns={"tag":"str"})
            self.original_data = self.data.copy(deep=True)
            del self.metadata["observaciones"]
    
    def getThresholds(self) -> dict:
        """Read level threshold information from .metadata"""
        if self.metadata is None:
            logging.warn("Metadata missing, unable to set thesholds")
            return None
        thresholds = {}
        if self.metadata["estacion"]["nivel_alerta"]:
            thresholds["nivel_alerta"] = self.metadata["estacion"]["nivel_alerta"]
        if self.metadata["estacion"]["nivel_evacuacion"]:
            thresholds["nivel_evacuacion"] = self.metadata["estacion"]["nivel_evacuacion"]
        if self.metadata["estacion"]["nivel_aguas_bajas"]:
            thresholds["nivel_aguas_bajas"] = self.metadata["estacion"]["nivel_aguas_bajas"]
        return thresholds
    
    def removeOutliers(self) -> bool:
        """If .lim_outliers is set, removes outilers and returns True if any outliers were removed. Removed data rows are saved into .outliers_data"""
        if self.lim_outliers is None:
            return False
        self.outliers_data = util.removeOutliers(self.data,self.lim_outliers)
        if len(self.outliers_data):
            return True
        else:
            return False
    
    def detectJumps(self) -> bool:
        """If lim_jump is set, detects jumps. Returns True if any jumps were found. Data rows containing jumps are saved into .jumps_data"""
        if self.lim_jump is None:
            return False
        self.jumps_data = util.detectJumps(self.data,self.lim_jump)
        if len(self.jumps_data):
            return True
        else:
            return False
    
    def applyMovingAverage(self) -> None:
        """If .moving_average is set, apply a moving average with a time window size equal to .moving_average to the values of the series"""
        if self.moving_average is not None:
            # self.data["valor"] = util.serieMovingAverage(self.data,self.moving_average)
            self.data = util.serieMovingAverage(self.data,self.moving_average,tag_column = "tag")
    
    def applyTimedeltaOffset(
        self,
        row,
        x_offset) -> datetime:
        return row.name + x_offset
    
    def applyOffset(self) -> None:
        """Applies .x_offset (time axis) and .y_offset (values axis) to the data"""
        if self.data is None:
            logging.warn("applyOffset: self.data is None")
            return
        if not len(self.data):
            logging.warn("applyOffset: self.data is empty")
            return
        if isinstance(self.x_offset,timedelta):
            self.data.index = self.data.apply(lambda row: row.name + self.x_offset, axis=1) # self.applyTimedeltaOffset(row,self.x_offset), axis=1) # for x in self.data.index]
            self.data.index.rename("timestart",inplace=True)
        elif self.x_offset != 0:
            self.data["valor"] = self.data["valor"].shift(self.x_offset, axis = 0) 
            self.data["tag"] = self.data["tag"].shift(self.x_offset, axis = 0) 
        if self.y_offset != 0:
            self.data["valor"] = self.data["valor"] + self.y_offset
    
    def regularize(
        self,
        timestart : datetime,
        timeend : datetime,
        time_interval : timedelta,
        time_offset : timedelta,
        interpolation_limit : timedelta,
        inline : bool = True,
        interpolate : bool = False
        ) -> Union[None,DataFrame]:
        """Regularize the time step of the timeseries
        
        Parameters:
        -----------
        timestart : datetime
            Begin time of the output regular timeseries

        timeend : datetime
            End time of the output regular timeseries

        time_interval : timedelta
            time step of the output regular timeseries

        time_offset : timedelta
            Start time of the day of the output regular timeseries (overrides that of timestart)

        interpolation_limit : timedelta
            Maximum number of time steps to interpolate (default: 1)
        
        inline : bool = True
            If True, saves output regular timeseries to .data. Else, returns output regular timeseries
        
        interpolate : bool = False
            If True, interpolate missing values"""
        data = util.serieRegular(self.data,time_interval,timestart,timeend,time_offset,interpolation_limit=interpolation_limit,tag_column="tag",interpolate=interpolate)
        if inline:
            self.data = data
        else:
            return data
    
    def fillNulls(
        self,
        other_data : DataFrame,
        fill_value : float = None,
        x_offset : int = 0,
        y_offset : float = 0,
        inline : bool = False
        ) -> Union[None,DataFrame]:
        """Fills missing values of .data from other_data, optionally applying x_offset and y_offset. If for a missing value in .data, other_data is also missing, fill_value is set.
        
        Parameters:
        -----------
        other_data : DataFrame
            Timeseries data to be used to fill missing values in .data. Index must be the localized time and a column 'valor' must contain the values

        fill_value : float = None
            If for a missing value in .data, other_data is also missing, set this value.

        x_offset : int = 0
            Shift other_data this number of rows

        y_offset : float = 0
            Apply this offset to other_data values

        inline : bool = False
            If True, save null-filled timeseries into .data. Else return null-filled timeseries"""
        data = util.serieFillNulls(self.data,other_data,fill_value=fill_value,shift_by=x_offset,bias=y_offset,tag_column="tag")
        if inline:
            self.data = data
        else:
            return data
    
    def toCSV(
        self,
        include_series_id : bool = False
        ) -> str:
        """Convert timeseries into csv string
        
        Parameters:
        -----------
        include_series_id : bool = False
            Add a column with series_id"""
        if include_series_id:
            data = self.data
            data["series_id"] = self.series_id
            return data.to_csv()
        return self.data.to_csv()
    
    def toList(
        self,
        include_series_id : bool = False,
        timeSupport : timedelta = None,
        remove_nulls : bool = False,
        max_obs_date : datetime = None
        ) -> List[TVP]:
        """Convert timeseries to list of time-value pair dicts
        
        Parameters:
        -----------
        include_series_id : bool = False
            Add series_id to TVP dicts

        timeSupport : timedelta = None
            Time support of the timeseries (i.e., None for instantaneous observations, 1 day for daily mean)

        remove_nulls : bool = False
            Remove null values

        max_obs_date : datetime = None
            Remove data beyond this date
        
        Returns:
        --------
        list of time-value pair dicts : List[TVP]"""
        if self.data is None:
            return list()
        data = self.data[self.data.index <= max_obs_date] if max_obs_date is not None else self.data.copy(deep=True)
        data["timestart"] = data.index
        data["timeend"] = [x + timeSupport for x in data["timestart"]] if timeSupport is not None else data["timestart"]
        data["timestart"] = [x.isoformat() for x in data["timestart"]]
        data["timeend"] = [x.isoformat() for x in data["timeend"]]
        if include_series_id:
            data["series_id"] = self.series_id
        obs_list = data.to_dict(orient="records")
        for obs in obs_list:
            obs["valor"] = None if isna(obs["valor"]) else obs["valor"]
            obs["tag"] = None if "tag" not in obs else None if isna(obs["tag"]) else obs["tag"]
        if remove_nulls:
            obs_list = [x for x in obs_list if x["valor"] is not None] # remove nulls
        return obs_list
    
    def toDict(
        self,
        timeSupport : timedelta = None,
        as_prono : bool = False,
        remove_nulls : bool = False,
        max_obs_date : datetime = None
        ) -> Union[SeriesDict, SeriesPronoDict]:
        """Convert timeseries to series dict
        
        Parameters:
        -----------
        timeSupport : timedelta = None
            Time support of the timeseries (i.e., None for instantaneous observations, 1 day for daily mean)
        as_prono : bool = False
            Return SeriesPronoDict instead of SeriesDict
        
        remove_nulls : bool = False
            Remove null values
        
        max_obs_date : datetime = None
            Remove data beyond this date
        
        Returns:
        --------
        Dict containing
        - series_id: int
        - tipo: str
        - observaciones (or pronosticos, if as_prono=True): list of dict"""
        obs_list = self.toList(include_series_id=False,timeSupport=timeSupport,remove_nulls=remove_nulls,max_obs_date=max_obs_date)
        series_table = self.getSeriesTable()
        if as_prono:
            return {"series_id": self.series_id, "series_table": series_table, "pronosticos": obs_list}
        else:
            return {"series_id": self.series_id, "series_table": series_table, "observaciones": obs_list}
    
    def getSeriesTable(self) -> str:
        """Retrieve series table name (of a5 schema) for this timeseries"""
        return "series" if self.type == "puntual" else "series_areal" if self.type == "areal" else "series_rast" if self.type == "raster" else "series"