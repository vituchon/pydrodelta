from .util import interval2timedelta, createDatetimeSequence
from .derived_node_variable import DerivedNodeVariable
from .observed_node_variable import ObservedNodeVariable
from .a5 import createEmptyObsDataFrame, Serie
from .descriptors.int_descriptor import IntDescriptor
from .descriptors.string_descriptor import StringDescriptor
from .descriptors.datetime_descriptor import DatetimeDescriptor
from .descriptors.duration_descriptor import DurationDescriptor
from .descriptors.dict_descriptor import DictDescriptor
import pandas
import json
from datetime import datetime, timedelta
import isodate
from typing import Union, List, Dict
from pandas import DatetimeIndex, DataFrame

class Node:
    id = IntDescriptor()
    """Numeric identifier of the node"""
    tipo = StringDescriptor()
    """Type of node according to its geometry. Either 'puntual', 'areal' or 'raster'"""
    name = StringDescriptor()
    """Name of the node"""
    timestart = DatetimeDescriptor()
    """Start time of the observations"""
    timeend = DatetimeDescriptor()
    """End time of the observations"""
    forecast_timeend = DatetimeDescriptor()
    """Time end of the forecast"""
    time_interval = DurationDescriptor()
    """Intended time step of the observations/forecasts"""
    time_offset = DurationDescriptor()
    """Start time of the observations/forecasts relative to zero local time"""
    hec_node = DictDescriptor()
    """Mapping of this node to HECRAS geometry"""
    @property
    def variables(self) -> Dict[int,Union[ObservedNodeVariable,DerivedNodeVariable]]:
        """Variables represent the hydrologic observed/simulated properties at the node (such as discharge, precipitation, etc.). They are stored as a dictionary where and integer, the variable identifier, is used as the key, and the values are dictionaries. They may contain one or many ordered series, which contain the timestamped values. If series are missing from a variable, it is assumed that observations are not available for said variable at said node. Additionally, series_prono may be defined to represent timeseries of said variable at said node that are originated by an external modelling procedure. If series are available, said series_prono may be automatically fitted to the observed data by means of a linear regression. Such a procedure may be useful to extend the temporal extent of the variable into the forecast horizon so as to cover the full time domain of the plan. Finally, one or many series_sim may be added and it is where simulated data (as a result of a procedure) will be stored. All series have a series_id identifier which is used to read/write data from data source whether it be an alerta5DBIO instance or a csv file."""
        return self._variables
    @variables.setter
    def variables(self,variables : List[Union[DerivedNodeVariable,ObservedNodeVariable,dict]] = None):
        self._variables = {}
        if variables is not None:
            for variable in variables:
                if isinstance(variable, (DerivedNodeVariable,ObservedNodeVariable)):
                    self._variables[variable["id"]] = variable
                else:
                    self._variables[variable["id"]] = DerivedNodeVariable(node=self,**variable) if "derived" in variable and variable["derived"] == True else ObservedNodeVariable(node=self,**variable)
    node_type = StringDescriptor()
    """The type of node: either 'station' or 'basin'"""
    def __init__(
            self,
            id : int,
            name : str,
            time_interval : Union[dict,int],
            tipo : str="puntual",
            timestart : datetime = None,
            timeend : datetime = None,
            forecast_timeend : datetime = None,
            plan = None,
            time_offset : timedelta = None,
            topology = None,
            hec_node : dict = None,
            variables : List[Union[DerivedNodeVariable,ObservedNodeVariable]] = list(),
            node_type : str = "station"
        ):
        """Nodes represent stations and basins. These nodes are identified with a node_id and must contain one or many variables each, which represent the hydrologic observed/simulated properties at that node (such as discharge, precipitation, etc.). They are identified with a variable_id and may contain one or many ordered series, which contain the timestamped values. If series are missing from a variable, it is assumed that observations are not available for said variable at said node. Additionally, series_prono may be defined to represent timeseries of said variable at said node that are originated by an external modelling procedure. If series are available, said series_prono may be automatically fitted to the observed data by means of a linear regression. Such a procedure may be useful to extend the temporal extent of the variable into the forecast horizon so as to cover the full time domain of the plan. Finally, one or many series_sim may be added and it is where simulated data (as a result of a procedure) will be stored. All series have a series_id identifier which is used to read/write data from data source whether it be an alerta5DBIO instance or a csv file.
        
        Parameters:
        -----------
        id : int
            The node identifier

        name : str
            The node name

        time_interval : Union[dict,int]
            Intended time step of the observations/forecasts
        
        tipo : str="puntual"
            Type of node according to its geometry. Either 'puntual', 'areal' or 'raster'

        timestart : datetime = None
            Start time of the observations

        timeend : datetime = None
            End time of the observations
        
        forecast_timeend : datetime = None
            Time end of the forecast
        
        plan : Plan = None
            Plan that contains the topology that contains this node
        
        time_offset : timedelta = None
            Start time of the observations/forecasts relative to zero local time
            
        topology : Topology = None
            The topology that contains this node

        hec_node : dict = None
            Mapping of this node to HECRAS geometry
        
        variables : List[Union[DerivedNodeVariable,ObservedNodeVariable]] = list()
            The hydrologic observed/simulated properties at this node

        node_type : str = "station"
            The type of node: either 'station' or 'basin'

        """
        # if "id" not in params:
        #     raise ValueError("id of node must be defined")
        self.id = id
        self.tipo = tipo
        # if "name" not in params:
        #     raise ValueError("name of node must be defined")
        self.name = name
        self.timestart = timestart
        self.timeend = timeend
        self.forecast_timeend = forecast_timeend
        # if "time_interval" not in params:
        #     raise ValueError("time_interval of node must be defined")
        self.time_interval = time_interval
        self.time_offset = time_offset # if time_offset is not None else interval2timedelta(params["time_offset"]) if "time_offset" in params and params["time_offset"] is not None else None
        self.hec_node = hec_node
        self._plan = plan
        self._topology = topology
        self.variables = variables
        self.node_type = node_type
    def __repr__(self):
        variables_repr = ", ".join([ "%i: Variable(id: %i, name: %s)" % (k,self.variables[k].id, self.variables[k].metadata["nombre"] if self.variables[k].metadata is not None else None) for k in self.variables.keys() ])
        return "Node(id: %i, name: %s, variables: {%s})" % (self.id, self.name, variables_repr)
    def setOriginalData(self):
        """For each variable in .variables, set original data"""
        for variable in self.variables.values():
            variable.setOriginalData()
    def toDict(self) -> dict:
        """Convert node to dict"""
        return {
            "id": self.id,
            "tipo": self.tipo,
            "name": self.name,
            "timestart": self.timestart.isoformat() if self.timestart is not None else None,
            "timeend": self.timeend.isoformat() if self.timeend is not None else None,
            "forecast_timeend": self.forecast_timeend.isoformat() if self.forecast_timeend is not None else None,
            "time_interval": isodate.duration_isoformat(self.time_interval) if self.time_interval is not None else None,
            "time_offset": isodate.duration_isoformat(self.time_offset) if self.time_offset is not None else None,
            "hec_node": dict(self.hec_node) if self.hec_node is not None else None,
            "variables": [self.variables[key].toDict() for key in self.variables], 
            "node_type": self.node_type
        }
    def createDatetimeIndex(self) -> DatetimeIndex:
        """Create DatetimeIndex from .time_interval, .timestart, .timeend and .time_offset"""
        return createDatetimeSequence(None, self.time_interval, self.timestart, self.timeend, self.time_offset)
    def toCSV(
            self,
            include_series_id : bool = True,
            include_header : bool = True
            ) -> str:
        """
        returns self.variables.data as csv

        Parameters:
        -----------
        include_series_id : bool = True
            Add a column with series_id
        
        include_header : bool = True
            Add a header row
        
        Returns:
        --------
        csv string : str
        """
        data = createEmptyObsDataFrame(extra_columns={"tag":"str","series_id":"int"} if include_series_id else {"tag":"str"})
        for variable in self.variables.values():
            data = pandas.concat([data,variable.getData(include_series_id=include_series_id)])
        return data.to_csv(header=include_header)
    def outputToCSV(
            self,
            include_header : bool = True
            ) -> str:
        """
        returns data of self.variables.series_output as csv

        Parameters:
        -----------
        include_header : bool = True
            Add a header row
        
        Returns:
        --------
        csv string : csv
        """
        data = createEmptyObsDataFrame(extra_columns={"tag":"str"})
        for variable in self.variables.values():
            data = data.join(variable.mergeOutputData())
        return data.to_csv(header=include_header) # self.series[0].toCSV()
    def variablesToSeries(
            self,
            include_series_id : bool = False,
            use_node_id : bool = False
        ) -> List[Serie]:
        """
        return node variables as array of Series objects using self.variables.data as observaciones

        Parameters:
        -----------
        include_series_id : bool = False
            Add series_id property to items of Series
        
        use_node_id : bool = False
            Use node_id as series_id

        Returns:
        --------
        list of Series : List[Serie]
        """
        return [variable.toSerie(include_series_id=include_series_id,use_node_id=use_node_id) for variable in self.variables.values()]
    def variablesOutputToList(
            self,
            flatten : bool = True
        ) -> list:
        """
        For each variable in .variables, converts series_output to list of dict

        Parameters:
        -----------
        flatten : bool = True
            If True, merges observations into single list. Else, returns list of series objects: [{series_id:int, observaciones:[{obs1},{obs2},...]},...]
        
        Returns:
        --------
        list
        """
        list = []
        for variable in self.variables.values():
            output_list = variable.outputToList(flatten=flatten)
            if output_list is not None:
                list.extend(output_list)
        return list
    def variablesPronoToList(
            self,
            flatten : bool = True
        ) -> list:
        """
        For each variable in .variables, returns series_prono as a list
        
        Parameters:
        -----------
        flatten : bool = True
            If True, returns list of dict each containing one forecast time-value pair (pronosticos). Else returns list of dict each containing series_id:int and pronosticos:list 
        
        Returns:
        --------
        list
        """
        list = []
        for variable in self.variables.values():
            pronolist = variable.pronoToList(flatten=flatten)
            if pronolist is not None:
                list.extend(pronolist)
        return list
    def adjust(
        self,
        plot : bool = True,
        error_band : bool = True
        ) -> None:
        """For each variable in .variables, if adjust_from is set, run .adjust()
        
        Parameters:
        -----------
        plot : bool = True
            Generate plot
        
        error_band : bool = True
            Add 01-99 error band to result data"""
        for variable in self.variables.values():
            if variable.adjust_from is not None:
                variable.adjust(plot,error_band)
    def apply_linear_combination(
        self,
        plot : bool = True,
        series_index : int = 0
        ) -> None:
        """For each variable in .variables, if linear_combination is set, run .apply_linear_combination()
        
        Parameters:
        -----------
        plot : bool = True
            Generate plot
        
        series_index : int = 0
            Index of the series to apply the linear combination"""
        for variable in self.variables.values():
            if variable.linear_combination is not None:
                variable.apply_linear_combination(plot,series_index)
    def adjustProno(
        self,
        error_band : bool = True
        ) -> None:
        """For each variable in .variables run .adjustProno()
        
        Parameters:
        -----------
        error_band : bool = True
            Add 01-99 error band to result data"""
        for variable in self.variables.values():
            variable.adjustProno(error_band=error_band)
    def setOutputData(self) -> None:
        """For each variable in .variables run setOutputData()
        """
        for variable in self.variables.values():
            variable.setOutputData()
    def uploadData(
        self,
        include_prono : bool = False
        ) -> list:
        """For each variable in .variables run .uploadData()
        
        Parameters:
        -----------
        include_prono : bool = False
            Concatenate forecast into the data to upload

        Returns:
        --------
        created observations : list
        """
        created = []
        for variable in self.variables.values():
            result = variable.uploadData(include_prono=include_prono)
            created.extend(result)
        return created
    def pivotData(
        self,
        include_prono : bool = True
        ) -> DataFrame:
        """Join all variables' data into a single pivoted DataFrame
        
        Parameters:
        -----------
        include_prono : bool = False
            Concatenate forecast into the observed data

        Returns:
        --------
        joined, pivoted data : DataFrame
        """
        data = createEmptyObsDataFrame()
        for variable in self.variables.values():
            data = data.join(variable.pivotData(include_prono=include_prono))
        return data
    def pivotOutputData(
        self,
        include_tag : bool = True
        ) -> DataFrame:
        """Join all variables' output data into a single pivoted DataFrame
        
        Parameters:
        -----------
        include_tag : bool = True
            Include tag columns

        Returns:
        --------
        joined, pivoted data : DataFrame
        """
        data = createEmptyObsDataFrame()
        for variable in self.variables.values():
            data = data.join(variable.pivotOutputData(include_tag=include_tag))
        return data
    def seriesToDataFrame(
        self,
        pivot : bool = False,
        include_prono : bool = True
        ) -> DataFrame:
        """Join all variables' series data into a single DataFrame
        
        Parameters:
        -----------
        include_prono : bool = False
            Concatenate forecast into the observed data
        
        pivot : bool = True
            Pivot series into columns

        Returns:
        --------
        data : DataFrame
        """
        if pivot:
            data = self.pivotData(include_prono)
        else:
            data = createEmptyObsDataFrame()
            for variable in self.variables.values():
                data = data.append(variable.seriesToDataFrame(include_prono=include_prono),ignore_index=True)
        return data
    def saveSeries(
        self,
        output : str,
        format : str = "csv",
        pivot : bool = False
        ) -> None:
        """Join all variables' series data into a single DataFrame and save as csv or json file
        
        Parameters:
        -----------
        output : str
            File path where to save
        
        format : str = "csv"
            Output format, either "csv" or "json"
        
        pivot : bool = True
            Pivot series into columns
        """
        data = self.seriesToDataFrame(pivot=pivot)
        if format=="csv":
            return data.to_csv(output)
        else:
            return json.dump(data.to_dict(orient="records"),output)
    def concatenateProno(
        self,
        inline : bool = True,
        ignore_warmup : bool = True
        ) -> DataFrame:
        """Join every variable in .variables, run .concatenateProno().
        
        Parameters:
        -----------
        inline : bool = True
            If True, stores concatenation results into each variables' data
            If set to False, appends all results together and returns the resulting DataFrame
        
        ignore_warmup : bool = True
            Skips data values where timestart predates the forecast_date
        
        Returns:
        --------
        None or DataFrame
        """
        if inline:
            for variable in self.variables.values():
                variable.concatenateProno(inline=True,ignore_warmup=ignore_warmup)
        else:
            data = createEmptyObsDataFrame()
            for variable in self.variables.values():
                data = data.append(variable.concatenateProno(inline=False,ignore_warmup=ignore_warmup))
            return data
    def interpolate(
        self,
        limit : timedelta = None,
        extrapolate : bool = None
        ) -> None:
        """Join every variable in .variables, run .interpolate().
        
        Parameters:
        -----------
        limit : timedelta = None
            Maximum time distance to interpolate 
        
        extrapolate : bool = None
            If true, extrapolate data up to a distance of limit
        """
        for variable in self.variables.values():
                variable.interpolate(limit=limit,extrapolate=extrapolate)
    def plot(self) -> None:
        """
        For each variable of .variables run .plot()
        """
        for variable in self.variables.values():
            variable.plot()
    def plotProno(
        self,
        output_dir : str = None,
        figsize : tuple = None,
        title: str = None,
        markersize : int = None,
        obs_label : str = None,
        tz : str = None,
        prono_label : str = None,
        footnote : str = None,
        errorBandLabel : str = None,
        obsLine : bool = None,
        prono_annotation : str = None,
        obs_annotation : str = None,
        forecast_date_annotation : str = None,
        ylim : tuple = None,
        station_name : str = None,
        ydisplay : float = None,
        text_xoffset : float = None,
        xytext : tuple = None,
        datum_template_string : str = None,
        title_template_string : str = None,
        x_label : str = None,
        y_label : str = None,
        xlim : tuple = None
        ) -> None:
        """
        For each variable in .variables run .plotProno()

        Parameters:
        -----------
        output_dir : str = None
            Directory path where to save the plots

        figsize : tuple = None
            Figure size (width, height) in cm
        
        title: str = None
            Figure title
        
        markersize : int = None
            Size of marker in points
        
        obs_label : str = None
            Label for observed data

        tz : str = None
            Time zone for horizontal axis

        prono_label : str = None
            Label for forecast data

        footnote : str = None
            Footnote text
        
        errorBandLabel : str = None
            Label for error band
        
        obsLine : bool = None
            Add a line to observed data

        prono_annotation : str = None
            Annotation for forecast data

        obs_annotation : str = None
            Annotation for observed data

        forecast_date_annotation : str = None
            Annotation for forecast date

        ylim : tuple = None
            Y axis range (min, max)

        station_name : str = None
            Station name

        ydisplay : float = None
            Y position of annotations

        text_xoffset : float = None
            X offset of annotations
        
        xytext : tuple = None
            Not used
        
        datum_template_string : str = None
            Template string for datum text

        title_template_string : str = None
            Template string for title
        
        x_label : str = None
            Label for x axis

        y_label : str = None
            Label for y axis

        xlim : tuple = None
            Range of x axis (min, max)
        """
        for variable in self.variables.values():
            variable.plotProno(output_dir=output_dir,figsize=figsize,title=title,markersize=markersize,obs_label=obs_label,tz=tz,prono_label=prono_label,footnote=footnote,errorBandLabel=errorBandLabel,obsLine=obsLine,prono_annotation=prono_annotation,obs_annotation=obs_annotation,forecast_date_annotation=forecast_date_annotation,ylim=ylim,station_name=station_name,ydisplay=ydisplay,text_xoffset=text_xoffset,xytext=xytext,datum_template_string=datum_template_string,title_template_string=title_template_string,x_label=x_label,y_label=y_label,xlim=xlim)
    def loadData(
        self,
        timestart : Union[datetime,str,dict],
        timeend : Union[datetime,str,dict],
        include_prono : bool = True,
        forecast_timeend : Union[datetime,str,dict] = None
        ) -> None:
        """
        For each variable in variables, if variable is an ObservedNodeVariable run .loadData()
        
        Parameters:
        -----------
        timestart : Union[datetime,str,dict]
            Begin date

        timeend : Union[datetime,str,dict]
            End date

        include_prono : bool = True
            For each variable, load forecast data for each series of .series_prono 
        
        forecast_timeend : Union[datetime,str,dict] = None
            End date of forecast retrieval. If None, uses timeend
        """
        for variable in self.variables.values():
            if isinstance(variable,ObservedNodeVariable):
                variable.loadData(timestart,timeend,include_prono,forecast_timeend)
    def removeOutliers(self) -> bool:
        """
        For each variable of .variables, if variable is an ObservedNodeVariable, run .removeOutliers(). Removes outilers and returns True if any outliers were removed
        
        Returns:
        --------
        bool"""
        found_outliers = False
        for variable in self.variables.values():
            if isinstance(variable,ObservedNodeVariable):
                found_outliers_ = variable.removeOutliers()
                found_outliers = found_outliers_ if found_outliers_ else found_outliers
        return found_outliers
    def detectJumps(self) -> bool:
        """
        For each variable of .variables, if variable is an ObservedNodeVariable, run .detectJumps(). Returns True if any jumps were found
        
        Returns:
        --------
        bool"""
        found_jumps = False
        for variable in self.variables.values():
            if isinstance(variable,ObservedNodeVariable):
                found_jumps_ = variable.detectJumps()
                found_jumps = found_jumps_ if found_jumps_ else found_jumps
        return found_jumps
    def applyOffset(self) -> None:
        """
        For each variable of .variables, if variable is an ObservedNodeVariable, run .applyOffset()
        """
        for variable in self.variables.values():
            if isinstance(variable,ObservedNodeVariable):
                variable.applyOffset()
    def regularize(
        self,
        interpolate : bool = False
        ) -> None:
        """
        For each variable of .variables, if variable is an ObservedNodeVariable, run .regularize(). 

        Parameters:
        -----------
        interpolate : bool = False
            Interpolate missing values
        """
        for variable in self.variables.values():
            if isinstance(variable,ObservedNodeVariable):
                variable.regularize(interpolate=interpolate)
    def fillNulls(
        self,
        inline : bool =True,
        fill_value : float = None
        ) -> None:
        """
        For each variable of .variables, if variable is an ObservedNodeVariable, run .fillNulls(). 

        Parameters:
        -----------
        inline : bool = True
            Store result in variables' data property
        
        fill_value : float = None
            Fill missing values with this value
        """
        for variable in self.variables.values():
            if isinstance(variable,ObservedNodeVariable):
                variable.fillNulls(inline,fill_value)
    def derive(self) -> None:
        """For each variable of .variables, if variable is a DerivedNodeVariable, run .derive()"""
        for variable in self.variables.values():
            if isinstance(variable,DerivedNodeVariable):
                variable.derive()
    def applyMovingAverage(self) -> None:
        """For each variable of .variables fun applyMovingAverage()"""
        for variable in self.variables.values():
            variable.applyMovingAverage()
