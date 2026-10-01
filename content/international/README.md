# International PVS reference values

`values.csv` contains **223 published aggregate values across 14 indicators**,
recovered from the plotting code for the original Thai report and verified
against the primary publications. It contains no respondent records and no
Thai estimates. Thai estimates are joined separately from the audited current
`content/national/national_summary.csv`, selecting `group_id == "all"`.
`thai-indicator-join.json` defines that join.

| File | Use |
| --- | --- |
| `values.csv` | One row per metric and country/region; `value_percent` is the published percentage |
| `metrics.json` | Thai labels, source figure/table, recall period and comparison notes |
| `sources.json` | Citations, source URLs, source hashes and verification method |
| `spatial-scope.json` | Geographic interpretation and the public-domain Mendoza locator |
| `unmet-need-table1.json` | Primary unmet-need values with reported numerator and sample N |
| `thai-indicator-join.json` | Crosswalk to corrected Thai aggregate indicator IDs |

The thirteen confidence, endorsement and quality metrics come from Figures 2
and 3 of [Kruk et al. (2024)](https://doi.org/10.1016/S2214-109X(23)00499-0).
Each contains 15 country/region estimates and the published `Total`.
The unmet-need metric comes from Table 1 of
[Croke et al. (2024)](https://doi.org/10.1016/S2214-109X(23)00513-2):
14 country/region estimates and its `Total`; Greece is absent. Every
unmet-need percentage was checked programmatically against the primary article
XML; every Kruk figure value was checked visually against its printed label.
Values were not estimated from chart dimensions or map colours.

The local recovery source was `archive/legacy/main.ipynb`, cells 17, 27 and 30
(zero-based indices). Only literal dictionaries containing published aggregate
statistics were parsed. The notebook was not executed and its private outputs
were not copied. Old Thai values and comments are superseded by the current
analysis. In particular, the old notebook contains a stale comment about the
government-responsiveness item; use the audited Thai `listens` indicator.

## Required interpretation

- **Argentina means Mendoza Province only.** Keep the Argentina polygon grey
  and show a labelled point at the public-domain Mendoza locator. The point is
  a provincial-capital location marker, not a survey location or a city-level
  estimate. Do not shade all Argentina as if its sample were national.
- **Thai values describe the unweighted sample in 13 selected provinces.**
  Show them with a distinct marker or hatch and retain that qualification.
  Statistical adjustment does not convert the sample into a national sample.
- **Unmet need refers to the past 12 months in both sources.** On 1 October
  2026 the researcher checked the original questionnaire and confirmed this
  period for Thai Q27/Q29. Abbreviated export headers had omitted it; see
  `content/questionnaire/recall-confirmation.json`. Sampling, weighting and
  fieldwork dates still differ, so these are descriptive comparisons, not rankings.
- **The unmet-need Total is 3,296/23,230 = 14.2% from 14 countries.** It is
  neither a 15-country average nor an arithmetic mean of country percentages.
  Never include Thailand when reproducing this published aggregate.
- Kruk's reported country estimates use sampling/post-stratification weights
  as applicable. Croke Table 1 gives descriptive n (%) and the unmet values
  agree with those displayed counts and sample Ns. Preserve the specific
  source series rather than mixing in nearby weighted estimates from another
  PVS paper, which differ by several tenths of a percentage point.
- Both studies include adults aged 18+; fieldwork period, interview mode,
  sampling, weighting and language differ from the Thai survey. Ratings reflect
  reported confidence or perceived quality, not measured clinical outcomes.
- Q40 Thai quality items use valid-answer denominators, excluding responses
  that cannot assess quality. Their restored numerators/denominators must be
  retained in the report. Published foreign figure labels do not supply
  item-specific denominators or confidence intervals; equal denominators
  across sources must not be assumed.
- `TOTAL` is a non-geographic benchmark and must not be mapped. Grey countries
  mean no value for the selected metric, not zero. The countries surveyed do not
  represent the entire world.

## Source rights

The dataset redistributes attributed numerical facts and newly written labels,
not source article text or figure artwork. Kruk's article is CC BY 4.0.
Croke's PMC record contains conflicting license statements (the main copyright
statement says CC BY 4.0, while the license section says CC BY-NC-ND 4.0);
`sources.json` records this without claiming its article or figures have a
broader license. No original article artwork is bundled. The Mendoza location
is Natural Earth public-domain data; its URL, feature ID and source hash are in
`spatial-scope.json`. Repository code licensing does not replace these source
notices or the map-boundary licenses in `content/geography/`.
