from pydrodelta.plan import Plan
from unittest import TestCase
import yaml
import os
from pandas import DataFrame

class Test_Plan(TestCase):

    def test_init(self):
        config = yaml.load(open("%s/sample_data/plans/linear_channel_dummy.yml" % os.environ["PYDRODELTA_DIR"]),yaml.CLoader)
        plan = Plan(**config)
        self.assertEqual(plan.name,"linear_channel_dummy")
        self.assertEqual(plan.id, 505)
        self.assertEqual(plan.forecast_date.isoformat(), "2024-01-03T00:00:00-03:00")
        self.assertEqual(len(plan.topology.nodes),2)
        self.assertEqual(len(plan.procedures),1)

    def test_analysis(self):
        config = yaml.load(open("%s/sample_data/plans/linear_channel_dummy.yml" % os.environ["PYDRODELTA_DIR"]),yaml.CLoader)
        plan = Plan(**config)
        plan.topology.batchProcessInput()
        for n in plan.topology.nodes:
            for v in n.variables:
                self.assert_(isinstance(n.variables[v].data,DataFrame))
                self.assertEqual(len(n.variables[v].data),14)
                self.assertEqual(min(n.variables[v].data.index).isoformat(),"2024-01-01T00:00:00-03:00")
                self.assertEqual(max(n.variables[v].data.index).isoformat(),"2024-01-14T00:00:00-03:00")

    def test_exec(self):
        config = yaml.load(open("%s/sample_data/plans/linear_channel_dummy.yml" % os.environ["PYDRODELTA_DIR"]),yaml.CLoader)
        plan = Plan(**config)
        plan.execute(upload=False)
        for p in plan.procedures:
            for i in p.input:
                self.assert_(isinstance(i,DataFrame))
                self.assertEqual(len(i),14)
                self.assertEqual(min(i.index).isoformat(),"2024-01-01T00:00:00-03:00")
                self.assertEqual(max(i.index).isoformat(),"2024-01-14T00:00:00-03:00")
            for o in p.output:
                self.assert_(isinstance(o,DataFrame))
                self.assertEqual(len(o),14)
                self.assertEqual(min(o.index).isoformat(),"2024-01-01T00:00:00-03:00")
                self.assertEqual(max(o.index).isoformat(),"2024-01-14T00:00:00-03:00")
        for s in plan.topology.nodes[1].variables[40].series_sim:
            self.assert_(isinstance(s.data,DataFrame))
            self.assertEqual(len(s.data),14)
            self.assertEqual(min(s.data.index).isoformat(),"2024-01-01T00:00:00-03:00")
            self.assertEqual(max(s.data.index).isoformat(),"2024-01-14T00:00:00-03:00")
            self.assertAlmostEqual(
                plan.topology.nodes[0].variables[40].data["valor"].sum(skipna=True),
                sum(s.data["valor"]), 
                places = 1)
    
    def test_api(self):
        config = yaml.load(open("%s/sample_data/plans/dummy_polynomial.yml" % os.environ["PYDRODELTA_DIR"]),yaml.CLoader)
        plan = Plan(**config)
        plan.topology.batchProcessInput(
            input_api_config = {
                "url": "https://alerta.ina.gob.ar/test",
                "token": "MY_TOKEN"
            })
        for n in plan.topology.nodes:
            for v in n.variables:
                self.assert_(isinstance(n.variables[v].data,DataFrame))
                self.assertEqual(len(n.variables[v].data),3)
                self.assertEqual(min(n.variables[v].data.index).isoformat(),"2022-07-15T00:00:00-03:00")
                self.assertEqual(max(n.variables[v].data.index).isoformat(),"2022-07-17T00:00:00-03:00")
    
    def test_api_exec(self):
        config = yaml.load(open("%s/sample_data/plans/dummy_polynomial.yml" % os.environ["PYDRODELTA_DIR"]),yaml.CLoader)
        plan = Plan(**config)
        plan.execute(
            upload = False,
            input_api_config = {
                "url": "https://alerta.ina.gob.ar/test",
                "token": "MY_TOKEN"
            })