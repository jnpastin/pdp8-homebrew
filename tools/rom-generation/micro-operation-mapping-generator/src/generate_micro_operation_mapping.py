"""Generate a candidate micro-operation mapping from reviewed inputs."""
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

DEFAULT_MICRO_OPERATIONS=Path("build/simulation_outputs/rom-generation/micro-operation-extractor/micro-operations.json")
DEFAULT_CONTROL_WORD_SCHEMA=Path("rom/microcode/v1/control-word-schema.json")
DEFAULT_MAINTAINED_MAPPING=Path("rom/microcode/v1/micro-operation-mapping.json")
DEFAULT_CANDIDATE_OUTPUT=Path("build/simulation_outputs/rom-generation/micro-operation-mapping-generator/micro-operation-mapping.candidate.json")
DEFAULT_REPORT_OUTPUT=Path("build/simulation_outputs/rom-generation/micro-operation-mapping-generator/generation-report.txt")
MAPPING_SCHEMA_VERSION=1
CONTROL_DESIGN_VERSION="v1"

@dataclass(frozen=True)
class Diagnostic:
    severity:str; code:str; message:str
    micro_operation:str|None=None; field_name:str|None=None
    source_path:str|None=None; source_line:int|None=None

class GenerationFailure(Exception): pass

def parse_arguments(arguments:Sequence[str]|None=None)->argparse.Namespace:
    p=argparse.ArgumentParser(description="Generate a candidate micro-operation mapping.")
    p.add_argument("--repo-root",required=True,type=Path)
    p.add_argument("--micro-operations",type=Path,default=DEFAULT_MICRO_OPERATIONS)
    p.add_argument("--control-word-schema",type=Path,default=DEFAULT_CONTROL_WORD_SCHEMA)
    p.add_argument("--maintained-mapping",type=Path,default=DEFAULT_MAINTAINED_MAPPING)
    p.add_argument("--candidate-output",type=Path,default=DEFAULT_CANDIDATE_OUTPUT)
    p.add_argument("--report-output",type=Path,default=DEFAULT_REPORT_OUTPUT)
    return p.parse_args(arguments)

def resolve_from_repo(root:Path,path:Path)->Path:
    return path.resolve() if path.is_absolute() else (root/path).resolve()

def read_json(path:Path,*,optional:bool=False)->dict[str,Any]|None:
    if optional and not path.exists(): return None
    try: text=path.read_text(encoding="utf-8")
    except FileNotFoundError as e: raise GenerationFailure(f"Required input does not exist: {path}") from e
    except UnicodeDecodeError as e: raise GenerationFailure(f"Input is not valid UTF-8: {path}") from e
    except OSError as e: raise GenerationFailure(f"Unable to read input {path}: {e}") from e
    if optional and not text.strip(): return None
    try: value=json.loads(text)
    except json.JSONDecodeError as e: raise GenerationFailure(f"Input is not valid JSON: {path}: line {e.lineno}, column {e.colno}: {e.msg}") from e
    if not isinstance(value,dict): raise GenerationFailure(f"Input must contain a top-level JSON object: {path}")
    return value

def diag(severity,code,message,*,micro_operation=None,field_name=None,source=None):
    return Diagnostic(severity,code,message,micro_operation,field_name,
        source.get("path") if isinstance(source,dict) and isinstance(source.get("path"),str) else None,
        source.get("line") if isinstance(source,dict) and isinstance(source.get("line"),int) else None)

