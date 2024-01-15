from pydrodelta.procedure_function import ProcedureFunction, ProcedureBoundary
import logging
import json
import pydrodelta.util as util
from pydrodelta.a5 import createEmptyObsDataFrame
from pydrodelta.result_statistics import ResultStatistics
from pydrodelta.procedure_function_results import ProcedureFunctionResults


class Procedure():
    """
    A Procedure defines an hydrological, hydrodinamic or static procedure which takes one or more NodeVariables from the Plan as boundary condition, one or more NodeVariables from the Plan as outputs and a ProcedureFunction. The input is read from the selected boundary NodeVariables and fed into the ProcedureFunction which produces an output, which is written into the output NodeVariables
    """
    def __init__(self,params,plan):
        self.id = params["id"]
        self._plan = plan
        self.initial_states = params["initial_states"] if "initial_states" in params else []
        if params["function"]["type"] in procedureFunctionDict:
            self.function_type = procedureFunctionDict[params["function"]["type"]]
            self.function_type_name = params["function"]["type"]
        else:
            logging.warn("Procedure init: class %s not found. Instantiating abstract class ProcedureFunction" % params["function"]["type"])
            self.function_type = ProcedureFunction
            self.function_type_name = "ProcedureFunction"
        # self.function = self.function_type(params["function"])
        if isinstance(params["function"],dict): # read params from dict
            self.function = self.function_type(params["function"],self)
        else: # if not, read from file
            f = open(params["function"])
            self.function = self.function_type(json.load(f),self)
            f.close()
        # self.procedure_type = params["procedure_type"]
        self.parameters = params["parameters"] if "parameters" in params else []
        self.time_interval = util.interval2timedelta(params["time_interval"]) if "time_interval" in params else None
        self.time_offset = util.interval2timedelta(params["time_offset"]) if "time_offset" in params else None
        self.input = None # <- boundary conditions
        self.output = None # <- outputs
        self.output_obs = None # <- observed values for error calculation
        self.states = None
        self.procedure_function_results = None
        self.save_results = params["save_results"] if "save_results" in params else None
    def toDict(self):
        return {
            "id": self.id,
            "function": self.function.toDict()
        }
    def loadInput(self,inplace=True,pivot=False):
        """
        Carga las variables de borde definidas en self.boundaries. De cada elemento de self.boundaries toma .data y lo concatena en una lista. Si pivot=True, devuelve un DataFrame con 
        """
        if pivot:
            data = createEmptyObsDataFrame(extra_columns={"tag":str})
            columns = ["valor","tag"]
            for boundary in self.function.boundaries:
                if boundary._variable.data is not None and len(boundary._variable.data):
                    rsuffix = "_%s_%i" % (str(boundary.node_id), boundary.var_id) 
                    data = data.join(boundary._variable.data[columns][boundary._variable.data.valor.notnull()],how='outer',rsuffix=rsuffix,sort=True)
            for column in columns:
                del data[column]
            # data = data.replace({np.NaN:None})
        else:
            data = []
            for boundary in self.function.boundaries:
                logging.debug("loading boundary: %s: node %i, variable %i, optional: %s, warmup_only: %s" % (boundary.name, boundary.node_id,boundary.var_id, str(boundary.optional), str(boundary.warmup_only)))
                if not boundary.optional:
                    try:
                        warmup_only = boundary.warmup_only if boundary.warmup_only else False
                        boundary.assertNoNaN(warmup_only)
                    except AssertionError as e:
                        raise Exception("load input error at procedure %s, node %i, variable, %i: %s" % (self.id, boundary.node_id, boundary.var_id, str(e)))
                data.append(boundary._variable.data.copy())
        if inplace:
            self.input = data
        else:
            return data
    def loadOutputObs(self,inplace=True,pivot=False):
        """
            Carga las variables de output definidas en self.outputs. Para cálculo de error.
        """
        if pivot:
            data = createEmptyObsDataFrame()
            for i, output in enumerate(self.function.outputs):
                if output._variable.data is not None and len(output._variable.data):
                    colname = "valor_%i" % (i + 1) 
                    data = data.join(output._variable.data[["valor"]].rename(columns={"valor": colname}).dropna(),how='outer',sort=True)
                else:
                    logging.warn("loadOutputObs: Procedure: %s, output: %i, with no data. Skipped." % (self.id,i))
            # logging.debug("loadOutputObs: columns: %s" % (data.columns))
            if "valor" in data.columns:
                data.drop(columns="valor",inplace=True)
        else:
            data = []
            for output in self.function.outputs:
                data.append(output._variable.data[["valor"]].dropna())
        if inplace:
            self.output_obs = data
        else:
            return data
    def computeStatistics(self, obs:list|None=None, sim:list|None=None) -> list[ResultStatistics]:
        obs = obs if obs is not None else self.output_obs
        sim = sim if sim is not None else self.output
        result = list()
        # if len(obs) < len(sim):
        #     raise Exception("length of obs must be equal than length of sim")
        for i, o in enumerate(self.function.outputs):
            if len(sim) < i + 1:
                raise Exception("List of sim outputs is shorter than function.outputs (%i < %i" % (len(sim), len(self.function.outputs)))
            if len(obs) < i + 1:
                raise Exception("List of obs outputs is smaller than function.outputs (%i < %i" % (len(obs), len(self.function.outputs)))
            inner_join = sim[i][["valor"]].rename(columns={"valor":"sim"}).join(obs[i][["valor"]].rename(columns={"valor":"obs"}),how="inner").dropna()
            result.append(ResultStatistics({
                "obs": inner_join["obs"].values, 
                "sim": inner_join["sim"].values, 
                "compute": o.compute_statistics, 
                "metadata": o.__dict__()
            }))
        if self.procedure_function_results is not None:
            self.procedure_function_results.setStatistics(result)
        return result
    
    def read_statistics(self):
        return {
            "procedure_id": self.id,
            "function_type": self.function_type_name,
            "results": [x.toDict() if x is not None else None for x in self.procedure_function_results.statistics]
        }
    def read_results(self):
        return {
            "procedure_id": self.id,
            "function_type": self.function_type_name,
            "results": self.procedure_function_results.toDict() if self.procedure_function_results is not None else None
        }
    def run(self,inplace=True,save_results=None):
        """
        Run self.function.run()

        :param inplace: if True, writes output to self.output, else returns output (array of seriesData)
        """
        save_results = save_results if save_results is not None else self.save_results
        # loads input inplace
        input = self.loadInput(inplace)
        # runs procedure function
        output, procedure_function_results = self.function.run(input=input)
        # sets procedure_function_results
        self.procedure_function_results = procedure_function_results if type(procedure_function_results) == ProcedureFunctionResults else ProcedureFunctionResults(procedure_function_results)
        # loads observed outputs
        output_obs = self.loadOutputObs(inplace)
        # sets states
        if self.procedure_function_results.states is not None:
            self.states = self.procedure_function_results.states
        # compute statistics
        if inplace:
            self.output = output
            self.computeStatistics()
        else:
            self.computeStatistics(obs=output_obs,sim=output)
        # saves results to file
        if save_results is not None:
            self.procedure_function_results.save(output=save_results)
        # returns
        if inplace:
            return
        else:
            return output
    def getOutputNodeData(self,node_id,var_id,tag=None):
        """
        Extracts single series from output using node id and variable id

        :param node_id: node id
        :param var_id: variable id
        :returns: timeseries dataframe
        """
        index = 0
        for o in self.outputs:
            if o.var_id == var_id and o.node_id == node_id:
                if self.output is not None and len(self.output) <= index + 1:
                    return self.output[index]
            index = index + 1
        raise("Procedure.getOutputNodeData error: node with id: %s , var %i not found in output" % (str(node_id), var_id))
        # col_rename = {}
        # col_rename[node_id] = "valor"
        # data = self.output[[node_id]].rename(columns = col_rename)
        # if tag is not None:
        #     data["tag"] = tag
        # return data
    def outputToNodes(self):
        if self.output is None:
            logging.error("Procedure output is None, which means the procedure wasn't run yet. Can't perform outputToNodes.")
            return
        # output_columns = self.output.columns
        index = 0
        for o in self.function.outputs:
            if o._variable.series_sim is None:
                logging.warn("series_sim not defined for output %s" % o.name)
                continue
            if index + 1 > len(self.output):
                logging.error("Procedure output for node %s variable %i not found in self.output. Skipping" % (str(o.node_id),o.var_id))
                continue
            o._variable.concatenate(self.output[index])
            for serie in o._variable.series_sim:
                # logging.debug("output serie %i, data: %s" % (index, str(self.output[index])))
                serie.setData(data=self.output[index]) # self.getOutputNodeData(o.node_id,o.var_id))
                serie.applyOffset()
            index = index + 1
    
