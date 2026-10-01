# Reproducing the PVS analysis

The supported entry point is the installed `pvs` package. Both the command line and `notebooks/analysis.ipynb` use its implementation. The original notebook and scripts are retained locally under `archive/legacy/` as historical material.

## Install

From the repository root, create a Python 3.13 environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
python -m pip check
```

`requirements-lock.txt` records the complete analysis dependency snapshot. `requirements.txt` lists direct dependencies and supplies the package metadata in `pyproject.toml`. The validated platform is Python 3.13.2 on macOS arm64; other operating systems have not been tested. Build tooling and optional notebook tools are not part of the analysis dependency snapshot.

For notebook use, also install the optional tools:

```bash
python -m pip install -e '.[notebook]'
python -m ipykernel install --user --name pvs --display-name "Python 3 (PVS)"
```

Open `notebooks/analysis.ipynb` in your notebook editor and select the PVS kernel. Its default mode displays approved aggregate tables and a figure without reading private responses. Set `REPRODUCE = True` only when the private inputs are available. The notebook redirects detailed pipeline output to the ignored `output/notebook_run.log` and never displays the prepared respondent frame.

## Private inputs

Arrange the files described in [the input guide](../data/README.md): survey export, validation dictionary, `data/mappings/`, and the Thai sampling report. The report defaults to `data/reference/thai_report.docx`; `PVS_THAI_REPORT` overrides that path. Do not guess or regenerate missing validation rules and maps.

Use working copies of the inputs. The existing cleaning routine refreshes a generated dictionary sheet, can write error extracts, and can update mappings or request missing values. The validated input set runs without interactive responses.

## Run

```bash
# Complete workflow: tables, figures, report, and chart-ready data
python -m pvs

# Or run individual stages, in this order
python -m pvs tables
python -m pvs figures
python -m pvs report
python -m pvs figure-data
```

The tables stage includes the segmentation tables and workbook. `python -m pvs segments` regenerates only that component from an existing prepared frame. The installed `pvs` command is equivalent to `python -m pvs`.

Outputs are written to `output/tables/`, `output/figures/`, `output/figure_data/`, and working report/model files under `output/`. These commands overwrite their working products. `analysis_frame.pkl` contains respondent-level data and stays local. Approved release files under `results/2026-09/` are not overwritten.

## Run from another directory

Paths are shared through `pvs.paths`. The package finds this repository from the current directory or its parent directories, or from an editable installation. For another workspace, choose it explicitly:

```bash
python -m pvs --project-root /path/to/workspace
```

That workspace must contain `data/`; the workflow creates `output/` there. `--project-root` takes precedence over `PVS_PROJECT_ROOT`. For Python API use, set `PVS_PROJECT_ROOT` before importing any `pvs` analysis module and restart a notebook kernel if changing it. `PVS_THAI_REPORT`, when set, still overrides the report location.

## Code map

| Module under `src/pvs/` | Role |
| --- | --- |
| `__main__.py`, `pipeline.py` | CLI and stage orchestration |
| `paths.py` | Shared input and output paths |
| `cleaning.py`, `preparation.py` | Cleaning, derived variables, and analytic cohorts |
| `audit.py` | Classification, health coding, and denominator audits |
| `sampling.py` | Planned allocation and achieved sample |
| `inventory.py` | Transcribed questionnaire and framework coverage |
| `analysis.py` | Statistical models and inference |
| `tables.py` | Analysis tables and segmentation orchestration |
| `segments.py` | Private-hospital-user segmentation and workbook |
| `figures.py`, `figure_data.py` | Figures and chart-ready data from tables |
| `report.py` | English report assembled from analysis outputs |

Website modules (`story*.py`, `report_figures.py`, `publication.py`, `web_assets.py`, `national.py`, `report_models.py`) are described in the [website guide](website.md).

## Public checks

```bash
python -m unittest discover -s tests -v
python tools/verify_release.py
```

Tests use synthetic examples and temporary workspaces. The release checker uses only the Python standard library, verifies artifact checksums, rejects unlisted release files, and checks that public notebooks have no saved outputs, execution counts, or attachments. Clear notebook outputs before committing.

## Release and validation

The approved September release remains unchanged. Its manifest records source paths as they were when the release was copied; the original working products now live in `archive/legacy/output/revision_2026-09/`.

The regenerated report uses the new repository paths in its provenance paragraph. That editorial change does not replace the approved report. See the [validation record](validation.md) for the comparison and its limits.

## October report recheck and definition clarification

`python tools/audit_current_report.py` is a read-only check of the corrected
October author-managed DOCX. It writes a new private workbook and aggregate
review evidence under `output/precommit_review_20261001/`. It re-estimates the
four overall model tables with their original exact-age complete-case cohorts;
these are model-based logistic models, separate from the September four-provider
models with cluster-adjusted covariance. It checks the latter against approved
CSV estimates and reruns the segmentation analyses.

The researcher confirmed 12-month recall for Q27, Q29 and Q31 from the original
questionnaire. The canonical numeric frame and released estimates are unchanged;
current inventory/working-report wording reflects that clarification. Historical
September artifacts remain frozen and are accompanied by an explicit erratum.
The earlier byte/pixel reproduction record applies to the pre-clarification code
and must not be interpreted as a promise that newly corrected wording matches it.
