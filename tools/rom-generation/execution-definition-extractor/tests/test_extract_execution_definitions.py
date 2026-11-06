from __future__ import annotations
import sys, unittest
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/"src";sys.path.insert(0,str(SRC))
import extract_execution_definitions as e

class ParserTests(unittest.TestCase):
 def test_condition_parser(self):
  lines=["Conditional μops:","","```text","FLAG = 1 -> PC_INC","```"]
  self.assertEqual(e.conditional_after(lines,0),[{"predicate":"FLAG = 1","micro_operation":"PC_INC"}])
 def test_group2_overlapping_bit_uses_group2_name(self):
  self.assertEqual(
   e.normalize_opr_predicate("IR[2] = 1", {"RAL":2,"OSR":2}, 2),
   "IR_OPR_OSR = 1",
  )
 def test_group3_overlapping_bits_remain_raw_without_named_inputs(self):
  self.assertEqual(
   e.normalize_opr_predicate("IR[6] = 1 AND IR[4] = 1", {"CLL":6,"MQA":6,"CML":4,"MQL":4}, 3),
   "IR[6] = 1 AND IR[4] = 1",
  )
 def test_iot_op_field_normalization(self):
  self.assertEqual(e.normalize_context_term("IR[2:0] = 101"),"IR_IOT_OP = 101")
 def test_mri_context_includes_instruction_class(self):
  self.assertEqual(
   e.normalize_execute_context("mri", "3.1", "IR[11:9] = 000"),
   ["IR_IS_MRI = 1", "IR_MRI_OPCODE = 000"],
  )
 def test_memory_extension_decoded_contexts(self):
  expected={
   "10.1":["IR_IS_IOT = 1","IR_WRITES_DF = 1"],
   "10.2":["IR_IS_IOT = 1","IR_WRITES_IF = 1"],
   "10.3":["IR_IS_IOT = 1","IR_READS_DF = 1"],
   "10.4":["IR_IS_IOT = 1","IR_READS_IF = 1"],
   "10.5":["IR_IS_IOT = 1","IR_READS_IB = 1"],
   "10.6":["IR_IS_IOT = 1","IR_RESTORES_IB = 1"],
  }
  for number,context in expected.items():self.assertEqual(e.normalize_execute_context("iot",number,"unused"),context)
 def test_console_case(self):
  text="""## 6. Load Address Operation\nApplicable context:\n```text\nRUN = 0\nFP_LOAD = 1\n```\nExecution model:\n```text\nsingle TS-equivalent console transaction\n```\nμops:\n- AC_CLEAR\n"""
  x=e.parse_console(text,"x")[0];self.assertEqual(x["execution_model"],"console-transaction");self.assertEqual(x["context"],["RUN = 0","FP_LOAD = 1"])
 def test_opr_context_includes_instruction_class(self):
  text="""### 4. Instruction Definition
#### 4.1 X
TS1:
- if IR[bit(CLA)] = 1: AC_CLEAR
"""
  x=e.parse_opr_execution(text,"x",1,{"CLA":7})[0]
  self.assertEqual(x["context"],["MS = EXECUTE","IR_IS_OPR = 1","IR_OPR_GROUP1 = 1"])
 def test_opr_bit_resolution(self):
  text="""### 4. Instruction Definition\n#### 4.1 X\nTS1:\n- if IR[bit(CLA)] = 1: AC_CLEAR\n"""
  x=e.parse_opr_execution(text,"x",1,{"CLA":7})[0];self.assertEqual(x["id"],"opr1:ts1");self.assertEqual(x["conditional_micro_operations"][0]["predicate"],"IR_OPR_CLA = 1")

class ValidationTests(unittest.TestCase):
 def test_clean_removes_markdown_backticks(self):self.assertEqual(e.clean("`IB_TO_DF`"),"IB_TO_DF")
 def test_bullets_ignore_horizontal_rule_noise(self):self.assertEqual(e.bullets_after(["TS4:","- AC_CLEAR","- --"],0),["AC_CLEAR"])
 def test_malformed_uop_is_error(self):
  item=e.case("x","doc",1,["MS = EXECUTE"],1,["`BAD`"]);d=e.validate_cases([item],set());self.assertEqual(d[0].code,"MALFORMED_MICRO_OPERATION")
 def test_unknown_uop_is_error(self):
  item=e.case("x","doc",1,["MS = EXECUTE"],1,["NOPE"]);d=e.validate_cases([item],{"AC_CLEAR"});self.assertEqual(d[0].code,"UNKNOWN_MICRO_OPERATION")
 def test_duplicate_case_id_is_error(self):
  item=e.case("x","doc",1,["MS = EXECUTE"],1);d=e.validate_cases([item,item],set());self.assertIn("DUPLICATE_CASE_ID",[x.code for x in d])
 def test_unresolved_opr_bit_is_error(self):
  item=e.case("x","doc",1,["MS = EXECUTE"],1,[],[{"predicate":"IR[bit(CLA)] = 1","micro_operation":"AC_CLEAR"}]);d=e.validate_cases([item],{"AC_CLEAR"});self.assertIn("UNRESOLVED_OPR_BIT",[x.code for x in d])

class RepositoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.root=Path(__file__).resolve().parents[4];cls.data=e.extract(cls.root)
 def test_no_diagnostics(self):self.assertEqual(self.data["diagnostics"],[])
 def test_opr_bits_are_found(self):
  for name in ("CLA","RAR","RAL","BSW","IAC","MQA","MQL","OSR","HLT"):self.assertIn(name,self.data["opr_bit_positions"])
 def test_opr_bit_positions(self):
  expected={"CLA":7,"CLL":6,"CMA":5,"CML":4,"RAR":3,"RAL":2,"BSW":1,"IAC":0,"SPA":6,"SNA":5,"SZL":4,"OSR":2,"HLT":1,"MQA":6,"MQL":4}
  for name,bit in expected.items():self.assertEqual(self.data["opr_bit_positions"][name],bit)
 def test_mri_context_uses_control_input_names(self):
  x=next(c for c in self.data["cases"] if c["id"]=="mri:3.3:ts4")
  self.assertEqual(x["context"],["MS = EXECUTE","IR_IS_MRI = 1","IR_MRI_OPCODE = 010"])
  self.assertNotIn("IR[11:9] = 010",x["context"])
 def test_iot_context_uses_control_input_names(self):
  x=next(c for c in self.data["cases"] if c["id"]=="iot:9.1:ts2");self.assertIn("IR_IS_IOT = 1",x["context"]);self.assertIn("IR_IOA = 00",x["context"])
 def test_device_zero_iot_uses_iot_op_input(self):
  x=next(c for c in self.data["cases"] if c["id"]=="iot:9.6:ts2")
  self.assertIn("IR_IOT_OP = 101",x["context"]);self.assertFalse(any("IR[2:0]" in term for term in x["context"]))
 def test_memory_extension_iot_uses_decoded_predicates(self):
  expected={"10.1":"IR_WRITES_DF = 1","10.2":"IR_WRITES_IF = 1","10.3":"IR_READS_DF = 1","10.4":"IR_READS_IF = 1","10.5":"IR_READS_IB = 1","10.6":"IR_RESTORES_IB = 1"}
  for section,predicate in expected.items():
   xs=[c for c in self.data["cases"] if c["id"].startswith(f"iot:{section}:")];self.assertTrue(xs);self.assertTrue(all(c["context"]==["IR_IS_IOT = 1",predicate] for c in xs))
 def test_iot_context_has_no_raw_selection_bits(self):
  for c in [x for x in self.data["cases"] if x["id"].startswith("iot:")]:
   joined=" ".join(c["context"]);self.assertNotIn("IR[2:0]",joined);self.assertNotIn("IR[8:6]",joined);self.assertNotIn("IR[5:3]",joined);self.assertNotIn("IR[2]",joined);self.assertNotIn("IR[1]",joined);self.assertNotIn("IR[0]",joined)
 def test_opr_context_uses_instruction_class_and_group_inputs(self):
  for group in (1,2,3):
   xs=[c for c in self.data["cases"] if c["id"].startswith(f"opr{group}:")]
   self.assertTrue(xs)
   self.assertTrue(all(x["context"] == ["MS = EXECUTE", "IR_IS_OPR = 1", f"IR_OPR_GROUP{group} = 1"] for x in xs))
 def test_group1_predicates_use_control_inputs(self):
  x=next(c for c in self.data["cases"] if c["id"]=="opr1:ts1");self.assertEqual([item["predicate"] for item in x["conditional_micro_operations"]],["IR_OPR_CLA = 1","IR_OPR_CLL = 1"])
 def test_group2_osr_uses_osr_input(self):
  x=next(c for c in self.data["cases"] if c["id"]=="opr2:ts3")
  self.assertEqual(x["conditional_micro_operations"],[{"predicate":"IR_OPR_OSR = 1","micro_operation":"AC_OR_FP_SR"}])
 def test_group3_mqa_mql_bits_remain_raw(self):
  x=next(c for c in self.data["cases"] if c["id"]=="opr3:ts2")
  predicates=[item["predicate"] for item in x["conditional_micro_operations"]]
  self.assertEqual(predicates,["IR[6] = 1","IR[4] = 1","IR[6] = 1 AND IR[4] = 1"])
 def test_fetch_cifp_condition(self):
  x=next(c for c in self.data["cases"] if c["id"]=="fetch-defer:3.1");self.assertEqual(x["conditional_micro_operations"],[{"predicate":"CIFP = 0","micro_operation":"II_CLEAR"}])
 def test_defer_autoindex(self):
  x=next(c for c in self.data["cases"] if c["id"]=="fetch-defer:4.4");self.assertEqual(x["conditional_micro_operations"][0]["predicate"],"AUTO_INDEX_REQUIRED = 1")
 def test_isz_skip(self):
  x=next(c for c in self.data["cases"] if c["id"]=="mri:3.3:ts4");self.assertEqual(x["conditional_micro_operations"][0]["predicate"],"ISZ_SKIP_REQUIRED = 1")
 def test_interrupt_context(self):
  xs=[c for c in self.data["cases"] if c["id"].startswith("interrupt:")];self.assertEqual(len(xs),4);self.assertTrue(all(c["context"]==["MS = INTERRUPT"] for c in xs))
 def test_console_operations(self):
  xs=[c for c in self.data["cases"] if c["execution_model"]=="console-transaction"];self.assertEqual({x["id"] for x in xs},{"console:6","console:7","console:8","console:10"})
 def test_group2_skip(self):
  x=next(c for c in self.data["cases"] if c["id"]=="opr2:ts1");self.assertEqual(x["conditional_micro_operations"][0]["predicate"],"SKIP_TAKEN = 1")
 def test_case_count(self):self.assertEqual(len(self.data["cases"]),109)
 def test_all_uops_are_normalized(self):
  import re
  for c in self.data["cases"]:
   for u in c["micro_operations"]+[x["micro_operation"] for x in c["conditional_micro_operations"]]:self.assertRegex(u,r"^[A-Z][A-Z0-9_]*$")
 def test_dca_ts4_has_only_ac_clear(self):
  x=next(c for c in self.data["cases"] if c["id"]=="mri:3.4:ts4");self.assertEqual(x["micro_operations"],["AC_CLEAR"])
 def test_rmf_uops_are_normalized(self):
  x=next(c for c in self.data["cases"] if c["id"]=="iot:10.6:ts2");self.assertEqual(x["micro_operations"],["IB_TO_DF","IB_TO_DIF","II_SET","CIFP_SET"])
 def test_all_six_mri_opcodes_have_four_ts_cases(self):
  for section in range(1,7):self.assertEqual(len([c for c in self.data["cases"] if c["id"].startswith(f"mri:3.{section}:")]),4)
 def test_iot_noop_sgt_is_preserved(self):
  xs=[c for c in self.data["cases"] if c["id"].startswith("iot:9.7:")];self.assertEqual(len(xs),4);self.assertTrue(all(not x["micro_operations"] and not x["conditional_micro_operations"] for x in xs))
 def test_group1_nop_is_representable(self):
  xs=[c for c in self.data["cases"] if c["id"].startswith("opr1:")];self.assertEqual({x["timing_state"] for x in xs},{1,2,3,4});self.assertTrue(all(not x["micro_operations"] for x in xs))
 def test_group1_rotate_combinations(self):
  x=next(c for c in self.data["cases"] if c["id"]=="opr1:ts4");ops={i["micro_operation"] for i in x["conditional_micro_operations"]};self.assertEqual(ops,{"AC_RAR","AC_RAL","AC_RTR","AC_RTL","AC_BSW"})
 def test_group3_swap_is_preserved(self):
  x=next(c for c in self.data["cases"] if c["id"]=="opr3:ts2");self.assertIn({"predicate":"IR[6] = 1 AND IR[4] = 1","micro_operation":"AC_MQ_SWAP"},x["conditional_micro_operations"])
 def test_console_cases_are_tsless(self):
  xs=[c for c in self.data["cases"] if c["execution_model"]=="console-transaction"];self.assertTrue(all(c["timing_state"] is None for c in xs))

 def test_external_iot_phase_binding(self):
  text="""## 7. External IOT Phase Binding
- `IO_CLEAR_AC_REQ` selects `AC_CLEAR` during the TS in which the request is asserted.
- `IO_SKIP_REQ` selects `PC_INC` during TS4.
## 8. Response Constraints
"""
  xs=e.parse_external_iot_phase_binding(text,"doc")
  self.assertEqual(len(xs),4)
  self.assertTrue(all(x["context"]==["MS = EXECUTE","IOT_ACTIVE = 1"] for x in xs))
  self.assertEqual(xs[0]["conditional_micro_operations"],[{"predicate":"IO_CLEAR_AC_REQ = 1","micro_operation":"AC_CLEAR"}])
  self.assertEqual(xs[3]["conditional_micro_operations"],[{"predicate":"IO_CLEAR_AC_REQ = 1","micro_operation":"AC_CLEAR"},{"predicate":"IO_SKIP_REQ = 1","micro_operation":"PC_INC"}])

 def test_external_iot_response_cases(self):
  xs=[c for c in self.data["cases"] if c["id"].startswith("iot:external:")]
  self.assertEqual(len(xs),4)
  self.assertTrue(all(c["context"]==["MS = EXECUTE","IOT_ACTIVE = 1"] for c in xs))
  ts4=next(c for c in xs if c["timing_state"]==4)
  self.assertIn({"predicate":"IO_SKIP_REQ = 1","micro_operation":"PC_INC"},ts4["conditional_micro_operations"])

if __name__=="__main__":unittest.main()
