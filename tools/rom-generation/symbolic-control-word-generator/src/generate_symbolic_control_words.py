"""Generate predicate-preserving symbolic control words from maintained artifacts."""
from __future__ import annotations
import argparse,json,re,sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FILES={"inputs":"control-input-schema.json","words":"control-word-schema.json","mappings":"micro-operation-mapping.json","execution":"execution-definitions.json","direct":"direct-control-definitions.json","timing":"timing-constraints.json"}
class Failure(Exception): pass
@dataclass(frozen=True)
class Diagnostic:
 severity:str; code:str; message:str; source:str|None=None
 def dict(self): return {k:v for k,v in self.__dict__.items() if v is not None}
TOKEN=re.compile(r"\s*(?:(AND|OR|NOT)\b|(!=|=)|(is\s+not\s+selected|is\s+selected)\b|([()])|([^\s()=]+))",re.I)

def tokenize(text):
 out=[]; p=0
 while p<len(text):
  m=TOKEN.match(text,p)
  if not m: raise Failure(f"Unrecognized expression text near {text[p:p+24]!r}.")
  p=m.end()
  if m.group(1): out.append(("logic",m.group(1).upper()))
  elif m.group(2): out.append(("compare",m.group(2)))
  elif m.group(3): out.append(("selected"," ".join(m.group(3).upper().split())))
  elif m.group(4): out.append(("paren",m.group(4)))
  else: out.append(("name",m.group(5)))
 result=[]
 def ending(x): return x[0] in ("name","selected") or x==("paren",")")
 def starting(x): return x[0]=="name" or x==("paren","(") or x==("logic","NOT")
 for x in out:
  if result and ending(result[-1]) and starting(x): result.append(("logic","AND"))
  result.append(x)
 return result
class Parser:
 def __init__(self,text): self.t=tokenize(text); self.i=0
 def at(self,k,v=None): return self.i<len(self.t) and self.t[self.i][0]==k and (v is None or self.t[self.i][1]==v)
 def pop(self): x=self.t[self.i]; self.i+=1; return x
 def parse(self):
  if not self.t: raise Failure("Empty expression.")
  x=self.orx()
  if self.i!=len(self.t): raise Failure(f"Unexpected token {self.t[self.i][1]!r}.")
  return x
 def orx(self):
  x=self.andx()
  while self.at("logic","OR"): self.pop(); x=("or",x,self.andx())
  return x
 def andx(self):
  x=self.notx()
  while self.at("logic","AND"): self.pop(); x=("and",x,self.notx())
  return x
 def notx(self):
  if self.at("logic","NOT"): self.pop(); return ("not",self.notx())
  if self.at("paren","("):
   self.pop(); x=self.orx()
   if not self.at("paren",")"): raise Failure("Missing closing parenthesis.")
   self.pop(); return x
  return self.atom()
 def atom(self):
  if not self.at("name"): raise Failure("Expected a field or micro-operation name.")
  n=self.pop()[1]
  if self.at("compare"):
   op=self.pop()[1]
   if not self.at("name"): raise Failure(f"Missing value after {n} {op}.")
   return ("cmp",n,op,self.pop()[1])
  if self.at("selected"): return ("sel",n,self.pop()[1]=="IS SELECTED")
  raise Failure(f"Missing operator after {n}.")
def parse(text): return Parser(text).parse()
def canonical(x):
 k=x[0]
 if k=="const": return "true" if x[1] else "false"
 if k=="cmp": return f"{x[1]} {x[2]} {x[3]}"
 if k=="sel": return f"{x[1]} is {'selected' if x[2] else 'not selected'}"
 if k=="not": return f"NOT ({canonical(x[1])})"
 return f"({canonical(x[1])} {k.upper()} {canonical(x[2])})"
def fields_in(x):
 if x[0]=="const": return set()
 if x[0]=="cmp": return {x[1]}
 if x[0]=="sel": return set()
 if x[0]=="not": return fields_in(x[1])
 return fields_in(x[1])|fields_in(x[2])
