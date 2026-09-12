# eval_diff.md — model/effort change, before vs after

**A model deprecation is this diff: rerun, compare, accept or hold. The judgment (schema, prompts, tolerances, golden set) is versioned and did not change.**

| | Gemini thinking medium (shipped) | Gemini thinking low | delta |
|---|---|---|---|
| run id | 20260911-220517 | 20260911-222706 | |
| strict catch (field + type) | 9/9 | 8/9 | -1 |
| field-level catch (diagnostic) | 9/9 | 9/9 | +0 |
| false flags on clean fields (lower is better) | 3/218 | 3/218 | +0 |
| cross-family agreement | 225/228 | 224/228 | -1 |
| auto-clear correctness | 9/9 | 9/9 | +0 |
| extraction accuracy gemini | 225/228 | 224/228 | -1 |
| extraction accuracy claude | 228/228 | 228/228 | +0 |
| cost per document (USD) | $0.1142 | $0.0722 | -0.0420 |

## Planted findings whose reported outcome moved

none

## Extraction fields whose correctness moved

none recorded (per-field accuracy is stored from v0.2 runs onward)

n: 12 documents in both runs. Directional, not statistically significant.
