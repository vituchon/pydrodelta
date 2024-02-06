import yaml
import os
from datetime import datetime 
import json
import logging
from pandas import concat
import networkx as nx
from networkx.readwrite import json_graph
import matplotlib.pyplot as plt
from typing import Union, List

from pydrodelta.a5 import Crud, createEmptyObsDataFrame
from pydrodelta.topology import Topology
import pydrodelta.util as util
from pydrodelta.procedure import Procedure
from pydrodelta.validation import getSchemaAndValidate

from pydrodelta.config import config

output_crud = Crud(config["output_api"])

class Plan():
    """
    Use this class to set up a modelling configuration, including the topology and the procedures.

    A plan is the root element of a pydro configuration

    """
    
    def __init__(
            self,
            name : str,
            id: int,
            topology: Union[dict, str],
            procedures: list = [],
            forecast_date: Union[dict, str] = datetime.now(),
            time_interval: Union[dict, str] = None,
            output_stats: str = None,
            output_analysis: str = None,
            pivot: bool = False,
            save_post: str = None,
            save_response: str = None
            ):
        """
        Constructor of the class

        :param name: Name of the plan        
        :param id: numeric id of the plan. Used as identifier when saving into the output api
        :param topology: Either topology dict or a topology file path
        :param procedures: list of procedure dicts
        :param forecast_date: timestamp of the plan execution
        :param time_interval: time step duration of the procedures
        :param output_stats: file path where to save result statistics
        :param output_analysis: file path where to save analysis results
        :param pivot: option to pivot the results table (set one column per variable)
        :param save_post: file path where to save the post data sent to the output api
        :param save_response: file path where to save the output api response
        """
        getSchemaAndValidate(params=locals(), name="plan")

        self.name : str = name
        """name of the plan"""

        self.id : int = id
        """numeric id of the plan. Used as identifier when saving into the output api"""

        self.topology : Topology = None
        """Unordered list of nodes which represent stations and basins"""

        if isinstance(topology,dict):
            self.topology = Topology(topology)
        else:
            topology_file_path = os.path.join(os.environ["PYDRODELTA_DIR"],topology)
            f = open(topology_file_path)
            self.topology = Topology(yaml.load(f,yaml.CLoader),plan=self)
            f.close()
        self.procedures = [Procedure(**x,plan=self) for x in procedures]
        self.forecast_date = util.tryParseAndLocalizeDate(forecast_date)
        self.time_interval = util.interval2timedelta(time_interval) if time_interval is not None else None
        if self.time_interval is not None:
            self.forecast_date = util.roundDownDate(self.forecast_date,self.time_interval)
        # self.output_stats = []
        self.output_stats_file = output_stats
        self.output_analysis = output_analysis
        self.pivot = pivot
        self.save_post = save_post
        self.save_response = save_response
    def execute(self,include_prono=True,upload=True,pretty=False):
        """
        Runs analysis and then each procedure sequentially

        :param include_prono: if True (default), concatenates observed and forecasted boundary conditions. Else, reads only observed data.
        :type include_prono: bool
        :param upload: if True (default), Uploads result into output api.
        :type upload: bool
        :param pretty: Pretty print results.
        :type pretty: bool
        :returns: None
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
    def toCorrida(self):
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
    def uploadSim(self):
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
    def toCorridaJson(self,filename,pretty=False):
        """
        Guarda corrida en archivo .json
        """
        corrida = self.toCorrida()
        f = open(filename,"w")
        if pretty:
            f.write(json.dumps(corrida,indent=4))
        else:
            f.write(json.dumps(corrida))
        f.close()
    def toCorridaDataFrame(self,pivot=False):
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
                
    def toCorridaCsv(self,filename,pivot=False,include_header=True):
        """
        Guarda corrida en archivo .csv
        """
        corrida = self.toCorridaDataFrame(pivot=pivot)
        corrida.to_csv(filename,header=include_header)
    
    def toGraph(self,nodes):
        DG = self.topology.toGraph(nodes)
        edges = list()
        for procedure in self.procedures:
            proc_id = "procedure_%s" % procedure.id
            proc_dict = procedure.toDict()
            proc_dict["node_type"] = "procedure"
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

    def printGraph(self,nodes=None,output_file=None):
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

    def exportGraph(self,nodes=None,output_file=None):
        DG = self.toGraph(nodes)
        # NLD = nx.node_link_data(DG)
        if output_file is not None:
            with open(output_file,"w") as f:
                f.write(json.dumps(json_graph.node_link_data(DG),indent=4)) # json.dumps(NLD,indent=4))
                f.close()
        else:
            return json.dumps(json_graph.node_link_data(DG),indent=4)
    