def selected_in(x):
 if x[0]=="const": return set()
 if x[0]=="sel": return {x[1]}
 if x[0]=="cmp": return set()
 if x[0]=="not": return selected_in(x[1])
 return selected_in(x[1])|selected_in(x[2])
def conjunction(items):
 items=list(items)
 if not items: return None
 x=items[0]
 for y in items[1:]: x=("and",x,y)
 return x
def disjunction(items):
 items=list(items)
 if not items: raise Failure("Definition has no applicable context.")
 x=items[0]
 for y in items[1:]: x=("or",x,y)
 return x
def assignment_blocks(blocks):
 out=[]
 for block in blocks:
  for line in block.splitlines():
   if not line.strip(): continue
   m=re.fullmatch(r"\s*([^\s=]+)\s*=\s*([^\s]+)\s*",line)
   if not m: raise Failure(f"Malformed assignment {line!r}.")
   out.append(m.groups())
 return out
def encoding(field,value):
 value=str(value); vals=field.get("values",[])
 by_e={str(v["encoding"]):str(v["encoding"]) for v in vals}; by_m={str(v["meaning"]):str(v["encoding"]) for v in vals}
 if value in by_e:return by_e[value]
 if value in by_m:return by_m[value]
 aliases={"NONE":"0","READ":"1","WRITE":"2"}
 if value in aliases and aliases[value] in by_e:return aliases[value]
 if not vals:
  w=int(field["width"])
  if set(value)<={"0","1"} and len(value)<=w:return value.zfill(w)
  if value.isdigit() and int(value)<2**w:return format(int(value),f"0{w}b")
 raise Failure(f"Unknown encoding {value!r} for {field['name']}.")
def substitute_selected(x,selection):
 k=x[0]
 if k=="sel":
  name,want=x[1],x[2]
  if name not in selection:
   return ("const",not want)
  y=selection[name]
  return y if want else ("not",y)
 if k in ("cmp","const"):return x
 if k=="not":return ("not",substitute_selected(x[1],selection))
 return (k,substitute_selected(x[1],selection),substitute_selected(x[2],selection))
def evaluate(x,values,selected=None):
 selected=selected or set(); k=x[0]
 if k=="const": return x[1]
 if k=="cmp":
  if x[1] not in values:return None
  equal=values[x[1]]==x[3]; return equal if x[2]=="=" else not equal
 if k=="sel":return (x[1] in selected)==x[2]
 if k=="not":
  v=evaluate(x[1],values,selected);return None if v is None else not v
 a=evaluate(x[1],values,selected);b=evaluate(x[2],values,selected)
 if k=="and":
  if a is False or b is False:return False
  return True if a is True and b is True else None
 if a is True or b is True:return True
 return False if a is False and b is False else None
def domains_for(a,words):
 result={"TS":[str(x) for x in range(1,5)]}
 for f in a["inputs"]["fields"]:
  vals=[str(x["value"]) for x in f.get("values",[]) if "value" in x]
  if vals:result[f["name"]]=list(dict.fromkeys(vals))
 for n,f in words.items():result[n]=list(dict.fromkeys([str(x["encoding"]) for x in f.get("values",[])])) or [format(x,f"0{int(f['width'])}b") for x in range(2**int(f["width"]))]
 return result
def satisfiable(x,domains):
 names=sorted(fields_in(x)); assigned={}
 def visit(i):
  v=evaluate(x,assigned)
  if v is not None:return v
  if i==len(names):return False
  name=names[i]
  if name not in domains:raise Failure(f"No documented value domain for {name}.")
  for value in domains[name]:
   assigned[name]=value
   if visit(i+1):return True
  assigned.pop(name,None);return False
 return visit(0)

def fixed_equalities(x,out=None):
 out={} if out is None else out
 if x is None:return out
 if x[0]=="and": fixed_equalities(x[1],out);fixed_equalities(x[2],out)
 elif x[0]=="cmp" and x[2]=="=": out.setdefault(x[1],set()).add(x[3])
 return out
