from pydrodelta.procedure_function import ProcedureFunction
from pydrodelta.validation import getSchema, validate
from pydrodelta.function_boundary import FunctionBoundary
import logging

schemas, resolver = getSchema("PQProcedureFunction","data/schemas/json")
schema = schemas["PQProcedureFunction"]

class PQProcedureFunction(ProcedureFunction):
    _boundaries = [
        FunctionBoundary({"name": "pma"}),
        FunctionBoundary({"name": "etp"}),
        FunctionBoundary({"name": "q_obs", "optional": True}),
        FunctionBoundary({"name": "smc_obs", "optional": True})
    ]
    _outputs = [
        FunctionBoundary({"name": "q_sim"}),
        FunctionBoundary({"name": "smc_sim"})
    ]
    def __init__(self,params,procedure):
        # logging.debug("Running PQProcedureFunction constructor")
        super().__init__(params,procedure) # super(ProcedureFunction,self).__init__(params,procedure)
        validate(params,schema,resolver)
        if "fill_nulls" in self.extra_pars:
            self.fillnulls = bool(self.extra_pars["fill_nulls"])
        else:
            self.fillnulls = False
        logging.debug("fillnulls: %s" % str(self.fillnulls))
        if self.fillnulls:
            logging.debug("fillnulls: setting pma boundary to optional")
            self.boundaries[0].optional = True
        #### area basin area in square meters
        # logging.debug("extra_pars: %s" % self.extra_pars)
        self.area = float(self.extra_pars["area"])
        self.ae = float(self.extra_pars["ae"]) if "ae" in self.extra_pars else 1
        self.rho = float(self.extra_pars["rho"]) if "rho" in self.extra_pars else 0.5
        self.wp = float(self.extra_pars["wp"]) if "wp" in self.extra_pars else 0.03
        # self.parameters = params["parameters"] if "parameters" in params else {}
        # self.initial_states = params["initial_states"] if "initial_states" in params else {}