def validate_micro_operations(data:dict[str,Any])->list[Diagnostic]:
    d=[]
    if data.get("format_version")!=1:d.append(diag("ERROR","UNSUPPORTED_MICRO_OPERATION_FORMAT","Expected micro-operation format_version 1."))
    if data.get("extraction_stage")!="definition-validation":d.append(diag("ERROR","UNSUPPORTED_EXTRACTION_STAGE","Expected extraction_stage 'definition-validation'."))
    if data.get("diagnostics")!=[]:d.append(diag("ERROR","EXTRACTOR_DIAGNOSTICS_PRESENT","Micro-operation input contains diagnostics."))
    ops=data.get("micro_operations")
    if not isinstance(ops,list):return d+[diag("ERROR","INVALID_MICRO_OPERATIONS","micro_operations must be an array.")]
    seen=set()
    for op in ops:
        if not isinstance(op,dict):d.append(diag("ERROR","INVALID_MICRO_OPERATION","Micro-operation entry must be an object."));continue
        name=op.get("name"); src=op.get("source")
        if not isinstance(name,str) or not name:d.append(diag("ERROR","INVALID_MICRO_OPERATION_NAME","Micro-operation name must be non-empty.",source=src));continue
        if name in seen:d.append(diag("ERROR","DUPLICATE_MICRO_OPERATION",f"Micro-operation {name!r} appears more than once.",micro_operation=name,source=src))
        seen.add(name)
        if op.get("extraction_status")!="definition-validated":d.append(diag("ERROR","INVALID_EXTRACTION_STATUS","Micro-operation is not definition-validated.",micro_operation=name,source=src))
        for key in ("category","description","targets","expression","sources","preconditions","constraints","source"):
            if key not in op:d.append(diag("ERROR","MISSING_MICRO_OPERATION_PROPERTY",f"Micro-operation lacks {key!r}.",micro_operation=name,source=src))
        if not isinstance(src,dict) or not isinstance(src.get("path"),str) or not isinstance(src.get("heading"),str) or not isinstance(src.get("line"),int):d.append(diag("ERROR","INVALID_MICRO_OPERATION_SOURCE","Micro-operation source is invalid.",micro_operation=name))
    return d

def legal_encodings(field:dict[str,Any])->set[str]|None:
    values=field.get("values")
    if isinstance(values,list) and values:
        return {v.get("encoding") for v in values if isinstance(v,dict) and isinstance(v.get("encoding"),str) and str(v.get("meaning","")).casefold() not in {"reserved","invalid"}}
    width=field.get("width")
    if isinstance(width,int) and width>0:return {format(i,"o") for i in range(1<<width)}
    return None

def validate_schema(data:dict[str,Any])->tuple[list[Diagnostic],dict[str,dict[str,Any]]]:
    d=[]
    if data.get("specification_type")!="control-word-schema":d.append(diag("ERROR","INVALID_CONTROL_SCHEMA_TYPE","Expected control-word-schema input."))
    if data.get("schema_version")!=1:d.append(diag("ERROR","UNSUPPORTED_CONTROL_SCHEMA_VERSION","Expected control schema version 1."))
    if data.get("control_design_version")!=CONTROL_DESIGN_VERSION:d.append(diag("ERROR","CONTROL_DESIGN_VERSION_MISMATCH","Control design version must be v1."))
    fields=data.get("fields")
    if not isinstance(fields,list):return d+[diag("ERROR","INVALID_CONTROL_FIELDS","fields must be an array.")],{}
    index={}
    for f in fields:
        if not isinstance(f,dict):d.append(diag("ERROR","INVALID_CONTROL_FIELD","Control field must be an object."));continue
        name=f.get("name")
        if not isinstance(name,str) or not name:d.append(diag("ERROR","INVALID_CONTROL_FIELD_NAME","Control field name must be non-empty."));continue
        if name in index:d.append(diag("ERROR","DUPLICATE_CONTROL_FIELD",f"Control field {name!r} appears more than once.",field_name=name))
        index[name]=f
        if f.get("control_word_role") not in {"encoded","derived","external_input"}:d.append(diag("ERROR","INVALID_CONTROL_WORD_ROLE","Control field has invalid role.",field_name=name))
        if f.get("explicit_value_required") not in {"Yes","No","Conditionally"}:d.append(diag("ERROR","INVALID_EXPLICIT_VALUE_REQUIREMENT","Control field has invalid explicit-value requirement.",field_name=name))
        if not isinstance(f.get("value_required_when"),str):d.append(diag("ERROR","INVALID_VALUE_REQUIRED_WHEN","Control field lacks a valid value-required condition.",field_name=name))
    return d,index

