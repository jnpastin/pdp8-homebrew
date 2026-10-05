"""Tests for generate_micro_operation_mapping."""
from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"src"/"generate_micro_operation_mapping.py"
s=importlib.util.spec_from_file_location("generate_micro_operation_mapping",P);g=importlib.util.module_from_spec(s);sys.modules[s.name]=g;s.loader.exec_module(g)
def op(name="PC_INC",line=10):return {"name":name,"category":"Control Flow","description":"Increment PC.","targets":["PC"],"expression":["PC <- PC + 1"],"sources":["PC"],"preconditions":[],"constraints":[],"source":{"path":"docs/uops.md","heading":name,"line":line},"extraction_status":"definition-validated"}
def micros(items=None):return {"format_version":1,"extraction_stage":"definition-validation","source":{"path":"docs/uops.md"},"micro_operations":items or [op()],"diagnostics":[]}
def field(name="PC_INC",role="encoded",values=None,width=1):return {"name":name,"width":width,"control_word_role":role,"default_value":"0" if role=="encoded" else None,"explicit_value_required":"Yes" if role=="encoded" else "No","value_required_when":"Always","values":values if values is not None else [{"encoding":"0","meaning":"off"},{"encoding":"1","meaning":"on"}],"sources":{"definition":{"document":"docs/control.md","section":name,"line":1}}}
def schema(fields=None):return {"specification_type":"control-word-schema","schema_version":1,"control_design_version":"v1","fields":fields or [field()]}
def mapping(items=None):return {"specification_type":"micro-operation-mapping","schema_version":1,"control_design_version":"v1","mappings":items or []}
def entry(name="PC_INC",assignments=None,notes=None):return {"micro_operation":name,"assignments":assignments if assignments is not None else [{"field":"PC_INC","value":"1"}],"source":{"document":"old","section":name,"line":99},"notes":notes or []}
class Tests(unittest.TestCase):
 def test_resolve_relative(self):
  with tempfile.TemporaryDirectory() as t:self.assertEqual(g.resolve_from_repo(Path(t),Path("x")),(Path(t)/"x").resolve())
 def test_resolve_absolute(self):
    with tempfile.TemporaryDirectory() as temporary:
        path = (Path(temporary) / "x").resolve()
        self.assertEqual(g.resolve_from_repo(Path.cwd(), path), path)
 def test_missing_required_input(self):
  with self.assertRaises(g.GenerationFailure):g.read_json(Path("/missing"))
 def test_missing_optional(self):self.assertIsNone(g.read_json(Path("/missing"),optional=True))
 def test_empty_optional(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("");self.assertIsNone(g.read_json(p,optional=True))
 def test_invalid_json(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{")
   with self.assertRaises(g.GenerationFailure):g.read_json(p)
 def test_micro_validation(self):self.assertEqual(g.validate_micro_operations(micros()),[])
 def test_duplicate_micro(self):self.assertIn("DUPLICATE_MICRO_OPERATION",[x.code for x in g.validate_micro_operations(micros([op(),op()]))])
 def test_schema_validation(self):self.assertEqual(g.validate_schema(schema())[0],[])
 def test_duplicate_field(self):self.assertIn("DUPLICATE_CONTROL_FIELD",[x.code for x in g.validate_schema(schema([field(),field()]))[0]])
 def test_mapping_preserved_and_source_refreshed(self):
  c,d=g.build_candidate(micros(),schema(),mapping([entry(notes=["reviewed"])]));self.assertEqual(d,[]);e=c["mappings"][0];self.assertEqual(e["assignments"][0]["value"],"1");self.assertEqual(e["notes"],["reviewed"]);self.assertEqual(e["source"]["document"],"docs/uops.md");self.assertEqual(e["source"]["line"],10)
 def test_order_follows_extract(self):
  c,_=g.build_candidate(micros([op("B",2),op("A",3)]),schema([field("B"),field("A")]),None);self.assertEqual([x["micro_operation"] for x in c["mappings"]],["B","A"])
 def test_unresolved_new_mapping(self):
  c,d=g.build_candidate(micros(),schema(),None);self.assertEqual(c["mappings"][0]["assignments"],[]);self.assertIn("MAPPING_UNRESOLVED",[x.code for x in d])
 def test_stale_mapping(self):
  _,d=g.build_candidate(micros(),schema(),mapping([entry("OLD",[])]));self.assertIn("STALE_MAINTAINED_MAPPING",[x.code for x in d])
 def test_undefined_field(self):
  _,d=g.build_candidate(micros(),schema(),mapping([entry(assignments=[{"field":"BAD","value":"1"}])]));self.assertIn("UNDEFINED_ASSIGNED_FIELD",[x.code for x in d])
 def test_derived_field(self):
  _,d=g.build_candidate(micros(),schema([field("D","derived")]),mapping([entry(assignments=[{"field":"D","value":"1"}])]));self.assertIn("NON_ENCODED_ASSIGNMENT",[x.code for x in d])
 def test_external_field(self):
  _,d=g.build_candidate(micros(),schema([field("D","external_input")]),mapping([entry(assignments=[{"field":"D","value":"1"}])]));self.assertIn("NON_ENCODED_ASSIGNMENT",[x.code for x in d])
 def test_invalid_value(self):
  _,d=g.build_candidate(micros(),schema(),mapping([entry(assignments=[{"field":"PC_INC","value":"2"}])]));self.assertIn("INVALID_ASSIGNED_VALUE",[x.code for x in d])
 def test_reserved_value(self):
  f=field(values=[{"encoding":"0","meaning":"ok"},{"encoding":"1","meaning":"reserved"}]);_,d=g.build_candidate(micros(),schema([f]),mapping([entry()]));self.assertIn("INVALID_ASSIGNED_VALUE",[x.code for x in d])
 def test_duplicate_assignment(self):
  a=[{"field":"PC_INC","value":"1"},{"field":"PC_INC","value":"1"}];_,d=g.build_candidate(micros(),schema(),mapping([entry(assignments=a)]));self.assertIn("DUPLICATE_FIELD_ASSIGNMENT",[x.code for x in d])
 def test_data_field_without_values_uses_width(self):
  f=field("DATA",values=[],width=3);_,d=g.build_candidate(micros(),schema([f]),mapping([entry(assignments=[{"field":"DATA","value":"7"}])]));self.assertNotIn("INVALID_ASSIGNED_VALUE",[x.code for x in d])
 def test_deterministic_output(self):
  c,_=g.build_candidate(micros(),schema(),mapping([entry()]));
  with tempfile.TemporaryDirectory() as t:
   a=Path(t)/"a";b=Path(t)/"b";g.write_json(c,a);g.write_json(c,b);self.assertEqual(a.read_bytes(),b.read_bytes());self.assertTrue(a.read_text().endswith("\n"))
 def test_complete_run(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);(r/"micro.json").write_text(json.dumps(micros()));(r/"schema.json").write_text(json.dumps(schema()));status=g.run(["--repo-root",str(r),"--micro-operations","micro.json","--control-word-schema","schema.json","--candidate-output","candidate.json","--report-output","report.txt"]);self.assertEqual(status,0);self.assertTrue((r/"candidate.json").is_file());self.assertIn("Warnings: 1",(r/"report.txt").read_text())
if __name__=="__main__":unittest.main()