def impossible_with_base(condition,base):
 b=fixed_equalities(base); c=fixed_equalities(condition)
 return any(n in b and b[n].isdisjoint(v) for n,v in c.items())
def literals_in(x,out=None):
 out={} if out is None else out
 if x[0]=="cmp":out.setdefault(x[1],set()).add(x[3])
 elif x[0]=="not":literals_in(x[1],out)
 elif x[0] in ("and","or"):literals_in(x[1],out);literals_in(x[2],out)
 return out
def mutually_exclusive_pairs(input_fields,global_constraints=()):
 pairs=set()
 pattern=re.compile(r"^Mutually exclusive with ([^.`]+)\.?$")
 for field in input_fields:
  for constraint in field.get("constraints",[]):
   match=pattern.fullmatch(constraint.get("text", "").strip())
   if match:
    pairs.add(frozenset((field["name"], match.group(1).strip())))
 for constraint in global_constraints:
  if constraint.get("kind") not in ("exactly_one","at_most_one"):continue
  names=constraint.get("inputs",[])
  for i,left in enumerate(names):
   for right in names[i+1:]:pairs.add(frozenset((left,right)))
 return pairs
def violates_mutual_exclusion(values,exclusive_pairs):
 return any(all(values.get(name)=="1" for name in pair) for pair in exclusive_pairs)
def guards_overlap(a,b,exclusive_pairs):
 x=conjunction([a,b]); literals=literals_in(x); selections=sorted(selected_in(x)); names=sorted(literals); values={n:sorted(v|{"__OTHER__"}) for n,v in literals.items()}
 def visit_fields(i,env):
  if i==len(names):
   if violates_mutual_exclusion(env,exclusive_pairs):return False
   return visit_selected(0,env,set())
  for value in values[names[i]]:
   env[names[i]]=value
   if visit_fields(i+1,env):return True
  env.pop(names[i],None);return False
 def visit_selected(i,env,selected):
  if i==len(selections):return evaluate(x,env,selected) is True
  if visit_selected(i+1,env,selected):return True
  selected.add(selections[i]); result=visit_selected(i+1,env,selected);selected.remove(selections[i]);return result
 return visit_fields(0,{})

def timing_violations(a):
 rules=[]
 for item in a["timing"].get("constraints",[]):
  context=parse(item["context"])
  requirement=parse(item["requirement"])
  rules.append((item["id"],conjunction([context,("not",requirement)])))
 return rules
def constrained_guards_overlap(a,b,exclusive_pairs,timing_rules):
 x=conjunction([a,b]); literals=literals_in(x); selections=sorted(selected_in(x)); names=sorted(literals); values={n:sorted(v|{"__OTHER__"}) for n,v in literals.items()}
 for _,violation in timing_rules:
  for n,v in literals_in(violation).items(): values.setdefault(n,sorted(v|{"__OTHER__"}));
 names=sorted(values)
 def visit_fields(i,env):
  if i==len(names):
   if violates_mutual_exclusion(env,exclusive_pairs):return False
   return visit_selected(0,env,set())
  name=names[i]
  for value in values[name]:
   env[name]=value
   if visit_fields(i+1,env):return True
  env.pop(name,None);return False
 def visit_selected(i,env,selected):
  if i<len(selections):
   if visit_selected(i+1,env,selected):return True
   selected.add(selections[i]);result=visit_selected(i+1,env,selected);selected.remove(selections[i]);return result
  if evaluate(x,env,selected) is not True:return False
  return not any(evaluate(violation,env,selected) is True for _,violation in timing_rules)
 return visit_fields(0,{})
def load(directory): return {k:json.loads((directory/v).read_text(encoding="utf-8")) for k,v in FILES.items()}