def validate_maintained(data:dict[str,Any]|None)->tuple[list[Diagnostic],dict[str,dict[str,Any]]]:
    if data is None:return [],{}
    d=[]
    if data.get("specification_type")!="micro-operation-mapping":d.append(diag("ERROR","INVALID_MAPPING_TYPE","Expected micro-operation-mapping input."))
    if data.get("schema_version")!=MAPPING_SCHEMA_VERSION:d.append(diag("ERROR","UNSUPPORTED_MAPPING_VERSION","Expected mapping schema version 1."))
    if data.get("control_design_version")!=CONTROL_DESIGN_VERSION:d.append(diag("ERROR","MAPPING_DESIGN_VERSION_MISMATCH","Mapping control design version must be v1."))
    mappings=data.get("mappings")
    if not isinstance(mappings,list):return d+[diag("ERROR","INVALID_MAPPINGS","mappings must be an array.")],{}
    index={}
    for m in mappings:
        if not isinstance(m,dict):d.append(diag("ERROR","INVALID_MAPPING","Mapping must be an object."));continue
        name=m.get("micro_operation")
        if not isinstance(name,str) or not name:d.append(diag("ERROR","INVALID_MAPPING_NAME","Mapping micro_operation must be non-empty."));continue
        if name in index:d.append(diag("ERROR","DUPLICATE_MAPPING",f"Mapping {name!r} appears more than once.",micro_operation=name))
        index[name]=m
        if not isinstance(m.get("assignments"),list):d.append(diag("ERROR","INVALID_ASSIGNMENTS","assignments must be an array.",micro_operation=name))
        if not isinstance(m.get("notes"),list):d.append(diag("ERROR","INVALID_NOTES","notes must be an array.",micro_operation=name))
    return d,index

def validate_assignments(name:str,assignments:list[Any],fields:dict[str,dict[str,Any]],source:dict[str,Any])->list[Diagnostic]:
    d=[];seen={}
    for a in assignments:
        if not isinstance(a,dict):d.append(diag("ERROR","INVALID_ASSIGNMENT","Assignment must be an object.",micro_operation=name,source=source));continue
        field=a.get("field");value=a.get("value")
        if not isinstance(field,str) or not field:d.append(diag("ERROR","MISSING_ASSIGNMENT_FIELD","Assignment field must be non-empty.",micro_operation=name,source=source));continue
        if not isinstance(value,str) or not value:d.append(diag("ERROR","MISSING_ASSIGNMENT_VALUE","Assignment value must be a non-empty string.",micro_operation=name,field_name=field,source=source));continue
        if field in seen:d.append(diag("ERROR","DUPLICATE_FIELD_ASSIGNMENT",f"Field {field!r} is assigned more than once.",micro_operation=name,field_name=field,source=source))
        seen[field]=value
        definition=fields.get(field)
        if definition is None:d.append(diag("ERROR","UNDEFINED_ASSIGNED_FIELD",f"Field {field!r} is not defined.",micro_operation=name,field_name=field,source=source));continue
        role=definition.get("control_word_role")
        if role!="encoded":d.append(diag("ERROR","NON_ENCODED_ASSIGNMENT",f"Field {field!r} has role {role!r} and cannot be assigned.",micro_operation=name,field_name=field,source=source));continue
        legal=legal_encodings(definition)
        if legal is not None and value not in legal:d.append(diag("ERROR","INVALID_ASSIGNED_VALUE",f"Value {value!r} is not legal for field {field!r}.",micro_operation=name,field_name=field,source=source))
    return d

