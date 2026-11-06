"""Generate and validate a reviewable timing-constraint candidate."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
EXTRACTED=Path("build/simulation_outputs/rom-generation/timing-constraint-extractor/timing-constraints.json")
MAINTAINED=Path("rom/microcode/v1/timing-constraints.json")
CANDIDATE=Path("build/simulation_outputs/rom-generation/timing-constraint-generator/timing-constraints.candidate.json")
REPORT=Path("build/simulation_outputs/rom-generation/timing-constraint-generator/generation-report.txt")

def build(extracted,maintained=None):
 diagnostics=[];seen=set()
 for item in extracted.get("constraints",[]):
  for key in ("id","context","requirement","source"):
   if key not in item:diagnostics.append({"severity":"ERROR","code":"MISSING_FIELD","message":f"Constraint missing {key}.","constraint":item.get("id")})
  if item.get("id") in seen:diagnostics.append({"severity":"ERROR","code":"DUPLICATE_ID","message":"Duplicate constraint id.","constraint":item.get("id")})
  seen.add(item.get("id"))
 if extracted.get("diagnostics"):diagnostics.extend(extracted["diagnostics"])
 candidate={**extracted,"generation_stage":"candidate-generation","diagnostics":[]} if not diagnostics else None
 if candidate is not None and maintained is not None:
  old={x["id"]:x for x in maintained.get("constraints",[])};new={x["id"]:x for x in candidate["constraints"]}
  for key in sorted(new.keys()-old.keys()):diagnostics.append({"severity":"WARNING","code":"NEW_CONSTRAINT","message":"Constraint is new.","constraint":key})
  for key in sorted(old.keys()-new.keys()):diagnostics.append({"severity":"WARNING","code":"STALE_CONSTRAINT","message":"Maintained constraint is absent from extraction.","constraint":key})
 return candidate,diagnostics

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,required=True);a=p.parse_args(argv);root=a.repo_root.resolve();ex=json.loads((root/EXTRACTED).read_text());mp=root/MAINTAINED;maint=json.loads(mp.read_text()) if mp.exists() else None;c,d=build(ex,maint);out=root/CANDIDATE;rep=root/REPORT;out.parent.mkdir(parents=True,exist_ok=True);written=c is not None and not any(x["severity"]=="ERROR" for x in d)
 if written:out.write_text(json.dumps(c,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
 rep.write_text(("Timing-Constraint Generation Report\n===================================\n\n"+f"Constraints processed: {len(ex.get('constraints',[]))}\nCandidate written: {'yes' if written else 'no'}\nDiagnostics: {len(d)}\n\n"+"\n".join(f"{x['severity']} {x['code']} [{x.get('constraint','')}]: {x['message']}" for x in d)).rstrip("\n")+"\n",encoding="utf-8",newline="\n")
 errors=[x for x in d if x["severity"]=="ERROR"];print("Timing-constraint generation");print(f"Status: {'FAILED' if errors else 'SUCCEEDED'}");print(f"Constraints: {len(ex.get('constraints',[]))}");print(f"Candidate written: {'yes' if written else 'no'}");print(f"Diagnostics: {len(d)}");print(f"Candidate output: {out}");print(f"Report output: {rep}");return 1 if errors else 0
if __name__=="__main__":sys.exit(main())
