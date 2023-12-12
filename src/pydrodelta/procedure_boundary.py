# from pydrodelta.node_variable import NodeVariable 

class ProcedureBoundary():
    """
    A variable at a node which is used as a procedure boundary condition
    """
    def __init__(self,params,plan=None,optional=False):
        self.optional = optional
        print("params: %s" % str(params))
        self.node_id = int(params[0])
        self.var_id = int(params[1])
        self.name = str(params[2]) if len(params) > 2 else "%i_%i" % (self.node_id, self.var_id)
        if plan is not None:
            self.setNodeVariable(plan)
        else:
            self._variable = None
            self._node = None
    def setNodeVariable(self,plan):
        for t_node in plan.topology.nodes:
            if t_node.id == self.node_id:
                self._node = t_node
                if self.var_id in t_node.variables:
                    self._variable = t_node.variables[self.var_id]
                    return
        raise Exception("ProcedureBoundary.setNodeVariable error: node with id: %s , var %i not found in topology" % (str(self.node_id), self.var_id))
    def assertNoNaN(self):
        if self._variable is None:
            raise AssertionError("procedure boundary variable is None")
        if self._variable.data is None:
            raise AssertionError("procedure boundary data is None")
        na_count = self._variable.data["valor"].isna().sum()
        if na_count > 0:
            first_na_datetime = self._variable.data[self._variable.data["valor"].isna()].iloc[0].name.isoformat()
            raise AssertionError("procedure boundary variable data has NaN values starting at position %s" % first_na_datetime)
        return