def build_candidate(micro_data,schema_data,maintained_data=None):
    d=[]; sd,fields=validate_schema(schema_data); d.extend(sd)
    md,maintained=validate_maintained(maintained_data); d.extend(md)
    if any(x.severity=="ERROR" for x in d):return None,d
    ops=micro_data["micro_operations"]; names={op["name"] for op in ops}; mappings=[]
    for op in ops:
        name=op["name"]; old=maintained.get(name); source=op["source"]
        assignments=list(old.get("assignments",[])) if old else []
        notes=list(old.get("notes",[])) if old else []
        if old is None or not assignments:d.append(diag("WARNING","MAPPING_UNRESOLVED","Micro-operation mapping has no reviewed assignments.",micro_operation=name,source=source))
        d.extend(validate_assignments(name,assignments,fields,source))
        mappings.append({"micro_operation":name,"assignments":assignments,"source":{"document":source["path"],"section":source["heading"],"line":source["line"]},"notes":notes})
    for name in maintained:
        if name not in names:d.append(diag("WARNING","STALE_MAINTAINED_MAPPING","Maintained mapping is absent from the extracted catalog.",micro_operation=name))
    candidate={"specification_type":"micro-operation-mapping","schema_version":MAPPING_SCHEMA_VERSION,"control_design_version":CONTROL_DESIGN_VERSION,"description":"Maps documented micro-operations to symbolic control-field assignments.","sources":{"micro_operations":DEFAULT_MICRO_OPERATIONS.as_posix(),"control_word_schema":DEFAULT_CONTROL_WORD_SCHEMA.as_posix()},"mappings":mappings,"diagnostics":[diagnostic_dict(x) for x in d]}
    return candidate,d

def diagnostic_dict(x:Diagnostic):
    r={"severity":x.severity,"code":x.code,"message":x.message}
    if x.micro_operation:r["micro_operation"]=x.micro_operation
    if x.field_name:r["field_name"]=x.field_name
    if x.source_path:r["source_path"]=x.source_path
    if x.source_line is not None:r["source_line"]=x.source_line
    return r

def write_json(data,path):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
def write_report(diags,path,count,written):
    counts={s:sum(x.severity==s for x in diags) for s in ("INFO","WARNING","ERROR","FATAL")}
    lines=["Micro-Operation Mapping Generation Report","=========================================","",f"Mappings processed: {count}",f"Candidate written: {'yes' if written else 'no'}",f"Information diagnostics: {counts['INFO']}",f"Warnings: {counts['WARNING']}",f"Errors: {counts['ERROR']}",f"Fatal errors: {counts['FATAL']}","","Diagnostics","-----------"]
    lines += [f"{x.severity} {x.code} [{x.micro_operation or '-'}]{' ['+x.field_name+']' if x.field_name else ''}: {x.message}" for x in diags] or ["No diagnostics."]
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
def run(arguments=None):
    a=parse_arguments(arguments);root=a.repo_root.resolve();diags=[];count=0;written=False
    try:
        micro=read_json(resolve_from_repo(root,a.micro_operations));schema=read_json(resolve_from_repo(root,a.control_word_schema));maintained=read_json(resolve_from_repo(root,a.maintained_mapping),optional=True)
        vd=validate_micro_operations(micro);diags.extend(vd);count=len(micro.get("micro_operations",[])) if isinstance(micro,dict) else 0
        if not any(x.severity=="ERROR" for x in diags):
            candidate,more=build_candidate(micro,schema,maintained);diags.extend(more)
            if candidate is not None and not any(x.severity=="ERROR" for x in diags):write_json(candidate,resolve_from_repo(root,a.candidate_output));written=True
    except GenerationFailure as e:diags.append(diag("FATAL","GENERATION_FAILURE",str(e)))
    try:write_report(diags,resolve_from_repo(root,a.report_output),count,written)
    except OSError as e:print(e,file=sys.stderr);return 1
    return 1 if any(x.severity in {"ERROR","FATAL"} for x in diags) else 0
def main():raise SystemExit(run())
if __name__=="__main__":main()
