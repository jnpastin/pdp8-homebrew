import importlib.util,pathlib,sys,unittest
P=pathlib.Path(__file__).parents[1]/"src/extract_timing_constraints.py";S=importlib.util.spec_from_file_location("e",P);e=importlib.util.module_from_spec(S);sys.modules["e"]=e;S.loader.exec_module(e)
class Tests(unittest.TestCase):
 def test_nested_constraints(self):
  text="""##### 5.2.5 TS3
- Human rule:
  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1 OR IOT_WRITE_PENDING = 1`
##### 5.2.7 TS4
- Human rule:
  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1 OR IO_SKIP_REQ = 1`
""";r=e.parse(text,"doc.md");self.assertEqual(len(r["constraints"]),2);self.assertEqual(r["constraints"][1]["context"],"TS = 4 AND (IOT_READ_PENDING = 1 OR IO_SKIP_REQ = 1)");self.assertFalse(r["diagnostics"])
 def test_multiple_constraints_same_ts(self):
  r=e.parse("##### TS4\n- A:\n  - `X != 1 IF Y = 1`\n- B:\n  - `Z != 1 IF Q = 1`\n","doc");self.assertEqual(len(r["constraints"]),2);self.assertTrue(all(x["context"].startswith("TS = 4") for x in r["constraints"]))
 def test_ts_context_changes(self):
  r=e.parse("##### TS3\n- A:\n  - `X != 1 IF Y = 1`\n##### TS4\n- B:\n  - `X != 1 IF Z = 1`\n","doc");self.assertEqual([x["context"].split(" AND")[0] for x in r["constraints"]],["TS = 3","TS = 4"])
 def test_compound_or_preserved(self):
  r=e.parse("##### TS4\n- R:\n  - `A != 1 IF B = 1 OR C = 1`\n","doc");self.assertEqual(r["constraints"][0]["context"],"TS = 4 AND (B = 1 OR C = 1)")
 def test_constraint_outside_ts_diagnostic(self):
  r=e.parse("- R:\n  - `A != 1 IF B = 1`\n","doc");self.assertEqual(r["diagnostics"][0]["code"],"MISSING_TIMING_CONTEXT")
 def test_unrelated_nested_bullet_ignored(self):
  r=e.parse("##### TS4\n- R:\n  - ordinary explanatory text\n","doc");self.assertEqual(r["constraints"],[]);self.assertEqual(r["diagnostics"],[])
 def test_source_traceability(self):
  r=e.parse("##### TS4\n- Rule:\n  - `A != 1 IF B = 1`\n","doc.md");self.assertEqual(r["constraints"][0]["source"],{"path":"doc.md","line":3})
 def test_deterministic(self):
  text="##### TS4\n- Rule:\n  - `A != 1 IF B = 1 OR C = 1`\n";self.assertEqual(e.parse(text,"doc"),e.parse(text,"doc"))
if __name__=="__main__":unittest.main()
