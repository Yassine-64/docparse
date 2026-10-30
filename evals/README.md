# Evals

`run_eval.py` scores `docparse` output against ground-truth markdown placed next to each PDF in a
data directory (`evals/data/` is git-ignored). Metrics: whitespace-normalized edit similarity and
verbatim table-row recall. Next step is wiring public benchmarks (OHR-Bench, OmniDocBench subset)
through the same loop so the README table reports real numbers per engine.
