# Symbolic Control-Word Generator

Generates predicate-preserving symbolic control words from the five maintained artifacts under `rom/microcode/v1`.

Unlike address analysis, this stage does not enumerate control-input permutations. Each execution case contains canonical defaults plus guarded field assignments with provenance. Conditional micro-operation predicates and direct-control contexts remain symbolic.

```text
python tools/rom-generation/symbolic-control-word-generator/src/generate_symbolic_control_words.py --repo-root .
python -m unittest discover -s tools/rom-generation/symbolic-control-word-generator/tests -p "test_*.py"
```
