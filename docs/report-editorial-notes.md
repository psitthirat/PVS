# Study report: coverage audit and reproducibility

The report is titled **ผลการศึกษา** and reads from the national survey findings
and international context into the detailed provider comparison. Its public
prose does not describe the document-production process as the research result.
The original Thai and both English documents are preserved.

## Sources inspected in full

- `output/reports/ผลการสำรวจ_20260801.docx`: 150 paragraphs, 12 tables and four
  embedded images. Every results table and the national/international discussion
  were checked for coverage.
- `output/reports/Report - Customers of private hospitals in the Thai health system.docx`:
  159 paragraphs, 14 tables and seven images. Its substantive paragraphs match
  the approved English report; the difference is a provenance paragraph about
  repository paths. This user-named document was inspected directly.
- `results/2026-09/report.docx` and the corresponding 61 aggregate CSVs provide
  the audited subgroup definitions and models.
- Public foreign-country dictionaries were recovered from the original analysis
  notebook and independently checked against the primary articles. The national
  results use the canonical prepared frame rather than old plotted Thai values.

## Coverage audit of the original Thai report

| Original material | Treatment in the study report |
| --- | --- |
| PVS purpose, population perspective, foundations/processes/outcomes | Background explains population experience, usual source, last encounter and system confidence as distinct constructs. |
| Sampling plan and Table 1 | Methods, full regional allocation table, sample map and planned/achieved figure retained; quota convenience selection and unweighted interpretation made explicit. |
| Table 2: demographics, education, income and schemes by area | Full national and municipal/non-municipal table restored, with age bands, six education levels, all sex categories, explicit unknown coverage and supplementary insurance. |
| Table 3: health and activation | Separate national section, area comparisons, corrected good-or-better health, mental health, chronic condition and both activation definitions. |
| Table 4: utilisation and prevention | Separate national use and prevention sections, area-specific counts and charts, admission, unmet need, vision/oral-health differences, and women-only screening denominators. |
| Table 5: usual source, sector and setting | Full-sample coverage and area differences restored; complete six-category distribution includes no usual source and other/unclassifiable providers. Hospital OPD/ER is not called secondary care without evidence. |
| Table 6: profiles by provider | Current four-group analysis retains the question and separates private hospitals from clinics/pharmacies instead of treating the private sector as a single group. |
| Table 7: factors associated with perceived own-provider quality | The question is addressed using current provider-group models and the existing adjusted activation association (aOR 1.86, 95% CI 1.32–2.62). Old coefficients based on incorrect health coding and age denominators are not reused. No new all-covariate national model was fitted. |
| Table 8: usual source and prevention | The comparison itself is fully restored for all eight services using 1,529 with versus 488 without a usual source, and sex-specific denominators. These are current descriptive associations, explicitly not a re-estimation of the old adjusted model. |
| Table 9: confidence by public/private usual source | Pooled public/private descriptive comparison restored, separately from the later private-hospital analysis. |
| Table 10: having a usual source and confidence | Current descriptive comparison restored for all three confidence indicators and system improvement/endorsement. Superseded adjusted coefficients are not treated as current evidence. |
| Table 11: sector and confidence | Current pooled sector contrast and later adjusted four-group models retained as different questions. The old model is not copied. |
| Table 12: system quality and services | Full national, area and pooled sector results restored, including all four Q40 primary-care quality items with valid-response denominators. |
| International unmet need | All 14 country/area estimates plus published pooled total restored; Thai and foreign 12-month recall is explicit, following the researcher's original-questionnaire confirmation on 1 October 2026. |
| International confidence and system opinion | All 15 country/area estimates plus published aggregate restored for quality confidence, affordability confidence, health security, trajectory, endorsement, listening and COVID-19 management. |
| International system/primary-care quality | Public/private system ratings plus maternal, child, chronic and mental-health service ratings restored across countries. |
| Policy interpretation and limitations | National access, continuity, financing confidence and governance precede the private-hospital regulatory discussion; causal and clinical limits remain explicit. |

The first assembled draft overemphasised the subgroup analysis, compressed the
national material and limited international context to Thailand/India. The
current report restores those missing questions and comparisons. It contains
21 substantive sections, an executive summary, 31 tables and 28 shared figures.

## National aggregate snapshot and Q40 correction

`content/national/national_summary.csv` contains 342 aggregate rows, with columns:

```text
domain,measure_id,label,group_id,group_label,n,N,excluded,pct,ci_low,ci_high
```

