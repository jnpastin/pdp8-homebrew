from __future__ import annotations
import copy, io, json, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/"src";sys.path.insert(0,str(SRC))
import generate_execution_definitions as g

def case(case_id="x",uop="AC_CLEAR"):
 return {"id":case_id,"source":{"path":"doc","line":1},"execution_model":"major-state","context":["MS = EXECUTE"],"timing_state":1,"micro_operations":[uop],"conditional_micro_operations":[]}
def artifact(cases):
 return {"format_version":1,"control_design_version":"v1","artifact":"execution-definitions","extraction_stage":"documentation-extraction","cases":cases,"diagnostics":[]}

class StructureTests(unittest.TestCase):
 def test_paths(self):
  self.assertEqual(g.DEFAULT_EXTRACTED.name,"execution-definitions.json");self.assertEqual(g.DEFAULT_CANDIDATE.name,"execution-definitions.candidate.json");self.assertEqual(g.DEFAULT_MAINTAINED,Path("rom/microcode/v1/execution-definitions.json"))
 def test_missing_top_level_fields_blocks(self):
  required=sorted(g.REQUIRED_TOP_LEVEL)
  for field in required:
   a=artifact([case()]);del a[field];c,d=g.build_candidate(a,None);self.assertIsNone(c,field);self.assertIn("MISSING_TOP_LEVEL_FIELDS",[x.code for x in d],field)
 def test_wrong_artifact_type_blocks(self):
  a=artifact([case()]);a["artifact"]="wrong";c,d=g.build_candidate(a,None);self.assertIsNone(c);self.assertEqual(d[0].code,"UNEXPECTED_ARTIFACT_TYPE")
 def test_non_list_diagnostics_blocks(self):
  a=artifact([case()]);a["diagnostics"]={};c,d=g.build_candidate(a,None);self.assertIsNone(c);self.assertEqual(d[0].code,"INVALID_EXTRACTOR_DIAGNOSTICS")
 def test_extractor_error_blocks(self):
  for severity in ("ERROR","FATAL"):
   a=artifact([case()]);a["diagnostics"]=[{"severity":severity}];c,d=g.build_candidate(a,None);self.assertIsNone(c);self.assertEqual(d[0].code,"EXTRACTOR_FAILURE_DIAGNOSTICS")
 def test_missing_case_fields_block(self):
  for field in sorted(g.REQUIRED_CASE_FIELDS):
   item=case();del item[field];c,d=g.build_candidate(artifact([item]),None);self.assertIsNone(c,field);self.assertEqual(d[0].code,"INVALID_EXTRACTED_CASES",field)
 def test_non_object_case_blocks(self):
  c,d=g.build_candidate(artifact(["bad"]),None);self.assertIsNone(c);self.assertEqual(d[0].code,"INVALID_EXTRACTED_CASES")
 def test_invalid_ids_block(self):
  for value in (None,"",1):
   item=case();item["id"]=value;c,d=g.build_candidate(artifact([item]),None);self.assertIsNone(c);self.assertEqual(d[0].code,"INVALID_EXTRACTED_CASES")
 def test_duplicate_blocks(self):
  c,d=g.build_candidate(artifact([case(),case()]),None);self.assertIsNone(c);self.assertEqual(d[0].code,"INVALID_EXTRACTED_CASES")
 def test_malformed_maintained_blocks(self):
  maintained=artifact([case()]);maintained["cases"]=["bad"];c,d=g.build_candidate(artifact([case()]),maintained);self.assertIsNone(c);self.assertEqual(d[0].code,"INVALID_MAINTAINED_CASES")
 def test_version_mismatch_blocks(self):
  a=artifact([case()]);m=artifact([case()]);m["control_design_version"]="v2";c,d=g.build_candidate(a,m);self.assertIsNone(c);self.assertEqual(d[0].code,"CONTROL_DESIGN_VERSION_MISMATCH")

