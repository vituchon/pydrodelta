from pydrodelta.procedure_function import ProcedureFunction, ProcedureFunctionResults
from pydrodelta.validation import getSchema, validate
from pydrodelta.function_boundary import FunctionBoundary
import numpy as np

schemas, resolver = getSchema("JunctionProcedureFunction","data/schemas/json")
schema = schemas["JunctionProcedureFunction"]

class JunctionProcedureFunction(ProcedureFunction):
    _boundaries = [
        FunctionBoundary({"name": "input_1"}),
        FunctionBoundary({"name": "input_2"})
    ]
    _additional_boundaries = True
    _outputs = [
        FunctionBoundary({"name": "output"})
    ]
    def __init__(self,params,procedure):
        """
        Adds input_1 with input_2 (and input_3, etc... if present) and saves into output_2
        """
        super().__init__(params,procedure)
        validate(params,schema,resolver)
    def run(self,input=None):
        """
        Ejecuta la función. Si input es None, ejecuta self._procedure.loadInput para generar el input. input debe ser una lista de objetos SeriesData
        Devuelve una lista de objetos SeriesData y opcionalmente un objeto ProcedureFunctionResults
        """
        if input is None:
            input = self._procedure.loadInput(inplace=False,pivot=False)
        output = input[0][["valor"]].rename(columns={"valor": "valor_1"})
        output["valor"] = output["valor_1"]
        for i, serie in enumerate(input):
            if i == 0:
                continue
            colname = "input_%i" % (i + 1)
            output = output.join(serie[["valor"]].rename(columns={"valor":colname}))
            output["valor"] = output.apply(lambda row: row['valor'] + row[colname] if not np.isnan(row['valor']) and not np.isnan(row[colname]) else None, axis=1)
        # results_data = output.join(output_obs[["valor_1"]].rename(columns={"valor_1":"valor_obs"}),how="outer")
        return (
            [output[["valor"]]], 
            ProcedureFunctionResults({
                "border_conditions": input,
                "data": output
            })
        )