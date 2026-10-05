"""Extract normalized micro-operation definitions from project documentation."""
from __future__ import annotations
import argparse,json,re,sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
SOURCE_PATH=Path("docs/03-microarchitecture/02-micro-operations.md")
DEFAULT_JSON_OUTPUT=Path("build/simulation_outputs/rom-generation/micro-operation-extractor/micro-operations.json")
DEFAULT_REPORT_OUTPUT=Path("build/simulation_outputs/rom-generation/micro-operation-extractor/extraction-report.txt")
DEFINITION_TITLE="5. μop Definitions (Alphabetical)"
ATTRS={"category","description","target","expression","sources"}
REQUIRED={"category","description","target","sources"}
@dataclass(frozen=True)
class Diagnostic:
 severity:str; code:str; message:str; source_path:str; line:int|None=None; micro_operation:str|None=None
@dataclass(frozen=True)
class DefinitionBlock:
 name:str; source_path:str; start_line:int; lines:tuple[str,...]
class ExtractionFailure(Exception): pass
def normalize_markdown(s:str)->str:
 s=s.replace("\\_","_").replace("\\<","<").replace("\\>",">")
 return re.sub(r"`([^`]+)`",r"\1",s)
def is_code_fence(s:str)->bool:return re.fullmatch(r"\s*`{3,}(?:[A-Za-z0-9_-]+)?\s*",s) is not None
def heading(s:str):
 m=re.match(r"^(#{1,6})\s+(.+?)\s*$",s)
 return (len(m.group(1)),normalize_markdown(m.group(2))) if m else None
def resolve_from_repo(root:Path,p:Path)->Path:return p.resolve() if p.is_absolute() else (root/p).resolve()
def read_source(p:Path)->str:
 try:return p.read_text(encoding="utf-8")
 except FileNotFoundError as e:raise ExtractionFailure(f"Source file does not exist: {p}") from e
 except UnicodeDecodeError as e:raise ExtractionFailure(f"Source file is not valid UTF-8: {p}") from e
def section_bounds(lines:Sequence[str]):
 for i,line in enumerate(lines):
  h=heading(line)
  if h and h[1]==DEFINITION_TITLE:
   for j in range(i+1,len(lines)):
    q=heading(lines[j])
    if q and q[0]<=h[0]:return i+1,j,h[0]+1
   return i+1,len(lines),h[0]+1
 return None
def extract_definition_blocks(text:str,source_path:str):
 lines=text.splitlines(); b=section_bounds(lines)
 if not b:return [],[Diagnostic("ERROR","MISSING_DEFINITION_SECTION",f"Section {DEFINITION_TITLE!r} was not found.",source_path)]
 start,end,level=b; out=[]; diags=[]; seen=set(); current=None
 for i in range(start,end):
  h=heading(lines[i])
  if h and h[0]==level:
   if current:out.append(DefinitionBlock(*current))
   name=h[1]
   if name in seen:diags.append(Diagnostic("ERROR","DUPLICATE_MICRO_OPERATION",f"Micro-operation {name!r} is defined more than once.",source_path,i+1,name))
   seen.add(name);current=[name,source_path,i+1,[]]
  elif current:current[3].append(lines[i])
 if current:out.append(DefinitionBlock(current[0],current[1],current[2],tuple(current[3])))
 if not out:diags.append(Diagnostic("ERROR","NO_MICRO_OPERATIONS","No micro-operation definitions were found.",source_path))
 return out,diags
def expand(lines):
 marker=re.compile(r"(?=\*\*(?:Category|Description|Target|Expression|Sources|Preconditions|Constraints):\*\*)")
 return [(part,off) for off,line in enumerate(lines) for part in ([p for p in marker.split(line) if p] or [line])]
def label(line):
 m=re.match(r"^\s*\*\*([^*]+):\*\*\s*(.*)$",line)
 if not m:return None
 k=m.group(1).strip().casefold()
 return (k,normalize_markdown(m.group(2).strip())) if k in ATTRS else None
