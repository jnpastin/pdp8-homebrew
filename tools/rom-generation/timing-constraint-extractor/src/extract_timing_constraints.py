"""Extract machine-readable timing constraints from nested documentation bullets."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path

SOURCE=Path("docs/09-timing/03-major-state-timing.md")
OUTPUT=Path("build/simulation_outputs/rom-generation/timing-constraint-extractor/timing-constraints.json")
REPORT=Path("build/simulation_outputs/rom-generation/timing-constraint-extractor/extraction-report.txt")
CONSTRAINT=re.compile(r"^\s{2,}-\s+`([^`]+\s+IF\s+[^`]+)`\s*$")
TS_HEADING=re.compile(r"^#{4,5}\s+.*\bTS([1-4])\b")

def parse(text:str,path:str)->dict:
 lines=text.splitlines(); constraints=[]; diagnostics=[]; ts=None
 for number,line in enumerate(lines,1):
  heading=TS_HEADING.match(line)
  if heading: ts=int(heading.group(1))
  match=CONSTRAINT.match(line)
  if not match: continue
  expression=match.group(1).strip()
  if ts is None:
   diagnostics.append({"severity":"ERROR","code":"MISSING_TIMING_CONTEXT","message":"Constraint is not under a TS heading.","source":{"path":path,"line":number}});continue
  if " IF " not in expression:
   diagnostics.append({"severity":"ERROR","code":"MALFORMED_CONSTRAINT","message":"Constraint must contain IF.","source":{"path":path,"line":number}});continue
  requirement,condition=expression.split(" IF ",1)
  constraints.append({"id":f"timing:{number}","context":f"TS = {ts} AND ({condition})","requirement":requirement,"source":{"path":path,"line":number}})
 return {"format_version":1,"control_design_version":"v1","artifact":"timing-constraints","generation_stage":"extraction","sources":[path],"constraints":constraints,"diagnostics":diagnostics}

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,required=True);a=p.parse_args(argv);root=a.repo_root.resolve();src=root/SOURCE;out=root/OUTPUT;report=root/REPORT;out.parent.mkdir(parents=True,exist_ok=True)
 result=parse(src.read_text(encoding="utf-8"),SOURCE.as_posix());out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");report.write_text(f"Timing-constraint extraction\nStatus: {'FAILED' if result['diagnostics'] else 'SUCCEEDED'}\nConstraints: {len(result['constraints'])}\nDiagnostics: {len(result['diagnostics'])}\n",encoding="utf-8")
 print("Timing-constraint extraction");print(f"Status: {'FAILED' if result['diagnostics'] else 'SUCCEEDED'}");print(f"Constraints: {len(result['constraints'])}");print(f"Diagnostics: {len(result['diagnostics'])}");print(f"JSON output: {out}");print(f"Report output: {report}");return 1 if result['diagnostics'] else 0
if __name__=="__main__":sys.exit(main())
