# Microdata Ingestion

The "real-sampling" convergence pipeline (`synthbench convergence real`,
`synthbench convergence compare`) needs **individual-level survey
microdata**, not the pre-aggregated `human_distribution` shipped on every
`Question`. This doc explains the per-dataset setup and the on-disk layout
the GSS adapter expects.

## Why microdata

`synthbench convergence bootstrap` draws multinomial samples from a
collapsed aggregate distribution -- the idealized i.i.d. floor. That curve
shows the **theoretical** convergence rate but ignores population
heterogeneity (waves disagree, demographic strata cluster, rare options
have heavier tails than `1/√n` predicts).

Real-sampling convergence sub-samples *actual respondents* without
replacement and measures `JSD(subsample, full_population)`. Plotting both
curves on the same axes is the headline claim: *"synthpanel convergence at
n=Y matches real human sampling convergence at n=Z."*

## Common types

`synthbench.datasets.base` defines:

```python
@dataclass
class MicrodataRow:
    respondent_id: str            # stable within the dataset
    survey_wave: str              # e.g. "GSS:2022"
    responses: dict[str, str]     # question_key -> option_key
    subgroup: dict[str, str]      # optional cell labels (age_band, region, …)
```

Adapters override two methods on `Dataset`:

* `load_microdata(n=None) -> list[MicrodataRow]`
* `load_microdata_for_question(key) -> list[MicrodataRow]`

Adapters that don't ingest microdata raise `MicrodataNotAvailable` from
the base class default. The CLI catches that and emits a clean error.

## Dataset matrix

| Dataset       | License                  | Redistribution     | Status     |
|---------------|--------------------------|--------------------|------------|
| GSS           | NORC public domain       | `full`             | shipped    |
| WVS           | Research-use, attribution required | `gated`  | follow-on  |
| Eurobarometer | GESIS research-use       | `gated`            | follow-on  |
| OpinionsQA    | Pew restrictive          | `aggregates_only`  | not planned |

Per-respondent rows carry strictly more identifying information than
aggregates, so policy is enforced at publish time exactly as for aggregate
artifacts. `gated` datasets route microdata-derived artifacts to the
authenticated R2 origin; `aggregates_only` and `citation_only` suppress
them entirely.

## GSS setup

GSS microdata is publicly downloadable from NORC. The adapter expects a
**long-form CSV** at:

```
~/.synthbench/data/gss/microdata/gss_microdata.csv
```

with columns:

| Column            | Required | Notes                                     |
|-------------------|----------|-------------------------------------------|
| `respondent_id`   | yes      | Stable within a wave                      |
| `year`            | yes      | Survey wave (e.g. `2022`)                 |
| `question_id`     | yes      | Bare upstream id (e.g. `SPKATH`)          |
| `option`          | yes      | Selected option for that respondent       |
| `subgroup_*`      | no       | Sidecar columns -> `MicrodataRow.subgroup` |

One row per `(respondent_id, question_id)` the respondent actually
answered. Skipped questions are simply absent. Subgroup columns are read
from the first row seen for each respondent within a wave.

### Conversion from STATA / SPSS

NORC ships GSS as STATA (`.dta`) or SPSS (`.sav`). Convert to long-form
CSV with whichever stack you prefer:

```bash
# Python (pandas + pyreadstat)
pip install pandas pyreadstat
python -c "
import pandas as pd, pyreadstat
df, _ = pyreadstat.read_dta('GSS7222_R3.dta')
keep = ['id', 'year', 'spkath', 'abany']  # …add the questions you care about
df = df[keep]
long = df.melt(id_vars=['id', 'year'], var_name='question_id', value_name='option')
long = long.rename(columns={'id': 'respondent_id'}).dropna(subset=['option'])
long['question_id'] = long['question_id'].str.upper()
long.to_csv('~/.synthbench/data/gss/microdata/gss_microdata.csv', index=False)
"
```

### Smoke test

```bash
synthbench convergence real \
    --dataset gss --question SPKATH \
    --sample-sizes 50,200,1000 \
    --bootstraps 100 --seed 1 \
    --output /tmp/gss-real.json

synthbench convergence compare \
    --dataset gss --question SPKATH \
    --sample-sizes 50,200,1000 \
    --bootstraps 100 --seed 1 \
    --output /tmp/gss-compare.json
```

The `compare` payload's `delta_jsd_mean` array shows the per-`n` gap
between the bootstrap floor and the real-sampling curve.

## Adapter conventions for follow-on datasets

When extending `wvs.py` and `eurobarometer.py`:

* Store rows under the same canonical `Question.key` form (e.g. `WVS_…`).
  `compute_real_curve(rows, question_key=question.key)` then "just works".
* Mirror the `_microdata_path()` + raise-with-instructions pattern from
  `gss.py::load_microdata` rather than auto-downloading. License terms
  generally require attestation, which is friendlier as a manual step.
* Declare `redistribution_policy = "gated"` and a real `license_url` /
  `citation` on the adapter class. The publish step picks these up via
  `synthbench.datasets.policy.policy_for`.
* Add a per-dataset fixture under `tests/fixtures/microdata/` with ~100
  anonymized respondents and replicate the GSS test layout.
