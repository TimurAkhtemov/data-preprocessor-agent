# Small public evaluation fixtures

These fixtures were added after the core MVP worked, to evaluate different analytical tasks. They are not used by the app unless explicitly uploaded. Total original download size: **103,991 bytes** (~102 KiB). Source bytes are retained in `raw/`; upload-ready fixtures live in `prepared/`.

| Dataset | Shape | Purpose | Source and attribution | License |
| --- | --- | --- | --- | --- |
| Iris | 150 × 5 | Complete numeric measurements; overall vs within-species relationships | R. Fisher (1936), [UCI Iris](https://archive.ics.uci.edu/dataset/53/iris), [DOI](https://doi.org/10.24432/C56C76) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Palmer penguins | 344 × 8 | Mixed categorical/numeric data, missing values, group denominators | Data collected by Kristen Gorman and Palmer Station LTER; Horst, Hill & Gorman (2020), [palmerpenguins](https://allisonhorst.github.io/palmerpenguins/), [Gorman et al. 2014](https://doi.org/10.1371/journal.pone.0090081) | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Red wine quality | 1,599 × 12 | Numeric skew/outliers, repeated rows, imbalanced quality groups | Cortez, Cerdeira, Almeida, Matos & Reis (2009), [UCI Wine Quality](https://archive.ics.uci.edu/dataset/186/wine+quality), [DOI](https://doi.org/10.24432/C56S3T) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Preparation is deterministic and limited to file format. Iris receives descriptive headers and its trailing blank line is omitted; original values (including differences UCI documents from Fisher's original paper) remain unchanged. Red wine quality is converted from semicolon to comma delimiter, with unchanged headers/cells. Penguins is copied byte-for-byte from the package's simplified dataset. No cleaning, imputation or anomaly injection is performed.

`sources.json` records original URLs, retrieval date, original byte counts, licenses, attribution, explicit format changes and SHA-256 hashes of both versions. Re-fetch with `backend/.venv/bin/python scripts/fetch_eval_datasets.py` from the repo root. Downloads are explicitly opt-in, capped at 500 KB each, and checked against recorded source hashes on repeat runs. An upstream change requires manual source review.

For publication of new penguin analyses, consult the [data contributors' citation and access guidance](https://allisonhorst.github.io/palmerpenguins/#additional-data-use-information). This repository uses the small public data only for application evaluation and makes no biological research claim.
