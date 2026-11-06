import importlib.util,pathlib,sys,unittest
P=pathlib.Path(__file__).parents[1]/"src/generate_timing_constraints.py";S=importlib.util.spec_from_file_location("g",P);g=importlib.util.module_from_spec(S);sys.modules["g"]=g;S.loader.exec_module(g)
def item(i="x",context="TS = 4 AND (B = 1)",requirement="A != 1"):return {"id":i,"context":context,"requirement":requirement,"source":{"path":"doc","line":1}}
def extracted(items=None,diagnostics=None):return {"format_version":1,"control_design_version":"v1","artifact":"timing-constraints","generation_stage":"extraction","sources":["doc"],"constraints":items if items is not None else [item()],"diagnostics":diagnostics or []}
class Tests(unittest.TestCase):
 def test_valid_candidate(self):
  c,d=g.build(extracted());self.assertEqual(c["generation_stage"],"candidate-generation");self.assertFalse(d)
 def test_duplicate_id(self):
  c,d=g.build(extracted([item(),item()]));self.assertIsNone(c);self.assertIn("DUPLICATE_ID",{x["code"] for x in d})
 def test_missing_required_field(self):
  x=item();del x["requirement"];c,d=g.build(extracted([x]));self.assertIsNone(c);self.assertIn("MISSING_FIELD",{x["code"] for x in d})
 def test_extracted_diagnostics_fail_generation(self):
  c,d=g.build(extracted(diagnostics=[{"severity":"ERROR","code":"SOURCE_ERROR","message":"bad"}]));self.assertIsNone(c);self.assertIn("SOURCE_ERROR",{x["code"] for x in d})
 def test_new_constraint_warning(self):
  c,d=g.build(extracted(),extracted([]));self.assertIsNotNone(c);self.assertIn("NEW_CONSTRAINT",{x["code"] for x in d})
 def test_stale_constraint_warning(self):
  c,d=g.build(extracted([]),extracted([item()]));self.assertIsNotNone(c);self.assertIn("STALE_CONSTRAINT",{x["code"] for x in d})
 def test_deterministic_candidate(self):self.assertEqual(g.build(extracted()),g.build(extracted()))
 def test_two_current_style_constraints(self):
  xs=[item("ts3","TS = 3 AND (IOT_READ_PENDING = 1 OR IOT_WRITE_PENDING = 1)","IO_CLEAR_AC_REQ != 1"),item("ts4","TS = 4 AND (IOT_READ_PENDING = 1 OR IO_SKIP_REQ = 1)","IO_CLEAR_AC_REQ != 1")];c,d=g.build(extracted(xs));self.assertEqual(len(c["constraints"]),2);self.assertFalse(d)
if __name__=="__main__":unittest.main()
