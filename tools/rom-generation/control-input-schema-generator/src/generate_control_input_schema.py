"""Generate a candidate maintained control-input schema."""
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
DEFAULT_INPUT = Path('build/simulation_outputs/rom-generation/control-input-extractor/control-inputs.json')
DEFAULT_MAINTAINED = Path('rom/microcode/v1/control-input-schema.json')
DEFAULT_CANDIDATE = Path('build/simulation_outputs/rom-generation/control-input-schema-generator/control-input-schema.candidate.json')
DEFAULT_REPORT = Path('build/simulation_outputs/rom-generation/control-input-schema-generator/generation-report.txt')
USES = {'predicate', 'value'}

@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    input_name: str | None = None
    referenced_input: str | None = None
    source_path: str | None = None
    source_line: int | None = None

class GenerationFailure(Exception):
    pass

def D(sev, code, msg, *, name=None, ref=None, source=None):
    return Diagnostic(sev, code, msg, name, ref, source.get('path') if isinstance(source, dict) else None, source.get('line') if isinstance(source, dict) else None)

def resolve_from_repo(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()

def read_json(path: Path, optional=False):
    if optional and (not path.exists()):
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError as e:
        raise GenerationFailure(f'Required input does not exist: {path}') from e
    except UnicodeDecodeError as e:
        raise GenerationFailure(f'Input is not valid UTF-8: {path}') from e
    if optional and (not text.strip()):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise GenerationFailure(f'Input is not valid JSON: {path}: line {e.lineno}, column {e.colno}: {e.msg}') from e
    if not isinstance(data, dict):
        raise GenerationFailure(f'Input must contain a top-level object: {path}')
    return data

def validate_extracted(data):
    ds = []
    if data.get('format_version') != 1:
        ds.append(D('ERROR', 'UNSUPPORTED_FORMAT_VERSION', 'Expected format_version 1.'))
    if data.get('extraction_stage') != 'final-structure-validation':
        ds.append(D('ERROR', 'UNEXPECTED_EXTRACTION_STAGE', "Expected extraction_stage 'final-structure-validation'."))
    if data.get('diagnostics') != []:
        ds.append(D('ERROR', 'EXTRACTOR_DIAGNOSTICS_PRESENT', 'Extractor input contains diagnostics.'))
    signals = data.get('signals')
    if not isinstance(signals, list):
        return ds + [D('ERROR', 'INVALID_SIGNALS', 'signals must be an array.')]
    seen = set()
    for s in signals:
        if not isinstance(s, dict):
            ds.append(D('ERROR', 'INVALID_SIGNAL', 'Signal must be an object.'))
            continue
        n = s.get('name')
        src = s.get('definition_source')
        if not isinstance(n, str) or not n:
            ds.append(D('ERROR', 'INVALID_SIGNAL_NAME', 'Signal name must be non-empty.', source=src))
            continue
        if n in seen:
            ds.append(D('ERROR', 'DUPLICATE_SIGNAL', f'Signal {n!r} appears more than once.', name=n, source=src))
        seen.add(n)
        if s.get('extraction_status') != 'structure-validated':
            ds.append(D('ERROR', 'INVALID_EXTRACTION_STATUS', 'Signal is not structure-validated.', name=n, source=src))
        if not isinstance(s.get('bit_width'), int) or s['bit_width'] <= 0:
            ds.append(D('ERROR', 'INVALID_BIT_WIDTH', 'bit_width must be a positive integer.', name=n, source=src))
        vals = s.get('enumerated_values')
        ranges = s.get('value_ranges')
        if not isinstance(vals, list):
            ds.append(D('ERROR', 'INVALID_ENUMERATED_VALUES', 'enumerated_values must be an array.', name=n, source=src))
            vals = []
        ev = set()
        for v in vals:
            if not isinstance(v, dict) or not isinstance(v.get('value'), str):
                ds.append(D('ERROR', 'INVALID_ENUMERATED_VALUE', 'Enumerated value must be an object with a string value.', name=n, source=src))
                continue
            if v['value'] in ev:
                ds.append(D('ERROR', 'DUPLICATE_ENUMERATED_VALUE', f"Value {v['value']!r} appears more than once.", name=n, source=v.get('source') or src))
            ev.add(v['value'])
        if not isinstance(ranges, list):
            ds.append(D('ERROR', 'INVALID_VALUE_RANGES', 'value_ranges must be an array.', name=n, source=src))
        deps = s.get('dependencies')
        if not isinstance(deps, list):
            ds.append(D('ERROR', 'INVALID_DEPENDENCIES', 'dependencies must be an array.', name=n, source=src))
        if not isinstance(src, dict) or not isinstance(src.get('path'), str) or (not isinstance(src.get('heading'), str)) or (not isinstance(src.get('line'), int)):
            ds.append(D('ERROR', 'INVALID_DEFINITION_SOURCE', 'definition_source is invalid.', name=n))
    return ds

def validate_maintained(data):
    if data is None:
        return ([], {})
    ds = []
    if data.get('specification_type') != 'control-input-schema':
        ds.append(D('ERROR', 'INVALID_SCHEMA_TYPE', 'Expected control-input-schema.'))
    if data.get('schema_version') != 1:
        ds.append(D('ERROR', 'UNSUPPORTED_SCHEMA_VERSION', 'Expected schema_version 1.'))
    if data.get('control_design_version') != 'v1':
        ds.append(D('ERROR', 'CONTROL_DESIGN_VERSION_MISMATCH', 'Expected control_design_version v1.'))
    fields = data.get('fields')
    if not isinstance(fields, list):
        return (ds + [D('ERROR', 'INVALID_FIELDS', 'fields must be an array.')], {})
    idx = {}
    for f in fields:
        if not isinstance(f, dict):
            ds.append(D('ERROR', 'INVALID_FIELD', 'Maintained field must be an object.'))
            continue
        n = f.get('name')
        if not isinstance(n, str) or not n:
            ds.append(D('ERROR', 'INVALID_FIELD_NAME', 'Maintained field name must be non-empty.'))
            continue
        if n in idx:
            ds.append(D('ERROR', 'DUPLICATE_MAINTAINED_FIELD', f'Maintained field {n!r} appears more than once.', name=n))
        idx[n] = f
        uses = f.get('control_uses')
        if not isinstance(uses, list) or any((u not in USES for u in uses)) or len(uses) != len(set(uses)):
            ds.append(D('ERROR', 'INVALID_CONTROL_USES', 'control_uses must contain unique predicate/value entries.', name=n))
    return (ds, idx)

def field_from_signal(s, uses):
    logic = s.get('logic') if isinstance(s.get('logic'), dict) else {}
    derivation = logic.get('derivation') or logic.get('expression') or logic.get('internal_composition')
    return {'name': s['name'], 'category': s.get('category'), 'width': s['bit_width'], 'control_uses': list(uses), 'attributes': s.get('attributes', {}), 'polarity': s.get('polarity'), 'domain': s.get('domain'), 'values': s.get('enumerated_values', []), 'ranges': s.get('value_ranges', []), 'dependencies': s.get('dependencies', []), 'derivation': derivation, 'constraints': s.get('constraints', []), 'consumers': s.get('consumers', []), 'sources': {'index': s.get('index_source'), 'definition': s.get('definition_source')}}

def dd(d):
    r = {'severity': d.severity, 'code': d.code, 'message': d.message}
    for k, v in [('input_name', d.input_name), ('referenced_input', d.referenced_input), ('source_path', d.source_path), ('source_line', d.source_line)]:
        if v is not None:
            r[k] = v
    return r

def build_candidate(extracted, maintained=None):
    ds = validate_extracted(extracted)
    md, idx = validate_maintained(maintained)
    ds += md
    if any((d.severity == 'ERROR' for d in ds)):
        return (None, ds)
    names = {s['name'] for s in extracted['signals']}
    fields = []
    for s in extracted['signals']:
        old = idx.get(s['name'])
        uses = old.get('control_uses', []) if old else []
        if not uses:
            ds.append(D('WARNING', 'CONTROL_USES_UNRESOLVED', 'Input has no reviewed control-use classification.', name=s['name'], source=s.get('definition_source')))
        fields.append(field_from_signal(s, uses))
    for n in idx:
        if n not in names:
            ds.append(D('WARNING', 'STALE_MAINTAINED_FIELD', 'Maintained field is absent from current extraction.', name=n))
    for s in extracted['signals']:
        for dep in s.get('dependencies', []):
            if isinstance(dep, dict) and isinstance(dep.get('name'), str) and (dep['name'] not in names):
                ds.append(D('ERROR', 'UNDEFINED_DEPENDENCY', f"Dependency {dep['name']!r} is undefined.", name=s['name'], ref=dep['name'], source=dep.get('source')))
    c = {'specification_type': 'control-input-schema', 'schema_version': 1, 'control_design_version': 'v1', 'description': 'Logical control-input schema for version 1 CPU control.', 'source': {'specification_type': 'control-input-extractor', 'format_version': extracted['format_version'], 'extraction_stage': extracted['extraction_stage']}, 'fields': fields, 'diagnostics': [dd(d) for d in ds]}
    return (c, ds)

def write_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')

def write_report(ds, path, count, written):
    counts = {x: sum((d.severity == x for d in ds)) for x in ('INFO', 'WARNING', 'ERROR', 'FATAL')}
    lines = ['Control-Input Schema Generation Report', '======================================', '', f'Fields processed: {count}', f"Candidate written: {('yes' if written else 'no')}", f"Information diagnostics: {counts['INFO']}", f"Warnings: {counts['WARNING']}", f"Errors: {counts['ERROR']}", f"Fatal errors: {counts['FATAL']}", '', 'Diagnostics', '-----------']
    lines += [f"{d.severity} {d.code} [{d.input_name or '-'}]: {d.message}" for d in ds] or ['No diagnostics.']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')

def run(arguments=None):
    p = argparse.ArgumentParser()
    p.add_argument('--repo-root', required=True, type=Path)
    p.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    p.add_argument('--maintained-schema', type=Path, default=DEFAULT_MAINTAINED)
    p.add_argument('--candidate-output', type=Path, default=DEFAULT_CANDIDATE)
    p.add_argument('--report-output', type=Path, default=DEFAULT_REPORT)
    a = p.parse_args(arguments)
    root = a.repo_root.resolve()
    ds = []
    count = 0
    written = False
    try:
        extracted = read_json(resolve_from_repo(root, a.input))
        maintained = read_json(resolve_from_repo(root, a.maintained_schema), optional=True)
        count = len(extracted.get('signals', []))
        candidate, ds = build_candidate(extracted, maintained)
        if candidate is not None and (not any((d.severity in {'ERROR', 'FATAL'} for d in ds))):
            write_json(candidate, resolve_from_repo(root, a.candidate_output))
            written = True
    except GenerationFailure as e:
        ds = [D('FATAL', 'GENERATION_FAILURE', str(e))]
    write_report(ds, resolve_from_repo(root, a.report_output), count, written)
    return 1 if any((d.severity in {'ERROR', 'FATAL'} for d in ds)) else 0

def main():
    raise SystemExit(run())
if __name__ == '__main__':
    main()