def generate(a):
 diagnostics=[]; input_fields=a["inputs"]["fields"]; inputs={x["name"] for x in input_fields}; exclusive_pairs=mutually_exclusive_pairs(input_fields,a["inputs"].get("constraints",[])); timing_rules=timing_violations(a); words={x["name"]:x for x in a["words"]["fields"] if x.get("control_word_role")=="encoded"}; maps={x["micro_operation"]:x for x in a["mappings"]["mappings"]}; domains=domains_for(a,words)
 direct=[]
 for d in a["direct"]["definitions"]:
  try:
   expr=disjunction(parse(x) for x in d["applicable_context"])
   for n in fields_in(expr):
    if n not in inputs and n not in words and n not in {"MS","TS"}: raise Failure(f"Unknown context field {n}.")
   for n in selected_in(expr):
    if n not in maps: raise Failure(f"Unknown selected micro-operation {n}.")
   direct.append((d,expr))
  except Failure as e: diagnostics.append(Diagnostic("ERROR","INVALID_DIRECT_CONTROL",str(e),d.get("id")).dict())
 if diagnostics:return None,diagnostics
 cases=[]
 for case in a["execution"]["cases"]:
  try:
   base_parts=[parse(x) for x in case["context"]]
   if case.get("timing_state") is not None: base_parts.append(("cmp","TS","=",str(case["timing_state"])))
   base=conjunction(base_parts); selection={u:base for u in case["micro_operations"]}
   rules=[]
   for item in case["conditional_micro_operations"]:
    if item["micro_operation"] not in maps: raise Failure(f"Unknown micro-operation {item['micro_operation']}.")
    selection[item["micro_operation"]]=conjunction([base,parse(item["predicate"])])
   defaults={n:encoding(f,f["default_value"]) for n,f in words.items()}
   assignments={n:[] for n in words}
   def add(field,value,guard,origin,source):
    if field not in words: raise Failure(f"Unknown encoded field {field}.")
    encoded=encoding(words[field],value)
    current_when=canonical(guard) if guard else "always"
    for prior in assignments[field]:
     if "value" in prior and prior["value"]!=encoded and constrained_guards_overlap(prior["_guard"],guard,exclusive_pairs,timing_rules):
      raise Failure(
       f"Conflicting assignments for {field} in execution case {case['id']}: "
       f"{prior['value']} from {prior['origin']} {prior['source']} "
       f"when {prior['when']}; {encoded} from {origin} {source} "
       f"when {current_when}."
      )
    assignments[field].append({"value":encoded,"when":current_when,"origin":origin,"source":source,"_guard":guard})
   for u,guard in selection.items():
    if u not in maps: raise Failure(f"Unknown micro-operation {u}.")
    origin="micro-operation mapping" if u in case["micro_operations"] else "conditional micro-operation mapping"
    for x in maps[u]["assignments"]: add(x["field"],x["value"],guard,origin,u)
   applicable=[]
   for d,expr in direct:
    resolved_expr=substitute_selected(expr,selection)
    if not constrained_guards_overlap(base,resolved_expr,exclusive_pairs,timing_rules):
     continue
    guard=conjunction([base,resolved_expr])
    applicable.append(d["id"])
    for f,v in assignment_blocks(d["direct_assignments"]): add(f,v,guard,"direct-control definition",d["id"])
    for f,v in assignment_blocks(d["control_supplied_values"]):
     if v not in inputs: add(f,v,guard,"control-supplied value",d["id"])
     else: assignments[f].append({"value_from_input":v,"when":canonical(guard),"origin":"control-supplied value","source":d["id"],"_guard":guard})
   public_assignments={f:[{k:v for k,v in item.items() if k!="_guard"} for item in items] for f,items in assignments.items()}
   cases.append({"execution_case_id":case["id"],"source":case["source"],"base_context":canonical(base) if base else "always","defaults":defaults,"field_assignments":public_assignments,"selected_micro_operations":{u:canonical(g) if g else "always" for u,g in sorted(selection.items())},"applicable_direct_control_definitions":applicable})
  except Failure as e: diagnostics.append(Diagnostic("ERROR","CASE_GENERATION_FAILED",str(e),case["id"]).dict())
 if diagnostics:return None,diagnostics
 return {"format_version":1,"control_design_version":a["words"]["control_design_version"],"artifact":"symbolic-control-words","representation":"predicate-preserving","sources":list(FILES.values()),"cases":cases,"diagnostics":[]},[]