The groups are all respondents, municipal, non-municipal, usual source,
no usual source, public usual source and private usual source. Definitions are
in `content/national/metadata.json`. These are descriptive, unweighted results.
Wilson intervals do not correct convenience-selection bias or provide full
survey-design inference.

The frozen September Q40 exports expected numeric prefixes even though four
cleaned Q40 fields already contain Thai ordinal labels. The study-report
aggregate helper maps the exact labels `แย่`, `พอใช้`, `ดี`, `ดีมาก`, `ดีเยี่ยม` to
0–4 and defines high quality as the final two categories. It excludes
`ไม่สามารถประเมินได้` and missing values; unknown labels raise an error.
The old approved outputs are not edited.

| Q40 item | High rating | Valid denominator | Cannot evaluate | Percent |
| --- | ---: | ---: | ---: | ---: |
| Maternal | 458 | 1,650 | 367 | 27.8 |
| Child | 426 | 1,702 | 315 | 25.0 |
| Chronic care | 516 | 1,787 | 230 | 28.9 |
| Mental-health care | 350 | 1,648 | 369 | 21.2 |

With the trusted local prepared frame, regenerate this aggregate snapshot using:

```bash
python -m pvs.national --frame output/analysis_frame.pkl --out content/national
```

This reads the prepared frame without cleaning raw data, rewriting a dictionary
or changing the survey. The public report/story build reads the aggregate
snapshot and requires no private inputs. The synthetic regression checks in
`tests/test_national.py` verify all five ratings, structural exclusion, missing
values, unknown-label rejection and an all-inapplicable denominator.

## Definition and inference safeguards

- Good-or-better physical health is 78.8%; very-good/excellent is a separate
  32.1% definition. Mental health is 1,788/2,017 (88.6%).
- Q27 preventive receipt, Q29 unmet need and Q31 financial hardship refer to the past 12 months. The
  researcher confirmed this from the original questionnaire on 1 October 2026;
  shortened export headers had omitted the recall period. Q28 medical-error
  and discrimination items remain ever-experienced reports.
- Breast/cervical results use women-only denominators; no age/risk/interval
  eligibility is inferred. Full-sample values are 446/1,091 (40.9%) and
  463/1,091 (42.4%).
- Social Security in the regular private-hospital group is 88/126 (69.8%) among
  those reporting a scheme, or 88/127 (69.3%) over the entire group.
- Concordance is matching provider sector/setting, not the same named facility.
- Nine of 11 experience contrasts are higher for private-hospital users versus
  public-hospital users after the reported multiplicity adjustment. Neither
  perceived knowledge/skill nor equipment readiness establishes a difference.
- Admission does not identify the admitting hospital; coverage ownership does
  not identify actual payment, registration or employment.
- The national usual/no-usual and pooled-sector comparisons are descriptive.
  Existing adjusted four-group models answer different questions and are not
  presented as a new national causal analysis.

## International provenance

`content/international/values.csv` contains 223 foreign-country/aggregate rows:
13 metrics for 15 countries/areas plus their published aggregate, and unmet need
for 14 countries/areas plus its pooled total. Argentina means Mendoza Province
only. Thai values are joined from the current national snapshot.

The Kruk confidence/quality results use the article's weighted estimates.
Croke unmet-need percentages are retained as published in Table 1 and match its
counts and denominators. The 14.2% total is 3,296/23,230, not a 15-country
average. Neither aggregate is recomputed or combined with Thailand. Full source
locators, verification and attribution are in `content/international/sources.json`.

## Report production

The Thai report draft was first assembled by a generator that reused the exact
downloadable website PNGs, with titles and explanations outside the images. That
generator (`pvs.thai_report` and `content/report_th.json`) is superseded by the
author-managed October report and is no longer part of this repository. The
current site has no report download; readers request the reviewed report from
`peerasit.sit@mahidol.ac.th`. No unsupported fieldwork dates, ethics approval
numbers, response rates or completed instrument-validation results were invented.

## October author corrections

The four overall model tables were subsequently re-estimated using corrected
physical-health coding and women-only breast/cervical models. All printed
coefficients, intervals, p-values and complete-case sample sizes in the corrected
October report match. Earlier statements in this editorial history about
unreproduced national models are superseded by the [current validation record](validation.md).
The website continues to distinguish national descriptive findings from adjusted
four-provider comparisons; the two model specifications are not interchangeable.