def split_csv(s):return [normalize_markdown(x.strip()) for x in s.split(",") if x.strip()]
def parse_definition(block:DefinitionBlock):
 lines=expand(block.lines); vals={}; pre=[]; con=[]; diags=[]; i=0
 while i<len(lines):
  raw,off=lines[i]; sm=re.match(r"^\s*\*\*(Preconditions|Constraints):\*\*\s*(.*)$",raw)
  if sm:
   dest=pre if sm.group(1)=="Preconditions" else con; inline=normalize_markdown(sm.group(2).strip())
   if inline:dest.append({"text":inline,"source":{"path":block.source_path,"line":block.start_line+off+1}})
   i+=1
   while i<len(lines):
    r,o=lines[i]
    if label(r) or re.match(r"^\s*\*\*(Preconditions|Constraints):\*\*",r):break
    m=re.match(r"^\s*-\s+(.+?)\s*$",r)
    if m:dest.append({"text":normalize_markdown(m.group(1)),"source":{"path":block.source_path,"line":block.start_line+o+1}})
    elif r.strip() and r.strip()!="---":break
    i+=1
   continue
  p=label(raw)
  if not p:i+=1;continue
  key,first=p
  if key in vals:diags.append(Diagnostic("ERROR","DUPLICATE_ATTRIBUTE",f"Attribute {key!r} occurs more than once.",block.source_path,block.start_line+off+1,block.name))
  collected=[first] if first else [];i+=1
  while i<len(lines):
   r,_=lines[i]
   if label(r) or re.match(r"^\s*\*\*(Preconditions|Constraints):\*\*",r):break
   if not is_code_fence(r):
    x=normalize_markdown(r.strip())
    if x and x!="---":
     m=re.match(r"^-\s+(.+)$",x);collected.append(m.group(1) if key=="sources" and m else x)
   i+=1
  vals[key]=collected
 for key in REQUIRED:
  if key not in vals:diags.append(Diagnostic("ERROR","MISSING_REQUIRED_ATTRIBUTE",f"Definition does not specify {key}.",block.source_path,block.start_line,block.name))
 if not vals.get("expression"):diags.append(Diagnostic("ERROR","MISSING_EXPRESSION","Definition does not specify an expression.",block.source_path,block.start_line,block.name))
 src=vals.get("sources",[])
 sources=[] if len(src)==1 and src[0].casefold() in {"none","(none)"} else [x for line in src for x in split_csv(line)]
 result={"name":block.name,"category":" ".join(vals.get("category",[])),"description":" ".join(vals.get("description",[])),"targets":split_csv(" ".join(vals.get("target",[]))),"expression":vals.get("expression",[]),"sources":sources,"preconditions":pre,"constraints":con,"source":{"path":block.source_path,"heading":block.name,"line":block.start_line},"extraction_status":"definition-error" if any(d.severity=="ERROR" for d in diags) else "definition-validated"}
 return result,diags
def dto(d):
 x={"severity":d.severity,"code":d.code,"message":d.message,"source_path":d.source_path}
 if d.line is not None:x["line"]=d.line
 if d.micro_operation:x["micro_operation"]=d.micro_operation
 return x
def build_result(text,source_path):
 blocks,diags=extract_definition_blocks(text,source_path);ops=[]
 for b in blocks:
  op,ds=parse_definition(b);ops.append(op);diags.extend(ds)
 return {"format_version":1,"extraction_stage":"definition-validation","source":{"path":source_path},"micro_operations":ops,"diagnostics":[dto(d) for d in diags]},diags
def write_json(result,path):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
def write_report(diags,path,count,written):
 counts={k:sum(d.severity==k for d in diags) for k in ("INFO","WARNING","ERROR","FATAL")};lines=["Micro-Operation Extraction Report","=================================","",f"Micro-operations processed: {count}",f"JSON written: {'yes' if written else 'no'}",f"Information diagnostics: {counts['INFO']}",f"Warnings: {counts['WARNING']}",f"Errors: {counts['ERROR']}",f"Fatal errors: {counts['FATAL']}","","Diagnostics","-----------"]
 lines += [f"{d.severity} {d.code} [{d.micro_operation or '-'}] {d.source_path}{':' + str(d.line) if d.line else ''}: {d.message}" for d in diags] or ["No diagnostics."]
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
def run(arguments=None):
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True,type=Path);ap.add_argument("--json-output",type=Path,default=DEFAULT_JSON_OUTPUT);ap.add_argument("--report-output",type=Path,default=DEFAULT_REPORT_OUTPUT);a=ap.parse_args(arguments);root=a.repo_root.resolve();diags=[];count=0;written=False
 try:
  sp=resolve_from_repo(root,SOURCE_PATH);result,diags=build_result(read_source(sp),sp.relative_to(root).as_posix());count=len(result["micro_operations"]);write_json(result,resolve_from_repo(root,a.json_output));written=True
 except ExtractionFailure as e:diags=[Diagnostic("FATAL","EXTRACTION_FAILURE",str(e),SOURCE_PATH.as_posix())]
 write_report(diags,resolve_from_repo(root,a.report_output),count,written);return 1 if any(d.severity=="FATAL" for d in diags) else 0
def main():raise SystemExit(run())
if __name__=="__main__":main()
