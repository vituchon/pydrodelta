import yaml
import os
from datetime import datetime, timedelta
import json
import logging
from pandas import concat
import networkx as nx
from networkx.readwrite import json_graph
import matplotlib.pyplot as plt
from typing import Union, List
from pandas import DataFrame

from .a5 import Crud, createEmptyObsDataFrame
from .topology import Topology
import pydrodelta.util as util
from .procedure import Procedure
from .validation import getSchemaAndValidate
from .descriptors.string_descriptor import StringDescriptor
from .descriptors.int_descriptor import IntDescriptor
from .descriptors.bool_descriptor import BoolDescriptor

from pydrodelta.config import config

output_crud = Crud(config["output_api"])

class Plan():
    """
    Use this class to set up a modelling configuration, including the topology and the procedures.

    A plan is the root element of a pydro configuration

    """
    name = StringDescriptor()
    """name of the plan"""
    id = IntDescriptor()
    """numeric id of the plan. Used as identifier when saving into the output api"""
    # @property
    # def id(self):
    #     """numeric id of the plan. Used as identifier when saving into the output api"""
    #     return self._id
    # @id.setter
    # def id(self,value : int):
    #     self._id = int(value)
    @property
    def topology(self):
        """Unordered list of nodes which represent stations and basins"""
        return self._topology
    @topology.setter
    def topology(self,value : Union[dict,Topology,str,None]):
        if isinstance(value, dict):
            self._topology = Topology(**value,plan=self)
        elif isinstance(value, Topology):
            self._topology = value
        elif isinstance(value, str):
            topology_file_path = os.path.join(os.environ["PYDRODELTA_DIR"],value)
            f = open(topology_file_path)
            self._topology = Topology(**yaml.load(f,yaml.CLoader),plan=self)
            f.close()
        elif isinstance(value,None):
            self._topology = None
        else:
            raise ValueError("Topology must be a dict, Topology, str or None")
    @property
    def procedures(self):
        """Ordered list of procedures (of class Procedure). On .execute(), they are executed sequentially. The results are read and saved into the topology according to the mapping configuration in procedure.function.boundaries and procedure.function.outputs respectively, so that the procedures read the updated data generated by previous procedures"""
        return self._procedures
    @procedures.setter
    def procedures(self,values : list):
        self._procedures = [x if isinstance(x,Procedure) else Procedure(**x,plan=self) for x in values]
    @property
    def forecast_date(self):
        """Execution timestamp of the plan. Defaults to now rounded down to .time_interval"""
        return self._forecast_date
    @forecast_date.setter
    def forecast_date(self,value):
        self._forecast_date = util.tryParseAndLocalizeDate(value)
        if self.forecast_date is not None and self.time_interval is not None:
            self._forecast_date = util.roundDownDate(self.forecast_date,self.time_interval)
    @property
    def time_interval(self):
        """time step duration of the procedures"""
        return self._time_interval
    @time_interval.setter
    def time_interval(self,value):
        self._time_interval = util.interval2timedelta(value) if value is not None else None
        if self.time_interval is not None and self.forecast_date is not None:
            self.forecast_date = util.roundDownDate(self.forecast_date,self.time_interval)
    output_stats_file = StringDescriptor()
    """file path where to save result statistics"""
    output_analysis = StringDescriptor()
    """file path where to save analysis results"""
    pivot = BoolDescriptor()
    """option to pivot the results table (set one column per variable). Default False"""
    save_post = StringDescriptor()
    """file path where to save the post data sent to the output api"""
    save_response = StringDescriptor()
    """file path where to save the output api response"""
        
    def __init__(
            self,
            name : str,
            id: int,
            topology: Union[dict, str],
            procedures: list = [],
            forecast_date: Union[dict, str] = datetime.now().isoformat(),
            time_interval: Union[dict, str] = None,
            output_stats: str = None,
            output_analysis: str = None,
            pivot: bool = False,
            save_post: str = None,
            save_response: str = None
            ):
        """
        A plan defines a modelling configuration, including the topology, the procedures, the forecast date, time interval and output options. It is the root element of a pydro configuration

        Parameters:
        -----------

        name : str
            Name of the plan        
        
        id : int
            numeric id of the plan. Used as identifier when saving into the output api
        
        topology : dict or filepath
            Either topology configuration dict or a topology configuration file path (see Topology)
        
        procedures : list
            List of procedure dicts (see Procedure)
        
        forecast_date : str or dict
            Execution timestamp of the plan. Defaults to now rounded down to time_interval
        
        time_interval : str or dict
            time step duration of the procedures
        
        output_stats : str or None
            file path where to save result statistics
        
        output_analysis : str or None
            file path where to save analysis results
        
        pivot : bool
            option to pivot the results table (set one column per variable). Default False
        
        save_post : str or None
            file path where to save the post data sent to the output api
        
        save_response : str or None
            file path where to save the output api response
        
        """
        getSchemaAndValidate(params=locals(), name="plan")

        self.name = name
        self.id = id
        self.topology = topology
        self.procedures = procedures
        self._forecast_date : datetime = None
        self._time_interval : timedelta = None
        self.forecast_date = forecast_date
        self.time_interval = time_interval
        self.output_stats_file = output_stats
        self.output_analysis = output_analysis
        self.pivot = pivot
        self.save_post = save_post
        self.save_response = save_response
    def execute(self,include_prono=True,upload=True,pretty=False):
        """
        Runs analysis and then each procedure sequentially

        Parameters:
        -----------

        include_prono : bool
            If True (default), concatenates observed and forecasted boundary conditions. Else, reads only observed data.
        
        upload : bool
            If True (default), Uploads result into output api.
        
        pretty : bool
            Pretty print results. Default False

        Returns:
        --------
        
        None
        """
        self.topology.batchProcessInput(include_prono=include_prono)
        if self.output_analysis is not None:
            with open(self.output_analysis,'w') as analysisfile:
                if pretty:
                    json.dump(self.topology.toList(pivot=self.pivot),analysisfile,indent=4)
                else:
                    json.dump(self.topology.toList(pivot=self.pivot),analysisfile)
        for procedure in self.procedures:
            if procedure.calibration is not None and procedure.calibration.calibrate:
                procedure.calibration.run()
            else:
                procedure.run()
            procedure.outputToNodes()
            # logging.debug("statistics type: %s" % type(procedure.procedure_function_results.statistics))
            # self.output_stats.append(procedure.procedure_function_results.statistics)
        if upload:
            try:
                self.uploadSim()
            except Exception as e:
                logging.error("Failed to create corrida at database API: upload failed: %s" % str(e))
        if self.output_stats_file is not None:
            with open(self.output_stats_file,"w") as outfile:
                json.dump([p.read_results() for p in self.procedures], outfile, indent=4) # json.dump([p.read_statistics() for p in self.procedures],outfile,indent=4) # [o.__dict__ for o in self.output_stats],outfile)
    def toCorrida(self) -> dict:
        """Convert simulation results into dict according to alerta5DBIO schema (https://raw.githubusercontent.com/jbianchi81/alerta5DBIO/master/public/schemas/a5/corrida.yml)
        
        Returns:
        --------
        
        dict
        """
        series_sim = []
        for node in self.topology.nodes:
            for variable in node.variables.values():
                if variable.series_sim is not None:
                    for serie in variable.series_sim:
                        if serie.upload:
                            if serie.data is None:
                                logging.warn("Missing data for series sim:%i, variable:%i, node:%i" % (serie.series_id, variable.id, node.id))
                                continue
                            series_sim.append({
                                "series_id": serie.series_id,
                                "series_table": serie.getSeriesTable(),
                                "pronosticos": serie.toList(remove_nulls=True)
                            })
        return {
            "cal_id": self.id,
            "forecast_date": self.forecast_date.isoformat(),
            "series": series_sim 
        }
    def uploadSim(self) -> dict:
        """Upload forecast into output api. 
        
        If self.save_post is not None, saves the post message before request into that filepath. 

        If self.save_response not None, saves server response (either the created forecast or an error message) into that filepath
        
        Returns:
        --------
        
        dict : created forecast
        """
        corrida = self.toCorrida()
        if self.save_post is not None:
            save_path = "%s/%s" % (os.environ["PYDRODELTA_DIR"], self.save_post)
            json.dump(corrida,open(save_path,"w"))
            logging.info("Saved simulation post data to %s" % save_path)
        response = output_crud.createCorrida(corrida)
        if self.save_response:
            save_path = "%s/%s" % (os.environ["PYDRODELTA_DIR"], self.save_response)
            json.dump(corrida,open(save_path,"w"))
            logging.info("Saved simulation post response to %s" % save_path)
        return response
    def toCorridaJson(self,filename,pretty=False) -> None:
        """
        Saves forecast into filename (json) using alerta5DBIO schema (https://raw.githubusercontent.com/jbianchi81/alerta5DBIO/master/public/schemas/a5/corrida.yml)

        Parameters:
        -----------
        filename : str
            File path where to save
        
        pretty : bool
            Pretty-print JSON (default False)
        
        Returns:
        --------

        None
        """
        corrida = self.toCorrida()
        f = open(filename,"w")
        if pretty:
            f.write(json.dumps(corrida,indent=4))
        else:
            f.write(json.dumps(corrida))
        f.close()
    def toCorridaDataFrame(self,pivot=False) -> DataFrame:
        """
        Concatenates forecast data into a DataFrame

        Parameters:
        -----------
        pivot : bool
            Pivot the DataFrame with one column per variable grouping by timestamp. Default False
        
        Returns:
        --------

        DataFrame
        """
        corrida = createEmptyObsDataFrame(extra_columns={"tag":"str","series_id":"int"})
        for node in self.topology.nodes:
            for variable in node.variables.values():
                if variable.series_sim is not None:
                    for serie in variable.series_sim:
                        if serie.data is None:
                            logging.warn("Missing data for series sim:%i, variable:%i, node:%i" % (serie.series_id, variable.id, node.id))
                            continue
                        if pivot:
                            suffix = "_%i" % serie.series_id
                            corrida = corrida.join(serie.data,rsuffix=suffix,how="outer")
                            corrida = corrida.rename(columns={"valor_%i" % serie.series_id: str(serie.series_id)})
                        else:
                            data = serie.data.copy()
                            data["series_id"] = serie.series_id
                            corrida = concat([corrida,data])
        if pivot:
            del corrida["valor"]
            del corrida["tag"]
            del corrida["series_id"]
        return corrida
                
    def toCorridaCsv(self,filename,pivot=False,include_header=True) -> None:
        """
        Saves forecast as csv

        Parameters:
        -----------

        filename : str
            Where to save the csv file

        pivot : bool
            Pivot the table with one column per variable grouping by timestamp. Default False
        
        include_header : bool
            Add a header to the csv file. Default True
        
        Returns:
        --------

        None
        """
        corrida = self.toCorridaDataFrame(pivot=pivot)
        corrida.to_csv(filename,header=include_header)
    
    def toGraph(self,nodes : Union[list,None]) -> nx.DiGraph:
        """
        Generate directioned graph from the plan. Topology nodes are linked to procedures according to the mapping provided at procedure.function.boundaries (node to procedure) and procedure.function.outputs (procedure to node)

        Parameters:
        -----------
        nodes : list or None
            List of nodes to use for building the graph. If None, uses self.topology.nodes 
        
        Returns:
        --------
        NetworkX.DiGraph (See https://networkx.org for complete documentation)

        See also:
        ---------
        printGraph
        exportGraph

        """
        DG = self.topology.toGraph(nodes)
        edges = list()
        for procedure in self.procedures:
            proc_id = "procedure_%s" % procedure.id
            proc_dict = procedure.toDict()
            proc_dict["node_type"] = "procedure"
            # logging.debug(proc_dict)
            for key in proc_dict:
                # logging.debug("proc_dict['%s']:" % key)
                # logging.debug(proc_dict[key])
                try:
                    json.dumps(proc_dict[key])
                except TypeError as e:
                    logging.error("proc_dict['%s'] is not JSON serializable." % key)
                    raise(e)
            DG.add_node(proc_id,object=proc_dict)
            for b in procedure.function.boundaries:
                edges.append((b.node_id, proc_id))
            for o in procedure.function.outputs:
                edges.append((proc_id,o.node_id))
        for edge in edges:
            if not DG.has_node(edge[1]):
                raise Exception("Topology error: missing downstream node %s at node %s" % (edge[1], edge[0]))
            DG.add_edge(edge[0],edge[1])
        return DG

    def printGraph(
            self,
            nodes : Union[list,None]=None,
            output_file : Union[str,None]=None
        ) -> None:
        """Print directioned graph from the plan. Topology nodes are linked to procedures according to the mapping provided at procedure.function.boundaries (node to procedure) and procedure.function.outputs (procedure to node)
        
        Parameters:
        -----------        
        nodes : list or None
            List of nodes to use for building the graph. If None, uses self.topology.nodes 
        
        output_file : str
            Where to save the graph file
        
        Returns:
        --------
        None
        
        See also:
        ---------
        toGraph
        exportGraph
        """
        DG = self.toGraph(nodes)
        attrs = nx.get_node_attributes(DG, 'object') 
        labels = {}
        colors = []
        for key in attrs:
            labels[key] = attrs[key]["name"] if "name" in attrs[key] else attrs[key]["id"] if "id" in attrs[key] else "N"
            colors.append("blue" if attrs[key]["node_type"] == "basin" else "yellow" if attrs[key]["node_type"] == "procedure" else "red")
        logging.debug("nodes: %i, attrs: %s, labels: %s, colors: %s" % (DG.number_of_nodes(), str(attrs.keys()), str(labels.keys()), str(colors)))
        plt.figure(figsize=(config["graph"]["width"],config["graph"]["height"]))
        nx.draw_networkx(DG, with_labels=True, font_weight='bold', labels=labels, node_color=colors, node_size=100, font_size=9)
        if output_file is not None:
            plt.savefig(output_file, format='png')
            plt.close()

    def exportGraph(self,nodes : Union[list,None]=None,output_file : Union[str,None]=None) -> Union[str,None]:
        """Creates directioned graph from the plan and converts it to JSON. Topology nodes are linked to procedures according to the mapping provided at procedure.function.boundaries (node to procedure) and procedure.function.outputs (procedure to node)
        
        Parameters:
        -----------        
        nodes : list or None
            List of nodes to use for building the graph. If None, uses self.topology.nodes 
        
        output_file : str or None
            Where to save the JSON file. If None, returns the JSON string
        
        Returns:
        --------
        str or None
        
        See also:
        ---------
        toGraph
        printGraph
        """
        DG = self.toGraph(nodes)
        # NLD = nx.node_link_data(DG)
        if output_file is not None:
            with open(output_file,"w") as f:
                f.write(json.dumps(json_graph.node_link_data(DG),indent=4)) # json.dumps(NLD,indent=4))
                f.close()
        else:
            return json.dumps(json_graph.node_link_data(DG),indent=4)
    