from pydrodelta.procedures.hecras import HecRasProcedureFunction
from pydrodelta.procedures.polynomial import PolynomialTransformationProcedureFunction
from pydrodelta.procedures.muskingumchannel import MuskingumChannelProcedureFunction
from pydrodelta.procedures.grp import GRPProcedureFunction
from pydrodelta.procedures.linear_combination import LinearCombinationProcedureFunction
from pydrodelta.procedures.expression import ExpressionProcedureFunction
from pydrodelta.procedures.sacramento_simplified import SacramentoSimplifiedProcedureFunction
from pydrodelta.procedures.sac_enkf import SacEnkfProcedureFunction
from pydrodelta.procedures.junction import JunctionProcedureFunction
from pydrodelta.procedures.linear_channel import LinearChannelProcedureFunction
from pydrodelta.procedures.uh_linear_channel import UHLinearChannelProcedureFunction
from pydrodelta.procedures.gr4j import GR4JProcedureFunction
from pydrodelta.procedures.linear_combination_2b import LinearCombination2BProcedureFunction
from pydrodelta.procedures.linear_combination_3b import LinearCombination3BProcedureFunction
from pydrodelta.procedures.linear_combination_4b import LinearCombination4BProcedureFunction

procedureFunctionDict = {
    "ProcedureFunction": ProcedureFunction,
    "HecRas": HecRasProcedureFunction,
    "HecRasProcedureFunction": HecRasProcedureFunction,
    "PolynomialTransformationProcedureFunction": PolynomialTransformationProcedureFunction,
    "Polynomial": PolynomialTransformationProcedureFunction,
    "MuskingumChannel": MuskingumChannelProcedureFunction,
    "MuskingumChannelProcedureFunction": MuskingumChannelProcedureFunction,
    "GRP": GRPProcedureFunction,
    "GRPProcedureFunction": GRPProcedureFunction,
    "LinearCombination": LinearCombinationProcedureFunction,
    "LinearCombination2B": LinearCombination2BProcedureFunction,
    "LinearCombination3B": LinearCombination3BProcedureFunction,
    "LinearCombination4B": LinearCombination4BProcedureFunction,
    "Expression": ExpressionProcedureFunction,
    "SacramentoSimplified": SacramentoSimplifiedProcedureFunction,
    "SacEnKF": SacEnkfProcedureFunction,
    "Junction": JunctionProcedureFunction,
    "LinearChannel": LinearChannelProcedureFunction,
    "UHLinearChannel": UHLinearChannelProcedureFunction,
    "GR4J": GR4JProcedureFunction
}