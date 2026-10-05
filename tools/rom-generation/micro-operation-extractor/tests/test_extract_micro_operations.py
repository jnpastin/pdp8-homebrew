"""Tests for extract_micro_operations."""
from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"src"/"extract_micro_operations.py"
s=importlib.util.spec_from_file_location("extract_micro_operations",P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def doc(body):return f"## Micro-Operations\n\n## 5. μop Definitions (Alphabetical)\n\n{body}\n\n## 6. Notes\n"
def definition(name="PC_INC"):return f"### {name}\n\n**Category:** Control Flow\n**Description:** Increment PC.\n**Target:** PC\n**Expression:** PC ← PC + 1\n**Sources:** PC\n"
class Tests(unittest.TestCase):
 def parse(self,text=None):
  b,d=m.extract_definition_blocks(doc(text or definition()),"docs/test.md");self.assertFalse(d);return m.parse_definition(b[0])
 def test_relative_path(self):
  with tempfile.TemporaryDirectory() as t:self.assertEqual(m.resolve_from_repo(Path(t),Path("x")),(Path(t)/"x").resolve())
 def test_absolute_path(self):
    with tempfile.TemporaryDirectory() as temporary:
        path = (Path(temporary) / "x").resolve()
        self.assertEqual(m.resolve_from_repo(Path.cwd(), path), path)
 def test_missing_source(self):
  with self.assertRaises(m.ExtractionFailure):m.read_source(Path("/missing"))
 def test_invalid_utf8(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_bytes(b"\xff")
   with self.assertRaises(m.ExtractionFailure):m.read_source(p)
 def test_missing_section(self):self.assertEqual(m.extract_definition_blocks("# x","x")[1][0].code,"MISSING_DEFINITION_SECTION")
 def test_order(self):self.assertEqual([b.name for b in m.extract_definition_blocks(doc(definition("A")+definition("B")),"x")[0]],["A","B"])
 def test_duplicate(self):self.assertIn("DUPLICATE_MICRO_OPERATION",[d.code for d in m.extract_definition_blocks(doc(definition("A")+definition("A")),"x")[1]])
 def test_scalars(self):
  r,d=self.parse();self.assertFalse(d);self.assertEqual((r["category"],r["targets"],r["sources"]),("Control Flow",["PC"],["PC"]))
 def test_multiple_values(self):
  r,_=self.parse(definition().replace("**Target:** PC","**Target:** AC, L").replace("**Sources:** PC","**Sources:** AC, MB"));self.assertEqual(r["targets"],["AC","L"]);self.assertEqual(r["sources"],["AC","MB"])
 def test_none(self):
  for x in ("none","(none)"):
   r,_=self.parse(definition().replace("**Sources:** PC",f"**Sources:** {x}"));self.assertEqual(r["sources"],[])
 def test_multiline_expression(self):
  r,_=self.parse(definition().replace("**Expression:** PC ← PC + 1","**Expression:**\nAC ← MQ\nMQ ← AC"));self.assertEqual(r["expression"],["AC ← MQ","MQ ← AC"])
 def test_conditional(self):
  r,_=self.parse(definition().replace("**Expression:** PC ← PC + 1","**Expression:**\nif X:\nPC ← 1\nelse:\nPC ← 0"));self.assertEqual(len(r["expression"]),4)
 def test_lists(self):
  r,_=self.parse(definition()+"**Preconditions:**\n- Bus valid\n**Constraints:**\n- No conflict\n");self.assertEqual(r["preconditions"][0]["text"],"Bus valid");self.assertEqual(r["constraints"][0]["text"],"No conflict")
 def test_missing_attribute(self):
  _,d=self.parse("### X\n**Category:** X\n**Expression:** X ← 0\n");self.assertIn("MISSING_REQUIRED_ATTRIBUTE",[x.code for x in d])
 def test_duplicate_attribute(self):
  _,d=self.parse(definition().replace("**Category:** Control Flow","**Category:** A\n**Category:** B"));self.assertIn("DUPLICATE_ATTRIBUTE",[x.code for x in d])
 def test_inline_code_removed(self):
  r,_=self.parse(definition().replace("**Target:** PC","**Target:** `IOT_TRANSFER`").replace("**Sources:** PC","**Sources:** `IO_READ_REQ`, `IO_WRITE_REQ`"));self.assertEqual(r["targets"],["IOT_TRANSFER"]);self.assertEqual(r["sources"],["IO_READ_REQ","IO_WRITE_REQ"])
 def test_fences_removed(self):
  r,_=self.parse(definition().replace("**Expression:** PC ← PC + 1","**Expression:**\n```text\nX <- 1\n```"));self.assertEqual(r["expression"],["X <- 1"])
 def test_deterministic_json(self):
  result,_=m.build_result(doc(definition()),"x")
  with tempfile.TemporaryDirectory() as t:
   a=Path(t)/"a";b=Path(t)/"b";m.write_json(result,a);m.write_json(result,b);self.assertEqual(a.read_bytes(),b.read_bytes());self.assertTrue(a.read_text(encoding="utf-8").endswith("\n"))
 def test_complete_run(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=root/m.SOURCE_PATH;p.parent.mkdir(parents=True);p.write_text(doc(definition()),encoding="utf-8");self.assertEqual(m.run(["--repo-root",str(root)]),0);data = json.loads((root / m.DEFAULT_JSON_OUTPUT).read_text(encoding="utf-8"));self.assertEqual(data["micro_operations"][0]["name"],"PC_INC")
if __name__=="__main__":unittest.main()
