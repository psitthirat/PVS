# Validation record

The reorganized repository was verified on **30 September 2026** using a newly created **Python 3.13.2 environment on macOS arm64**. The `pvs-thailand` wheel was built from `pyproject.toml`, installed with the locked analysis dependencies, and checked with `pip check`. No broken requirements were reported.

The installed wheel's Python files were compared with `src/pvs/` and matched. Inspection confirmed that the wheel contains no private data, archived notebooks, working outputs, or research release artifacts.

## Full workflow

Private inputs were copied into an isolated workspace, with recoding maps at `data/mappings/` and no pre-existing analysis outputs. The installed package was run from outside the repository, with standard input closed:

```bash
python -m pvs --project-root /path/to/isolated-workspace
```

The tables, figures, report, and chart-data stages all completed successfully. The original survey and dictionary, archived working files, and approved release were not overwritten. Validated regenerated products were then copied into the repository's ignored `output/` directory for continued local use.

| Released artifact | Comparison with regenerated output | Result |
| --- | --- | --- |
| 61 CSV tables | Complete file bytes | All identical |
| Nine PNG figures | Decoded RGBA pixels and dimensions | All identical |
| Final English report | Every DOCX ZIP member, allowing the exact intended provenance-paragraph replacement | All other package contents identical |

The report's provenance paragraph now refers to `src/pvs/`, `output/`, and `results/2026-09/`, replacing references to the previous working-folder layout. No analysis values or other report content changed. The approved `results/2026-09/report.docx` remains unchanged.

The workflow also generated ten chart-data CSV files, their Excel workbook, and the segmentation workbook. These are local working products outside the approved release set.

## Notebook and public checks

The new `notebooks/analysis.ipynb` executed successfully in a Python kernel with its working directory set to `notebooks/`. The default mode displayed approved aggregates without loading private survey data. The public notebook remains free of saved outputs, execution counts, and attachments.

Seven tests passed against the installed wheel. They cover sampling-report configuration, failure before private-data loading when the report is missing, explicit workspace selection from another directory, mapping/output path resolution, missing-response denominators, zero denominators, and missing p-values in multiplicity adjustment.

The release checker verified all **71 approved artifacts**, found no unlisted files, and confirmed the clean notebook state. Git exclusion checks cover the private data, archive, working outputs, packaging artifacts, and virtual environment.

Repeat the public checks with:

```bash
python -m unittest discover -s tests -v
python tools/verify_release.py
```

See the [reproduction guide](reproduction.md) for the complete workflow. Detailed execution logs and comparisons are retained locally in the ignored `output/publication_validation/` directory.

## Release refresh, 1 October 2026

The continuity measure derived from Q20 was corrected. The question was fielded to every respondent
with at least one visit, not only to those with more than one, so the 161 respondents who attended
exactly once were included; 91.9% of them answer "one facility" by arithmetic. The measure now uses
`one_facility_multi`, restricted to more than one visit in twelve months (n = 1,238 in the
four-group cohort). Group ordering and the chi-square result are unchanged; every group falls by two
to five percentage points, and the private-hospital figure moves from 84.1% to 80.0%.

Eight of the 71 release artifacts were regenerated and replaced, and their manifest rows updated
with new sizes, checksums and source paths: four tables, the questionnaire inventory, two figures
and the English report. `tools/verify_release.py` passes against the refreshed manifest. The Thai
report and website were rebuilt from the refreshed release, so the narrative, the tables and
figure 3 now agree; the figure caption and the Thai label for that row were updated to state the
restricted denominator. The remaining 63 artifacts are byte-identical to the September release.

This refresh changes a snapshot that had previously been validated as a frozen set. The September
state is recoverable from version control; the manifest records the current contents.

## Scope

This establishes computational reproduction on the tested platform, not an independent review of the study design or interpretation. Other platforms and Python versions have not been tested. The analysis dependency snapshot pins package versions; it does not include wheel hashes, build tooling, or optional notebook tools.

## Expanded Thai study report and website

The study presentation now includes full-sample findings, broader international comparisons and the private-hospital subgroup. Its public checks verify 223 published foreign/pooled values, 342 national aggregate rows, 14 Thai indicator joins, the corrected Q40 denominators and the full-sample provider partition. All 28 chart PNGs are embedded unchanged in the 21-section, 31-table Thai report. The source reports and all 71 historical release artifacts remain unchanged.

The test suite now has ten passing checks, including three regression checks for Q40 Thai response labels, unknown categories and absent eligible denominators. Fifteen interface checks passed in Google Chrome for dark/light themes, saved and system preferences, mobile widths of 390 and 320 pixels, reading/presentation/exploration modes, keyboard focus, downloads and offline loading. These checks do not establish compatibility with every browser or native Word pagination. See the [website guide](website.md) and [report coverage audit](report-editorial-notes.md).

## Recheck of the corrected October author report

The precommit review checked the author-managed DOCX after the author's manual
corrections and insertion of the credited Thai figures. The report SHA-256 is
`a64ab8f1f51007c0a09866c04935667f59a15ebfb588407d1c18af7369a03727`.
The audit does not modify the DOCX or the respondent frame.