class LifecycleTests(unittest.TestCase):
 def test_first_generation(self):
  c,d=g.build_candidate(artifact([case()]),None);self.assertIsNotNone(c);self.assertEqual(d[0].code,"NEW_CASE")
 def test_unchanged(self):
  a=artifact([case()]);c,d=g.build_candidate(a,copy.deepcopy(a));self.assertIsNotNone(c);self.assertEqual(d,[])
 def test_changed(self):
  _,d=g.build_candidate(artifact([case(uop="AC_CLEAR")]),artifact([case(uop="L_CLEAR")]));self.assertEqual(d[0].code,"CHANGED_CASE")
 def test_stale(self):
  _,d=g.build_candidate(artifact([]),artifact([case()]));self.assertEqual(d[0].code,"STALE_CASE")
 def test_new_changed_stale_together(self):
  extracted=artifact([case("changed","AC_CLEAR"),case("new","L_CLEAR")]);maintained=artifact([case("changed","L_CLEAR"),case("stale","MQ_CLEAR")]);_,d=g.build_candidate(extracted,maintained);self.assertEqual({x.code for x in d},{"NEW_CASE","CHANGED_CASE","STALE_CASE"})
 def test_candidate_preserves_all_case_fields(self):
  item=case();item["context"].append("FLAG = 1");item["conditional_micro_operations"]=[{"predicate":"FLAG = 1","micro_operation":"PC_INC"}];a=artifact([item]);c,_=g.build_candidate(a,None);self.assertEqual(c["cases"][0],item)
 def test_candidate_preserves_order(self):
  a=artifact([case("z"),case("a")]);c,_=g.build_candidate(a,None);self.assertEqual([x["id"] for x in c["cases"]],["z","a"])
 def test_round_trip_maintained_candidate(self):
  a=artifact([case("a"),case("b","L_CLEAR")]);c,d=g.build_candidate(a,None);self.assertTrue(d);c2,d2=g.build_candidate(a,c);self.assertEqual(d2,[]);self.assertEqual(c2,c)
 def test_json_serializable(self):
  c,_=g.build_candidate(artifact([case()]),None);json.dumps(c)
 def test_missing_optional(self):
  with tempfile.TemporaryDirectory() as td:self.assertIsNone(g.read_json(Path(td)/"missing",optional=True))

class RunTests(unittest.TestCase):
 def _write(self,root,path,data):
  target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data),encoding="utf-8")
 def test_run_writes_candidate_with_warnings(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);self._write(root,g.DEFAULT_EXTRACTED,artifact([case()]));out=io.StringIO()
   with redirect_stdout(out):rc=g.run(["--repo-root",str(root)])
   self.assertEqual(rc,0);self.assertTrue((root/g.DEFAULT_CANDIDATE).exists());self.assertIn("Candidate written: yes",out.getvalue())
 def test_run_does_not_write_candidate_on_error(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);a=artifact([case()]);a["diagnostics"]=[{"severity":"ERROR"}];self._write(root,g.DEFAULT_EXTRACTED,a)
   with redirect_stdout(io.StringIO()):rc=g.run(["--repo-root",str(root)])
   self.assertEqual(rc,1);self.assertFalse((root/g.DEFAULT_CANDIDATE).exists())
 def test_second_run_against_promoted_candidate_has_zero_diagnostics(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);a=artifact([case()]);self._write(root,g.DEFAULT_EXTRACTED,a)
   with redirect_stdout(io.StringIO()):self.assertEqual(g.run(["--repo-root",str(root)]),0)
   promoted=json.loads((root/g.DEFAULT_CANDIDATE).read_text());self._write(root,g.DEFAULT_MAINTAINED,promoted)
   output=io.StringIO()
   with redirect_stdout(output):self.assertEqual(g.run(["--repo-root",str(root)]),0)
   report=(root/g.DEFAULT_REPORT).read_text();self.assertIn("Warnings: 0",report);self.assertIn("No diagnostics.",report)

class RepositoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(__file__).resolve().parents[4];cls.extracted=g.read_json(cls.root/g.DEFAULT_EXTRACTED);assert cls.extracted is not None;cls.candidate,cls.diagnostics=g.build_candidate(cls.extracted,None)
 def test_count(self):self.assertEqual(len(self.candidate["cases"]),105)
 def test_first_generation_warnings(self):self.assertEqual(len(self.diagnostics),105);self.assertTrue(all(x.code=="NEW_CASE" for x in self.diagnostics))
 def test_candidate_preserves_order(self):self.assertEqual([x["id"] for x in self.candidate["cases"]],[x["id"] for x in self.extracted["cases"]])
 def test_candidate_has_no_embedded_diagnostics(self):self.assertEqual(self.candidate["diagnostics"],[])
 def test_repository_round_trip_is_clean(self):
  c2,d2=g.build_candidate(self.extracted,self.candidate);self.assertEqual(d2,[]);self.assertEqual(c2,self.candidate)

if __name__=="__main__":unittest.main()
