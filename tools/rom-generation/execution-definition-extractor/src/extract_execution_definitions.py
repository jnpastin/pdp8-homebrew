"""Extract normalized execution definitions from authoritative ISA and microarchitecture docs."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

DOCS = (
    "04-fetch-defer.md",
    "05-mri-execution.md",
    "06-iot-execution.md",
    "08-interrupt-execution.md",
    "09-console-execution.md",
    "01-group1-execution.md",
    "02-group2-execution.md",
    "03-group3-execution.md",
)
ISA_DOCS = ("01-group-1.md", "02-group-2.md", "03-group-3.md")
DEFAULT_OUTPUT = Path("build/simulation_outputs/rom-generation/execution-definition-extractor/execution-definitions.json")
DEFAULT_REPORT = Path("build/simulation_outputs/rom-generation/execution-definition-extractor/extraction-report.txt")


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    source: str
    line: int | None = None


class ExtractionFailure(Exception): pass


def read(path: Path) -> str:
    try: return path.read_text(encoding="utf-8")
    except OSError as e: raise ExtractionFailure(f"Unable to read {path}: {e}") from e


def clean(text: str) -> str:
    return (
        text.replace("\\_", "_")
        .replace("\\[", "[")
        .replace("\\]", "]")
        .strip()
        .strip("`")
        .strip()
    )


def code_after(lines: list[str], index: int) -> tuple[list[str], int]:
    i=index+1
    while i<len(lines) and not lines[i].strip(): i+=1
    if i>=len(lines) or not lines[i].strip().startswith("```"): return [], index
    i+=1; values=[]
    while i<len(lines) and not lines[i].strip().startswith("```"):
        if lines[i].strip(): values.append(clean(lines[i].strip()))
        i+=1
    return values,i


def bullets_after(lines:list[str], index:int) -> list[str]:
    out=[]; i=index+1
    while i<len(lines):
        s=lines[i].strip()
        if not s: i+=1; continue
        if re.match(r"^(?:TS[1-4]|Conditional μops|Description|Result|Control Decisions|Applicable context|Execution model):",s) or s.startswith("#"): break
        if s.startswith("-"):
            value = clean(s[1:].strip())
            if value not in {"", "--", "(no μops)", "(no unconditional μops)"}:
                out.append(value)
        else: break
        i+=1
    return out


def conditional_after(lines:list[str], index:int) -> list[dict]:
    vals,_=code_after(lines,index); out=[]
    for value in vals:
        m=re.match(r"^(.+?)\s*->\s*([A-Z][A-Z0-9_]*)$",value)
        if not m: continue
        out.append({"predicate":clean(m.group(1)),"micro_operation":m.group(2)})
    return out


OPR_GROUP_INPUTS = {
    1: "IR_OPR_GROUP1",
    2: "IR_OPR_GROUP2",
    3: "IR_OPR_GROUP3",
}

OPR_BIT_INPUTS = {
    1: {
        "CLA": "IR_OPR_CLA",
        "CLL": "IR_OPR_CLL",
        "CMA": "IR_OPR_CMA",
        "CML": "IR_OPR_CML",
        "RAR": "IR_OPR_RAR",
        "RAL": "IR_OPR_RAL",
        "BSW": "IR_OPR_BSW",
        "IAC": "IR_OPR_IAC",
    },
    2: {
        "CLA": "IR_OPR_CLA",
        "OSR": "IR_OPR_OSR",
        "HLT": "IR_OPR_HLT",
    },
    3: {
        "CLA": "IR_OPR_CLA",
    },
}

def normalize_context_term(term: str) -> str:
    value = clean(term.strip())
    match = re.fullmatch(r"IR\[11:9\] = ([01]{3})", value)
    if match:
        opcode = match.group(1)
        if opcode in {"000", "001", "010", "011", "100", "101"}:
            return f"IR_MRI_OPCODE = {opcode}"
        if opcode == "110":
            return "IR_IS_IOT = 1"
    match = re.fullmatch(r"IR\[2:0\] = ([01]{3})", value)
    if match:
        return f"IR_IOT_OP = {match.group(1)}"
    if value.startswith("IOA = "):
        return "IR_IOA = " + value.removeprefix("IOA = ")
    return value

def normalize_opr_predicate(
    predicate: str, bits: dict[str, int], group: int
) -> str:
    result = clean(predicate)
    for mnemonic, input_name in OPR_BIT_INPUTS[group].items():
        bit = bits.get(mnemonic)
        if bit is not None:
            result = re.sub(rf"IR\[{bit}\]", input_name, result)
    return result

def parse_bit_diagram(text:str) -> dict[str,int]:
    """Parse the agreed three-row OPR bit diagram: position, required value, mnemonic."""
    lines=text.splitlines()
    for i,line in enumerate(lines):
        if "│ 11 │" not in line: continue
        window=lines[i:i+8]
        if len(window)<5: continue
        mnemonic_line=next((x for x in window[2:] if any(k in x for k in ("CLA","MQA","SPA","SMA","IAC"))),None)
        if not mnemonic_line: continue
        # Box-cell spans make positional splitting unreliable; derive from explicit labels by row columns.
        # Since every diagram is fixed-width, use cell center positions from the top row.
        centers=[]
        for m in re.finditer(r"\b(11|10|[0-9])\b",line): centers.append((int(m.group(1)),m.start()))
        result={}
        for name in ("CLA","CLL","CMA","CML","RAR","RAL","BSW","IAC","SPA","SNA","SZL","SMA","SZA","SNL","OSR","HLT","MQA","MQL"):
            pos=mnemonic_line.find(name)
            if pos>=0 and centers:
                bit=min(centers,key=lambda x:abs(x[1]-pos))[0]; result[name]=bit
        if result: return result
    return {}


def case(case_id, source, line, context, ts, uops=None, conditional=None, execution_model="major-state"):
    return {"id":case_id,"source":{"path":source,"line":line},"execution_model":execution_model,"context":context,"timing_state":ts,"micro_operations":uops or [],"conditional_micro_operations":conditional or []}


def parse_fetch_defer(text:str, source:str):
    lines=text.splitlines(); out=[]; state=None
    for i,l in enumerate(lines):
        if l.startswith("## 3. FETCH"): state="FETCH"
        elif l.startswith("## 4. DEFER"): state="DEFER"
        m=re.match(r"^###\s+(\d+\.\d+)\s+TS([1-4])",l)
        if not (state and m): continue
        end=next((j for j in range(i+1,len(lines)) if lines[j].startswith(("### ","## "))),len(lines))
        block=lines[i:end]; u=[]; cond=[]
        for k,x in enumerate(block):
            if x.strip()=="μops:": u=bullets_after(block,k)
            elif x.strip()=="Conditional μops:": cond=conditional_after(block,k)
        out.append(case(f"fetch-defer:{m.group(1)}",source,i+1,[f"MS = {state}"],int(m.group(2)),u,cond))
    return out


IOT_DECODED_CONTEXTS = {
    "10.1": ["IR_IS_IOT = 1", "IR_WRITES_DF = 1"],
    "10.2": ["IR_IS_IOT = 1", "IR_WRITES_IF = 1"],
    "10.3": ["IR_IS_IOT = 1", "IR_READS_DF = 1"],
    "10.4": ["IR_IS_IOT = 1", "IR_READS_IF = 1"],
    "10.5": ["IR_IS_IOT = 1", "IR_READS_IB = 1"],
    "10.6": ["IR_IS_IOT = 1", "IR_RESTORES_IB = 1"],
}


def normalize_execute_context(prefix: str, number: str, title: str) -> list[str]:
    if prefix == "iot" and number in IOT_DECODED_CONTEXTS:
        return list(IOT_DECODED_CONTEXTS[number])
    context = [normalize_context_term(x) for x in re.split(r"\s+AND\s+", title)]
    if prefix == "mri":
        return ["IR_IS_MRI = 1", *context]
    return context


def parse_numbered_execute(text:str,source:str,prefix:str):
    lines=text.splitlines(); out=[]
    headings=[]
    for i,l in enumerate(lines):
        m=re.match(r"^###\s+(\d+\.\d+)\s+(.+)$",l)
        if m and "IR[" in clean(m.group(2)): headings.append((i,m.group(1),clean(m.group(2))))
    for n,(start,num,title) in enumerate(headings):
        end=headings[n+1][0] if n+1<len(headings) else next((j for j in range(start+1,len(lines)) if lines[j].startswith("## ")),len(lines))
        block=lines[start:end]
        context=normalize_execute_context(prefix, num, title)
        for ts in range(1,5):
            marker=f"TS{ts}:"; idx=next((k for k,x in enumerate(block) if x.strip()==marker),None)
            if idx is None: continue
            u=bullets_after(block,idx); u=[] if any("no μops" in x or "no unconditional" in x for x in u) else u
            next_ts=next((k for k in range(idx+1,len(block)) if re.match(r"^\s*TS[1-4]:",block[k])),len(block))
            cond=[]
            for k in range(idx+1,next_ts):
                if block[k].strip()=="Conditional μops:": cond.extend(conditional_after(block,k))
            out.append(case(f"{prefix}:{num}:ts{ts}",source,start+1,["MS = EXECUTE",*context],ts,u,cond))
    return out


def parse_external_iot_phase_binding(text: str, source: str):
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == "## 7. External IOT Phase Binding"),
        None,
    )
    if start is None:
        return []
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    block = [clean(line).replace("`", "") for line in lines[start:end]]
    clear_binding = "- IO_CLEAR_AC_REQ selects AC_CLEAR during the TS in which the request is asserted."
    skip_binding = "- IO_SKIP_REQ selects PC_INC during TS4."
    if clear_binding not in block or skip_binding not in block:
        return []
    output = []
    for ts in range(1, 5):
        conditional = [
            {"predicate": "IO_CLEAR_AC_REQ = 1", "micro_operation": "AC_CLEAR"}
        ]
        if ts == 4:
            conditional.append(
                {"predicate": "IO_SKIP_REQ = 1", "micro_operation": "PC_INC"}
            )
        output.append(case(
            f"iot:external:ts{ts}", source, start + 1,
            ["MS = EXECUTE", "IOT_ACTIVE = 1"], ts, [], conditional,
        ))
    return output

def parse_interrupt(text,source):
    lines=text.splitlines();out=[]
    for i,l in enumerate(lines):
        m=re.match(r"^###\s+(4\.[1-4])\s+TS([1-4])",l)
        if m:
            out.append(case(f"interrupt:{m.group(1)}",source,i+1,["MS = INTERRUPT"],int(m.group(2)),bullets_after(lines,i)))
    return out


def parse_console(text,source):
    lines=text.splitlines();out=[]
    for i,l in enumerate(lines):
        m=re.match(r"^##\s+(6|7|8|10)\.\s+(.+?)\s+Operation",l)
        if not m: continue
        end=next((j for j in range(i+1,len(lines)) if lines[j].startswith("## ")),len(lines)); block=lines[i:end]
        ctx=[];u=[]
        for k,x in enumerate(block):
            if x.strip()=="Applicable context:": ctx,_=code_after(block,k)
            if x.strip()=="μops:": u=bullets_after(block,k)
        out.append(case(f"console:{m.group(1)}",source,i+1,ctx,None,u,[],"console-transaction"))
    return out


def parse_opr_execution(text, source, group, bits):
    lines = text.splitlines()
    by_ts = {ts: [] for ts in range(1, 5)}
    current_ts = None
    first_line = {}
    for i, line in enumerate(lines):
        heading = re.match(r"^###\s+4\.([2-5])\s+TS([1-4])", line)
        if heading:
            current_ts = int(heading.group(2))
            first_line.setdefault(current_ts, i + 1)
            continue
        timing = re.match(r"^TS([1-4]):", line.strip())
        if timing:
            current_ts = int(timing.group(1))
            first_line.setdefault(current_ts, i + 1)
            continue
        if current_ts is None:
            continue
        cleaned = clean(line.strip())
        conditional = re.match(r"^- if (.+?):\s*([A-Z][A-Z0-9_]*)$", cleaned)
        if conditional:
            predicate = conditional.group(1)
            for name, bit in bits.items():
                predicate = predicate.replace(f"IR[bit({name})]", f"IR[{bit}]")
            predicate = normalize_opr_predicate(predicate, bits, group)
            by_ts[current_ts].append({"predicate": predicate, "micro_operation": conditional.group(2)})

    if group == 2:
        for i, line in enumerate(lines):
            if line.strip() == "Conditional μops:":
                found = conditional_after(lines, i)
                if found:
                    by_ts[1].extend(found)
                    first_line.setdefault(1, i + 1)

    output = []
    for ts in range(1, 5):
        if not by_ts[ts]:
            continue
        output.append(case(
            f"opr{group}:ts{ts}",
            source,
            first_line[ts],
            ["MS = EXECUTE", "IR_IS_OPR = 1", f"{OPR_GROUP_INPUTS[group]} = 1"],
            ts,
            [],
            by_ts[ts],
        ))
    return output


UOP_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def micro_operation_catalog(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^###\s+([A-Z][A-Z0-9_]*)\s*$", clean(line))
        if match:
            names.add(match.group(1))
    return names


def validate_cases(cases: list[dict], known_uops: set[str]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    seen: set[str] = set()
    for item in cases:
        case_id = item["id"]
        source = item["source"]["path"]
        line = item["source"]["line"]
        if case_id in seen:
            diagnostics.append(Diagnostic("ERROR", "DUPLICATE_CASE_ID", f"Duplicate case id {case_id}.", source, line))
        seen.add(case_id)
        if item["execution_model"] == "major-state" and item["timing_state"] not in {1, 2, 3, 4}:
            diagnostics.append(Diagnostic("ERROR", "INVALID_TIMING_STATE", f"Case {case_id} has invalid timing state.", source, line))
        if item["execution_model"] == "console-transaction" and item["timing_state"] is not None:
            diagnostics.append(Diagnostic("ERROR", "CONSOLE_TIMING_STATE", f"Console case {case_id} must not have a timing state.", source, line))
        operations = list(item["micro_operations"]) + [entry["micro_operation"] for entry in item["conditional_micro_operations"]]
        for operation in operations:
            if not UOP_NAME.fullmatch(operation):
                diagnostics.append(Diagnostic("ERROR", "MALFORMED_MICRO_OPERATION", f"Malformed micro-operation {operation!r}.", source, line))
            elif operation not in known_uops:
                diagnostics.append(Diagnostic("ERROR", "UNKNOWN_MICRO_OPERATION", f"Unknown micro-operation {operation}.", source, line))
        for entry in item["conditional_micro_operations"]:
            predicate = entry["predicate"]
            if "bit(" in predicate:
                diagnostics.append(Diagnostic("ERROR", "UNRESOLVED_OPR_BIT", f"Unresolved OPR bit reference in {predicate!r}.", source, line))
            if not predicate.strip():
                diagnostics.append(Diagnostic("ERROR", "EMPTY_PREDICATE", "Conditional micro-operation has an empty predicate.", source, line))
    return diagnostics


def extract(root:Path):
    # Expected repository layout.
    isa=root/"docs/02-isa"; micro=root/"docs/03-microarchitecture"; opr=micro/"07-opr"
    bits={}
    for fname in ISA_DOCS:
        parsed=parse_bit_diagram(read(isa/fname)); bits.update(parsed)
    cases=[]
    cases += parse_fetch_defer(read(micro/"04-fetch-defer.md"),"docs/03-microarchitecture/04-fetch-defer.md")
    cases += parse_numbered_execute(read(micro/"05-mri-execution.md"),"docs/03-microarchitecture/05-mri-execution.md","mri")
    iot_text = read(micro/"06-iot-execution.md")
    cases += parse_external_iot_phase_binding(iot_text,"docs/03-microarchitecture/06-iot-execution.md")
    cases += parse_numbered_execute(iot_text,"docs/03-microarchitecture/06-iot-execution.md","iot")
    cases += parse_interrupt(read(micro/"08-interrupt-execution.md"),"docs/03-microarchitecture/08-interrupt-execution.md")
    cases += parse_console(read(micro/"09-console-execution.md"),"docs/03-microarchitecture/09-console-execution.md")
    cases += parse_opr_execution(read(opr/"01-group1-execution.md"),"docs/03-microarchitecture/07-opr/01-group1-execution.md",1,bits)
    cases += parse_opr_execution(read(opr/"02-group2-execution.md"),"docs/03-microarchitecture/07-opr/02-group2-execution.md",2,bits)
    cases += parse_opr_execution(read(opr/"03-group3-execution.md"),"docs/03-microarchitecture/07-opr/03-group3-execution.md",3,bits)
    known_uops = micro_operation_catalog(read(micro / "02-micro-operations.md"))
    diagnostics = validate_cases(cases, known_uops)
    diagnostics.sort(key=lambda item: (item.severity, item.code, item.source, item.line or -1, item.message))
    return {
        "format_version": 1,
        "control_design_version": "v1",
        "artifact": "execution-definitions",
        "extraction_stage": "documentation-extraction",
        "opr_bit_positions": bits,
        "cases": cases,
        "diagnostics": [asdict(item) for item in diagnostics],
    }


def run(arguments:Sequence[str]|None=None):
    p=argparse.ArgumentParser();p.add_argument("--repo-root",required=True,type=Path);p.add_argument("--json-output",type=Path,default=DEFAULT_OUTPUT);p.add_argument("--report-output",type=Path,default=DEFAULT_REPORT);a=p.parse_args(arguments);root=a.repo_root.resolve()
    try: result=extract(root)
    except ExtractionFailure as e: print(f"ERROR: {e}"); return 1
    out=a.json_output if a.json_output.is_absolute() else root/a.json_output; report=a.report_output if a.report_output.is_absolute() else root/a.report_output
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
    diagnostics = result["diagnostics"]
    report_lines = [
        "Execution-Definition Extraction Report",
        "======================================",
        "",
        f"Cases extracted: {len(result['cases'])}",
        f"Diagnostics: {len(diagnostics)}",
        "",
        "Diagnostic Details",
        "------------------",
    ]
    if diagnostics:
        report_lines.extend(
            f"{item['severity']} {item['code']} {item['source']}:{item.get('line')}: {item['message']}"
            for item in diagnostics
        )
    else:
        report_lines.append("No diagnostics.")
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text("\n".join(report_lines)+"\n",encoding="utf-8",newline="\n")
    failed = any(item["severity"] in {"ERROR", "FATAL"} for item in diagnostics)
    print("Execution-definition extraction");print(f"Status: {'FAILED' if failed else 'SUCCEEDED'}");print(f"Cases: {len(result['cases'])}");print(f"Diagnostics: {len(diagnostics)}");print(f"JSON output: {out}");print(f"Report output: {report}")
    if failed:
        print();print("Failure diagnostics");print("-------------------")
        for item in diagnostics:
            if item["severity"] in {"ERROR", "FATAL"}: print(f"{item['severity']} {item['code']}: {item['message']}")
    return 1 if failed else 0

def main(): raise SystemExit(run())
if __name__=="__main__":main()