def validate_symbolic_artifact(artifact,a):
 diagnostics=[]
 words={x["name"]:x for x in a["words"]["fields"] if x.get("control_word_role")=="encoded"}
 execution={x["id"] for x in a["execution"]["cases"]}
 cases=artifact.get("cases",[])
 seen=set()
 for case in cases:
  cid=case.get("execution_case_id")
  if cid in seen: diagnostics.append(Diagnostic("ERROR","DUPLICATE_EXECUTION_CASE",f"Execution case {cid} appears more than once.",cid).dict())
  seen.add(cid)
  defaults=case.get("defaults",{})
  if set(defaults)!=set(words): diagnostics.append(Diagnostic("ERROR","INCOMPLETE_FIELD_COVERAGE",f"Defaults do not cover every encoded control-word field.",cid).dict())
  for field,value in defaults.items():
   if field not in words: continue
   try: encoding(words[field],value)
   except Failure as e: diagnostics.append(Diagnostic("ERROR","INVALID_DEFAULT",str(e),cid).dict())
  assignments=case.get("field_assignments",{})
  if set(assignments)!=set(words): diagnostics.append(Diagnostic("ERROR","INCOMPLETE_ASSIGNMENT_COVERAGE",f"Field-assignment map does not cover every encoded control-word field.",cid).dict())
  for field,items in assignments.items():
   if field not in words:
    diagnostics.append(Diagnostic("ERROR","UNKNOWN_SYMBOLIC_FIELD",f"Unknown symbolic field {field}.",cid).dict());continue
   for item in items:
    if "value" in item:
     try: encoding(words[field],item["value"])
     except Failure as e: diagnostics.append(Diagnostic("ERROR","INVALID_SYMBOLIC_VALUE",str(e),cid).dict())
    elif "value_from_input" not in item:
     diagnostics.append(Diagnostic("ERROR","MISSING_SYMBOLIC_VALUE",f"Assignment for {field} has neither value nor value_from_input.",cid).dict())
    if not item.get("when") or not item.get("origin") or not item.get("source"):
     diagnostics.append(Diagnostic("ERROR","INCOMPLETE_PROVENANCE",f"Assignment for {field} lacks guard or provenance.",cid).dict())
 if seen!=execution:
  missing=sorted(execution-seen);extra=sorted(seen-execution)
  diagnostics.append(Diagnostic("ERROR","EXECUTION_CASE_COVERAGE",f"Execution-case coverage mismatch; missing={missing}, extra={extra}.").dict())
 return diagnostics

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--artifact-dir",type=Path);n=p.parse_args(argv);root=n.repo_root.resolve();ad=n.artifact_dir or root/"rom/microcode/v1";out=root/"build/simulation_outputs/rom-generation/symbolic-control-word-generator";out.mkdir(parents=True,exist_ok=True);candidate=out/"symbolic-control-words.candidate.json";report=out/"generation-report.json";source_artifacts=load(ad);artifact,diag=generate(source_artifacts);
 if artifact is not None and not diag:diag=validate_symbolic_artifact(artifact,source_artifacts);artifact=None if diag else artifact;
 if artifact is not None:candidate.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
 elif candidate.exists():candidate.unlink()
 report.write_text(json.dumps({"diagnostics":diag},indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
 print("Symbolic control-word generation")
 print(f"Status: {'FAILED' if diag else 'SUCCEEDED'}")
 print(f"Cases: {len(artifact['cases']) if artifact else 0}")
 print(f"Candidate written: {'yes' if artifact is not None else 'no'}")
 print(f"Diagnostics: {len(diag)}")
 print(f"Candidate output: {candidate}")
 print(f"Report output: {report}")
 return 1 if diag else 0
if __name__=="__main__":sys.exit(main())