- 471 table checks, including a source match for the historical sampling plan.
- 43 descriptive tests using Pearson without Yates, or fixed-margin Monte Carlo
  Pearson where expected counts are sparse, as stated in the corrected methods.
- 84 result-prose and summary checks, with ordered numeric values traced to
  canonical counts, re-estimated overall models and approved September outputs.
- Overall Tables 7, 8, 10 and 11 were re-estimated. The corrected ORs, CIs and p-values
  match; complete-case N is 1,268, 1,651 or 945 for women-only screening, as printed.
- Nine segmentation output tables were recalculated and matched. September model
  coefficients in this audit are compared with approved CSVs, not re-estimated.
- Of 13 embedded figures, 11 match reviewed PNG files byte for byte. Figure 9
  is a smaller raster checked visually against the current access chart and its
  aggregate CSV; its values and eligibility labels agree. Figure 1 is a conceptual
  framework without survey estimates. These visual findings are tied to the exact
  image hashes in the audit; changed images require another review.
- Q27/Q29/Q31: 12-month recall is based on the researcher's confirmation after
  inspecting the original questionnaire on 1 October 2026, not an inference from
  abbreviated spreadsheet headers. Counts and model estimates are unaffected.

All four required edit locations and both wording suggestions are now resolved.
The coverage-by-area p-value in Table 2 and its prose is 0.18 (Monte Carlo
p=0.179263); the quality-rating proportion is 54.6%; preventive services in the
private-section summary specify the past 12 months; appointment waiting time
and odds-ratio wording have been clarified. All 471 table checks, 43 descriptive
tests and 84 prose/summary checks pass, with no remaining findings.
The private workbook is `output/reports/ตรวจซ้ำก่อนเผยแพร่_ผลการสำรวจ_20261001.xlsx`.
The earlier workbook and unresolved-model notices describe the previous report
version and must not be reapplied to the corrected version.

Background citation years and external population figures have not been newly
recertified against every original publication. The sampling-plan table is
matched to the August report. Word pagination is not certified by numerical or
image-hash checks. The reviewed Thai DOCX is supplied on email request to
`peerasit.sit@mahidol.ac.th`; it is not included in the website or chart ZIP.
The report release record preserves the hash above. When the private DOCX is
available, a changed author report stops the build until a new review and
release-record update. Public clones use the review record without the DOCX.

Before the email-request interface change, the prepared site passed Chrome checks
for its two parts and 13 chapters, presentation navigation and arrow keys, figure
enlargement, PNG and then-enabled DOCX download bytes,
128 chart asset URLs, and mobile light/dark themes without horizontal overflow.
No JavaScript errors were observed. Thirteen unit tests and the public release,
comparison, website and candidate-file checks passed. Text whitespace checks
exclude Matplotlib-generated SVG files, whose path serialization contains trailing
spaces. GitHub Actions deployment has been prepared locally but not run.

## Editorial interface and email report requests

The revised interface passed Chrome checks at 320, 390, 768 and 1,440 pixels in
reading, presentation and exploration modes. The 2,017-point opening highlights
354, 488 or 1,298 responses, matching the verified national aggregates. Chart
tabs have descriptive topics; figures 4–6 load distinct dark and light SVGs while
retaining their original palettes and light PNG checksums. Tests cover keyboard
tabs, presentation navigation, image enlargement, PNG download bytes, reduced
motion, file-open fallback and all 128 chart/data URLs. No JavaScript errors or
outer horizontal overflow were observed.

Report links are email requests to `peerasit.sit@mahidol.ac.th`, with a prepared
subject and message; they do not send email automatically. The former public
DOCX URL returns 404, and neither the site nor chart ZIP includes the report.
The reviewed author DOCX is unchanged. Current browser evidence is retained
locally in `output/design_review_20261001/`.

The mixed-version browser failure was reproduced by loading the old cached
application/CSS against current HTML (`renderStory` accessed a removed element).
Content-hashed entry asset URLs now bypass those stale resources. The local
preview server sends `Cache-Control: no-store` and returns current bytes for
conditional requests. Chrome checks confirmed the corrected page loads all
2,017 opening dots without errors, including the file-open fallback.

## Typography and 16:9 layout review

The interface uses 14–15 px navigation, tabs and chart actions, 16 px primary
buttons, and at least 44 px header hit areas. The header and content share a
desktop alignment. The opening graphic adapts to viewport height so its statistic
and key remain visible at 1,280×720 and 1,366×768. Phone navigation occupies two
rows instead of reducing its text size. Chart expansion now has a visible Thai
label; text inside the exported chart artwork is unchanged.

Chrome checks passed at 12 widths from 320 to 1,920 pixels in all three modes,
including both sides of the phone and tablet breakpoints. All 13 presentation
chapters and their chart tabs retained visible navigation at 1,280×720,
1,366×768 and 1,920×1,080. Long slide text and source notes scroll inside their
panels. Reading mode also reflowed without outer horizontal overflow with the
root text size doubled; this is not a browser zoom certification.

Light/dark screenshots and measurements are retained privately in
`output/layout_review_20261001/`. Interaction checks, asset loading and PNG
download checks still pass, with no JavaScript errors. The reviewed DOCX and
existing Git index hashes are unchanged; no staging, commit or deployment was
performed during this review.
