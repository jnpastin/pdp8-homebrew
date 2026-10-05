from __future__ import annotations
import importlib.util, json, sys, tempfile, unittest
from pathlib import Path
P = Path(__file__).resolve().parents[1] / 'src' / 'generate_control_input_schema.py'
S = importlib.util.spec_from_file_location('generate_control_input_schema', P)
g = importlib.util.module_from_spec(S)
sys.modules[S.name] = g
S.loader.exec_module(g)

def signal(name='A', deps=None):
    return {'name': name, 'attributes': {'display_name': name, 'purpose': 'test'}, 'bit_width': 1, 'category': 'Test', 'constraints': [], 'consumers': [], 'definition_source': {'heading': name, 'line': 2, 'path': 'docs/in.md'}, 'dependencies': deps or [], 'domain': 'Test', 'enumerated_values': [{'value': '0', 'meaning': 'off', 'source': {'path': 'docs/in.md', 'line': 3}}, {'value': '1', 'meaning': 'on', 'source': {'path': 'docs/in.md', 'line': 4}}], 'extraction_status': 'structure-validated', 'index_source': {'path': 'docs/index.md', 'line': 1}, 'logic': {}, 'polarity': {'source': 'defaulted', 'value': 'active-high'}, 'value_ranges': []}

def extracted(items=None):
    return {'diagnostics': [], 'extraction_stage': 'final-structure-validation', 'format_version': 1, 'signals': items or [signal()], 'sources': ['docs/in.md']}

def maintained(fields=None):
    return {'specification_type': 'control-input-schema', 'schema_version': 1, 'control_design_version': 'v1', 'fields': fields or []}

def mf(name='A', uses=None):
    return {'name': name, 'control_uses': uses if uses is not None else ['predicate']}

class Tests(unittest.TestCase):

    def test_relative_path(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(g.resolve_from_repo(Path(t), Path('x')), (Path(t) / 'x').resolve())

    def test_absolute_path(self):
        with tempfile.TemporaryDirectory() as t:
            p = (Path(t) / 'x').resolve()
            self.assertEqual(g.resolve_from_repo(Path.cwd(), p), p)

    def test_missing_required(self):
        with self.assertRaises(g.GenerationFailure):
            g.read_json(Path('/missing'))

    def test_missing_optional(self):
        self.assertIsNone(g.read_json(Path('/missing'), optional=True))

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'x'
            p.write_text('{')
            with self.assertRaises(g.GenerationFailure):
                g.read_json(p)

    def test_valid_extracted(self):
        self.assertEqual(g.validate_extracted(extracted()), [])

    def test_wrong_version(self):
        x = extracted()
        x['format_version'] = 2
        self.assertIn('UNSUPPORTED_FORMAT_VERSION', [d.code for d in g.validate_extracted(x)])

    def test_duplicate_signal(self):
        self.assertIn('DUPLICATE_SIGNAL', [d.code for d in g.validate_extracted(extracted([signal(), signal()]))])

    def test_invalid_width(self):
        s = signal()
        s['bit_width'] = 0
        self.assertIn('INVALID_BIT_WIDTH', [d.code for d in g.validate_extracted(extracted([s]))])

    def test_duplicate_value(self):
        s = signal()
        s['enumerated_values'].append(s['enumerated_values'][0])
        self.assertIn('DUPLICATE_ENUMERATED_VALUE', [d.code for d in g.validate_extracted(extracted([s]))])

    def test_preserves_classification(self):
        c, d = g.build_candidate(extracted(), maintained([mf(uses=['predicate', 'value'])]))
        self.assertEqual(c['fields'][0]['control_uses'], ['predicate', 'value'])
        self.assertEqual(d, [])

    def test_unresolved_new(self):
        c, d = g.build_candidate(extracted(), None)
        self.assertEqual(c['fields'][0]['control_uses'], [])
        self.assertIn('CONTROL_USES_UNRESOLVED', [x.code for x in d])

    def test_stale(self):
        _, d = g.build_candidate(extracted(), maintained([mf('OLD')]))
        self.assertIn('STALE_MAINTAINED_FIELD', [x.code for x in d])

    def test_bad_use(self):
        self.assertIn('INVALID_CONTROL_USES', [d.code for d in g.validate_maintained(maintained([mf(uses=['bad'])]))[0]])

    def test_order(self):
        c, _ = g.build_candidate(extracted([signal('B'), signal('A')]), None)
        self.assertEqual([f['name'] for f in c['fields']], ['B', 'A'])

    def test_source_refresh(self):
        c, _ = g.build_candidate(extracted(), maintained([mf()]))
        self.assertEqual(c['fields'][0]['sources']['definition']['path'], 'docs/in.md')

    def test_undefined_dependency(self):
        _, d = g.build_candidate(extracted([signal('A', [{'name': 'B', 'source': {'path': 'docs/in.md', 'line': 5}}])]), None)
        self.assertIn('UNDEFINED_DEPENDENCY', [x.code for x in d])

    def test_deterministic(self):
        c, _ = g.build_candidate(extracted(), None)
        with tempfile.TemporaryDirectory() as t:
            a = Path(t) / 'a'
            b = Path(t) / 'b'
            g.write_json(c, a)
            g.write_json(c, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_complete_run(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / 'in.json').write_text(json.dumps(extracted()))
            status = g.run(['--repo-root', str(r), '--input', 'in.json', '--candidate-output', 'out.json', '--report-output', 'report.txt'])
            self.assertEqual(status, 0)
            self.assertTrue((r / 'out.json').exists())
            self.assertIn('Warnings: 1', (r / 'report.txt').read_text())
if __name__ == '__main__':
    unittest.main()
