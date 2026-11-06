import importlib.util,pathlib,sys,unittest
P=pathlib.Path(__file__).parents[1]/"src/generate_symbolic_control_words.py";S=importlib.util.spec_from_file_location("g",P);g=importlib.util.module_from_spec(S);sys.modules["g"]=g;S.loader.exec_module(g)
def vals():return [{"encoding":"0","meaning":"OFF"},{"encoding":"1","meaning":"ON"}]
def data():return {"inputs":{"fields":[{"name":"A"},{"name":"V"}],"constraints":[]},"words":{"control_design_version":"v1","fields":[{"name":"F","width":1,"control_word_role":"encoded","default_value":"0","values":vals()},{"name":"D","width":2,"control_word_role":"encoded","default_value":"0","values":[]}]},"mappings":{"mappings":[{"micro_operation":"U","assignments":[{"field":"F","value":"1"}]},{"micro_operation":"Z","assignments":[{"field":"D","value":"01"}]}]},"execution":{"cases":[{"id":"c","source":{},"context":["A = 0"],"timing_state":1,"micro_operations":[],"conditional_micro_operations":[]}]},"direct":{"definitions":[]},"timing":{"constraints":[]}}
class Tests(unittest.TestCase):
 def test_parser(self):self.assertEqual(g.canonical(g.parse("A = 1 AND (B != 2 OR NOT (U is selected))")),"(A = 1 AND (B != 2 OR NOT (U is selected)))")
 def test_malformed(self):
  with self.assertRaises(g.Failure):g.parse("A =")
 def test_defaults_complete(self):a,d=g.generate(data());self.assertFalse(d);self.assertEqual(a["cases"][0]["defaults"],{"F":"0","D":"00"})
 def test_unconditional_uop(self):x=data();x["execution"]["cases"][0]["micro_operations"]=["U"];a,d=g.generate(x);self.assertEqual(a["cases"][0]["field_assignments"]["F"][0]["value"],"1")
 def test_conditional_uop_preserved(self):x=data();x["execution"]["cases"][0]["conditional_micro_operations"]=[{"predicate":"A = 1","micro_operation":"U"}];a,d=g.generate(x);self.assertIn("A = 1",a["cases"][0]["selected_micro_operations"]["U"])
 def test_multiple_uops(self):x=data();x["execution"]["cases"][0]["micro_operations"]=["U","Z"];a,d=g.generate(x);self.assertFalse(d);self.assertTrue(a)
 def test_direct_preserved(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 0"],"direct_assignments":["F = ON"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertEqual(a["cases"][0]["field_assignments"]["F"][0]["origin"],"direct-control definition")
 def test_context_blocks_or(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 0","A = 1"],"direct_assignments":["F = 1"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertIn("OR",a["cases"][0]["field_assignments"]["F"][0]["when"])
 def test_selected_substitution(self):x=data();x["execution"]["cases"][0]["conditional_micro_operations"]=[{"predicate":"A = 0","micro_operation":"U"}];x["direct"]["definitions"]=[{"id":"d","applicable_context":["U is selected"],"direct_assignments":["D = 1"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertNotIn("is selected",a["cases"][0]["field_assignments"]["D"][0]["when"])
 def test_control_supplied_input(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 0"],"direct_assignments":[],"control_supplied_values":["D = V"]}];a,d=g.generate(x);self.assertEqual(a["cases"][0]["field_assignments"]["D"][0]["value_from_input"],"V")
 def test_unknown_context_field(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["BAD = 0"],"direct_assignments":[],"control_supplied_values":[]}];self.assertEqual(g.generate(x)[1][0]["code"],"INVALID_DIRECT_CONTROL")
 def test_unknown_selected_uop(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["BAD is selected"],"direct_assignments":[],"control_supplied_values":[]}];self.assertTrue(g.generate(x)[1])
 def test_unknown_assignment_field(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 0"],"direct_assignments":["BAD = 1"],"control_supplied_values":[]}];self.assertTrue(g.generate(x)[1])
 def test_unknown_encoding(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 0"],"direct_assignments":["F = MAYBE"],"control_supplied_values":[]}];self.assertTrue(g.generate(x)[1])
 def test_overlapping_conflict(self):
  x=data();x["mappings"]["mappings"].append({"micro_operation":"X","assignments":[{"field":"F","value":"0"}]});x["execution"]["cases"][0]["micro_operations"]=["U","X"];self.assertTrue(g.generate(x)[1])
 def test_disjoint_assignments_do_not_conflict(self):
  x=data();x["execution"]["cases"][0]["conditional_micro_operations"]=[{"predicate":"A = 0","micro_operation":"U"}];x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 1"],"direct_assignments":["F = 0"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertFalse(d)
 def test_mutually_exclusive_input_constraints_prevent_false_conflict(self):
  x=data();x["inputs"]["fields"] += [{"name":"R","constraints":[{"text":"Mutually exclusive with W."}]},{"name":"W","constraints":[{"text":"Mutually exclusive with R."}]}];x["direct"]["definitions"]=[{"id":"read","applicable_context":["R = 1"],"direct_assignments":["F = 0"],"control_supplied_values":[]},{"id":"write","applicable_context":["W = 1"],"direct_assignments":["F = 1"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertFalse(d);self.assertIsNotNone(a)
 def test_global_exactly_one_constraint_prevents_false_conflict(self):
  x=data();x["inputs"]["fields"] += [{"name":"IR_IS_MRI"},{"name":"IR_IS_IOT"}];x["inputs"]["constraints"]=[{"kind":"exactly_one","inputs":["IR_IS_MRI","IR_IS_IOT"]}];x["execution"]["cases"][0]["context"]=["IR_IS_MRI = 1"];x["direct"]["definitions"]=[{"id":"d","applicable_context":["IR_IS_IOT = 1"],"direct_assignments":["F = 1"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertFalse(d);self.assertEqual(a["cases"][0]["applicable_direct_control_definitions"],[])
 def test_global_at_most_one_constraint_prevents_false_conflict(self):
  pairs=g.mutually_exclusive_pairs([], [{"kind":"at_most_one","inputs":["G1","G2","G3"]}]);self.assertIn(frozenset(("G1","G3")),pairs);self.assertEqual(len(pairs),3)
 def test_unknown_global_constraint_kind_is_ignored(self):
  self.assertEqual(g.mutually_exclusive_pairs([], [{"kind":"other","inputs":["A","B"]}]),set())

 def test_unconstrained_inputs_still_conflict(self):
  x=data();x["inputs"]["fields"] += [{"name":"R"},{"name":"W"}];x["direct"]["definitions"]=[{"id":"read","applicable_context":["R = 1"],"direct_assignments":["F = 0"],"control_supplied_values":[]},{"id":"write","applicable_context":["W = 1"],"direct_assignments":["F = 1"],"control_supplied_values":[]}];self.assertTrue(g.generate(x)[1])
 def test_deterministic(self):self.assertEqual(g.generate(data()),g.generate(data()))
 def test_no_input_enumeration(self):x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["A = 0 AND V != 0"],"direct_assignments":["F = 1"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertEqual(len(a["cases"]),1)
 def test_symbolic_validation_accepts_generated_artifact(self):
  x=data();a,d=g.generate(x);self.assertFalse(d);self.assertEqual(g.validate_symbolic_artifact(a,x),[])
 def test_symbolic_validation_detects_incomplete_defaults(self):
  x=data();a,d=g.generate(x);del a["cases"][0]["defaults"]["F"];codes={e["code"] for e in g.validate_symbolic_artifact(a,x)};self.assertIn("INCOMPLETE_FIELD_COVERAGE",codes)
 def test_symbolic_validation_detects_case_coverage(self):
  x=data();a,d=g.generate(x);a["cases"]=[];codes={e["code"] for e in g.validate_symbolic_artifact(a,x)};self.assertIn("EXECUTION_CASE_COVERAGE",codes)

 def test_unselected_micro_operation_substitutes_false(self):
  expr=g.parse("U is selected")
  self.assertEqual(g.substitute_selected(expr,{}),("const",False))
  self.assertFalse(g.evaluate(g.substitute_selected(expr,{}),{}))
 def test_unselected_micro_operation_not_selected_substitutes_true(self):
  expr=g.parse("U is not selected")
  self.assertEqual(g.substitute_selected(expr,{}),("const",True))
  self.assertTrue(g.evaluate(g.substitute_selected(expr,{}),{}))
 def test_unselected_direct_definition_is_filtered(self):
  x=data();x["direct"]["definitions"]=[{"id":"d","applicable_context":["U is selected"],"direct_assignments":["F = 1"],"control_supplied_values":[]}];a,d=g.generate(x);self.assertFalse(d);self.assertNotIn("d",a["cases"][0]["applicable_direct_control_definitions"]);self.assertEqual(a["cases"][0]["field_assignments"]["F"],[])

 def test_timing_constraint_removes_only_illegal_overlap(self):
  x=data();x["inputs"]["fields"] += [{"name":"R"},{"name":"C"}];x["execution"]["cases"][0]["timing_state"]=4;x["execution"]["cases"][0]["conditional_micro_operations"]=[{"predicate":"R = 1","micro_operation":"U"}];x["direct"]["definitions"]=[{"id":"d","applicable_context":["C = 1"],"direct_assignments":["F = 0"],"control_supplied_values":[]}];x["timing"]["constraints"]=[{"id":"t","context":"TS = 4 AND (R = 1)","requirement":"C != 1"}];a,d=g.generate(x);self.assertFalse(d);self.assertIsNotNone(a)
 def test_nonmatching_timing_constraint_does_not_hide_conflict(self):
  x=data();x["inputs"]["fields"] += [{"name":"R"},{"name":"C"}];x["execution"]["cases"][0]["timing_state"]=4;x["execution"]["cases"][0]["conditional_micro_operations"]=[{"predicate":"R = 1","micro_operation":"U"}];x["direct"]["definitions"]=[{"id":"d","applicable_context":["C = 1"],"direct_assignments":["F = 0"],"control_supplied_values":[]}];x["timing"]["constraints"]=[{"id":"t","context":"TS = 3 AND (R = 1)","requirement":"C != 1"}];self.assertTrue(g.generate(x)[1])
 def test_timing_constraint_keeps_legal_overlap(self):
  x=data();x["inputs"]["fields"] += [{"name":"R"},{"name":"C"},{"name":"Q"}];x["execution"]["cases"][0]["timing_state"]=4;x["execution"]["cases"][0]["conditional_micro_operations"]=[{"predicate":"R = 1","micro_operation":"U"}];x["direct"]["definitions"]=[{"id":"d","applicable_context":["C = 1"],"direct_assignments":["F = 0"],"control_supplied_values":[]}];x["timing"]["constraints"]=[{"id":"t","context":"TS = 4 AND (Q = 1)","requirement":"C != 1"}];self.assertTrue(g.generate(x)[1])
 def test_timing_constraint_parser_uses_boolean_grammar(self):
  x=data();x["timing"]["constraints"]=[{"id":"t","context":"TS = 4 AND (A = 0 OR V = 1)","requirement":"A != 1"}];rules=g.timing_violations(x);self.assertEqual(len(rules),1);self.assertEqual(rules[0][0],"t")

if __name__=="__main__":unittest.main()
