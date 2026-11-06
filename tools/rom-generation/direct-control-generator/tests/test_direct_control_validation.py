from __future__ import annotations
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import direct_control_validation as v  # noqa: E402
import generate_direct_control as generator  # noqa: E402


def field(name="RUN_NEXT", width=1, role="encoded", default="0", values=None):
    return {"name": name, "width": width, "control_word_role": role, "default_value": default, "values": values or [{"encoding":"0","meaning":"off"},{"encoding":"1","meaning":"on"}]}

def definition(**changes):
    base={"id":"01:1.1","applicable_context":[],"direct_assignments":[],"control_supplied_values":[],"micro_operation_assignments":[]}
    base.update(changes); return base

class UnitTests(unittest.TestCase):

 def test_symbolic_value_resolution(self):
  f=field("MS_NEXT",3,values=[{"encoding":"0","meaning":"FETCH"}]); self.assertEqual(v.resolve_value(f,"FETCH"),"0")
 def test_iot_alias_resolution(self): self.assertEqual(v.resolve_value(field("IOT_TRANSFER_VAL",2),"READ"),"1")
 def test_unknown_field(self):
  _,d=v.validate_assignment_set([("BAD","1")],{},"x","direct"); self.assertEqual(d[0].code,"UNKNOWN_CONTROL_FIELD")
 def test_non_encoded_field(self):
  _,d=v.validate_assignment_set([("X","1")],{"X":field("X",role="derived")},"x","direct"); self.assertEqual(d[0].code,"NON_ENCODED_CONTROL_FIELD")
 def test_conflicting_assignment(self):
  _,d=v.validate_assignment_set([("RUN_NEXT","0"),("RUN_NEXT","1")],{"RUN_NEXT":field()},"x","direct"); self.assertEqual(d[0].code,"CONFLICTING_ASSIGNMENT")
 def test_malformed_assignment(self):
  _,d=v.parse_assignments(["RUN_NEXT <- 1"],"x","direct"); self.assertEqual(d[0].code,"MALFORMED_ASSIGNMENT")
 def test_unknown_context_input(self):
  d=v.validate_context(definition(applicable_context=["BAD = 1"]),{},{},{}); self.assertEqual(d[0].code,"UNKNOWN_CONTEXT_SYMBOL")
 def test_unknown_selected_operation(self):
  d=v.validate_context(definition(applicable_context=["NOPE is selected"]),{},{},{}); self.assertEqual(d[0].code,"UNKNOWN_MICRO_OPERATION")
 def test_control_address_context_is_allowed(self):
  self.assertEqual(v.validate_context(definition(applicable_context=["MS = FETCH\nTS = 4"]),{},{},{}),[])
 def test_control_output_readback_context_is_allowed(self):
  self.assertEqual(v.validate_context(definition(applicable_context=["/DMA_GRANT = 0"]),{},{"/DMA_GRANT":field("/DMA_GRANT")},{}),[])
 def test_micro_default_is_allowed(self):
  d=v.validate_micro_assignments(definition(applicable_context=["OP is selected"]),{"/WR":"1"},{"/WR":field("/WR",default="1")},{"OP":{}}); self.assertEqual(d,[])
 def test_micro_nondefault_must_match(self):
  d=v.validate_micro_assignments(definition(applicable_context=["OP is selected"]),{"/RD":"0"},{"/RD":field("/RD",default="1")},{"OP":{}}); self.assertEqual(d[0].code,"MICRO_OPERATION_ASSIGNMENT_MISMATCH")
 def test_value_width_mismatch(self):
  d=v.validate_control_supplied_values(definition(),[("DF_VAL","IR_DF")],{}, {"DF_VAL":field("DF_VAL",3)}, {"IR_DF":{"width":2,"control_uses":["value"]}}); self.assertEqual(d[0].code,"VALUE_WIDTH_MISMATCH")
 def test_value_input_must_be_value_capable(self):
  d=v.validate_control_supplied_values(definition(),[("DF_VAL","IR_DF")],{}, {"DF_VAL":field("DF_VAL",3)}, {"IR_DF":{"width":3,"control_uses":["predicate"]}}); self.assertEqual(d[0].code,"INPUT_NOT_VALUE_CAPABLE")
 def test_version_mismatch(self):
  d=v.validate_versions((("a",{"control_design_version":"v1"}),("b",{"control_design_version":"v2"}))); self.assertEqual(d[0].code,"CONTROL_DESIGN_VERSION_MISMATCH")
 def test_missing_file(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(v.ValidationFailure): v.load_json(Path(td)/"missing.json")

class RepositoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(__file__).resolve().parents[4]
  extracted=generator.read_json(cls.root/generator.DEFAULT_EXTRACTED)
  assert extracted is not None
  cls.defs,generation_diagnostics=generator.build_candidate(extracted,None)
  assert cls.defs is not None
  cls.inputs=v.load_json(cls.root/generator.DEFAULT_INPUT_SCHEMA,"control-input-schema")
  cls.word=v.load_json(cls.root/generator.DEFAULT_WORD_SCHEMA,"control-word-schema")
  cls.mapping=v.load_json(cls.root/generator.DEFAULT_MAPPING,"micro-operation-mapping")
  cls.diags=v.validate(cls.defs,cls.inputs,cls.word,cls.mapping)
  cls.generation_diagnostics=generation_diagnostics
 def test_repository_definitions_count(self): self.assertEqual(len(self.defs["definitions"]),64)
 def test_repository_validation(self): self.assertEqual(self.diags,[])
 def test_repository_candidate_is_built_in_memory(self):
  self.assertEqual(len(self.generation_diagnostics),64)
  self.assertTrue(all(item.code=="NEW_DEFINITION" for item in self.generation_diagnostics))
 def test_all_direct_fields_exist(self):
  fields=v.field_index(self.word)
  for d in self.defs["definitions"]:
   pairs,_=v.parse_assignments(d["direct_assignments"],d["id"],"direct")
   self.assertTrue(all(name in fields for name,_ in pairs))
 def test_control_supplied_sources(self):
  inputs=v.field_index(self.inputs)
  by_id={d["id"]:d for d in self.defs["definitions"]}
  self.assertIn("IR_DF",inputs); self.assertEqual(by_id["01:5.1"]["control_supplied_values"],["DF_VAL = IR_DF"])
 def test_memory_read_mapping(self):
  maps=v.mapping_index(self.mapping); self.assertEqual(maps["MEM_READ_TO_MB"]["/RD"],"0")
 def test_db_mapping(self):
  maps=v.mapping_index(self.mapping); self.assertEqual(maps["DB_READ_TO_AC"]["/DB_READ"],"0"); self.assertEqual(maps["DB_WRITE_FROM_AC"]["/DB_WRITE"],"0")

if __name__=="__main__": unittest.main()
