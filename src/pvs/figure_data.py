"""
Chart-ready data behind every figure, laid out for pasting into a PowerPoint chart.

    .venv/bin/python -m pvs figure_data

Writes output/figure_data/:
  * one CSV per figure, named to match the PNG
  * All figure data.xlsx, one sheet per figure

Layout in every file: column A holds the category labels, each following column is one
series with its name in row 1 — exactly the shape PowerPoint's chart data sheet expects.
Numbers only in the plotting block; any confidence bounds or flags come after a blank
spacer column so they are easy to leave out of the selection.

Values are read from output/tables/, the same source the figures use,
so a figure and its data file cannot disagree.
"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from . import preparation as prep
from .figures import _parse

from .paths import OUTPUT as OUT
TAB, DAT = f'{OUT}/tables', f'{OUT}/figure_data'
SHORT = {'public primary care': 'Public primary care',
         'public hospital OPD/ER': 'Public hospital OPD/ER',
         'private clinic/pharmacy': 'Private clinic/pharmacy',
         'private hospital OPD/ER': 'Private hospital OPD/ER'}
SHEETS: dict[str, pd.DataFrame] = {}


def _w(fname, df, sheet):
    os.makedirs(DAT, exist_ok=True)
    df.to_csv(f'{DAT}/{fname}.csv', index=False, encoding='utf-8-sig')
    SHEETS[sheet] = df
    print(f'  {fname}.csv  ({len(df)} rows x {len(df.columns)} cols)')


def _pct_block(table, measures, label_col='Measure', rename=None, ci=True):
    """Rows = measures, columns = the four provider groups, values = percentages."""
    t = pd.read_csv(f'{TAB}/{table}.csv')
    t[label_col] = t[label_col].astype(str).str.strip()
    t = t[t[label_col].isin(measures)].set_index(label_col).reindex(measures)
    out = pd.DataFrame({'Category': [(rename or {}).get(m, m) for m in measures]})
    for g in prep.GROUPS:
        out[SHORT[g]] = [round(_parse(t.loc[m, g])[2], 1) for m in measures]
    if ci:
        out[''] = ''
        for g in prep.GROUPS:
            out[f'{SHORT[g]} — 95% CI low'] = [round(_parse(t.loc[m, g])[3], 1) for m in measures]
            out[f'{SHORT[g]} — 95% CI high'] = [round(_parse(t.loc[m, g])[4], 1) for m in measures]
    return out


def _forest_block(csv, group, order=None):
    e = pd.read_csv(f'{TAB}/{csv}.csv')
    e = e[e['Group'] == group].copy()
    if order:
        e['__o'] = e['Outcome'].map({o: i for i, o in enumerate(order)})
        e = e.sort_values('__o')
    pcol = 'p (BH within family)' if 'p (BH within family)' in e.columns else 'p'
    out = pd.DataFrame({
        'Outcome': e['Outcome'].values,
        'Adjusted odds ratio': e['aOR'].round(2).values,
        '': '',
        'Error bar — minus': (e['aOR'] - e['lo']).round(3).values,
        'Error bar — plus': (e['hi'] - e['aOR']).round(3).values,
        '95% CI low': e['lo'].round(2).values,
        '95% CI high': e['hi'].round(2).values,
        'Difference (percentage points)': e['Diff (pp)'].round(1).values,
        'p (unadjusted)': e['p'].round(4).values,
        'p (BH-adjusted)': e[pcol].round(4).values,
        'Significant after BH (1 = yes)': (e[pcol] < 0.05).astype(int).values,
    })
    return out


def main():
    SHEETS.clear()
    os.makedirs(DAT, exist_ok=True)
    print('Writing chart-ready data …')

    # ---------------------------------------------------------------- Figure A1
    t = pd.read_csv(f'{TAB}/T10_planned_vs_achieved_region.csv')
    _w('Figure A1 - Planned vs achieved sample', pd.DataFrame({
        'Health region': [f"Region {int(r['Health region'])} — {r['Province sampled']}"
                          for _, r in t.iterrows()],
        'Planned': t['Planned total'].values,
        'Achieved': t['Achieved total'].values,
        '': '',
        'Deviation': t['Deviation (total)'].values,
        'Planned municipal': t['Planned municipal'].values,
        'Achieved municipal': t['Achieved municipal'].values,
        'Planned non-municipal': t['Planned non-municipal'].values,
        'Achieved non-municipal': t['Achieved non-municipal'].values,
    }), 'Fig A1 sampling')

    # ---------------------------------------------------------------- Figure 4
    prev = ['Blood pressure measured (Q27A)', 'Blood sugar tested (Q27F)',
            'Blood lipids tested (Q27G)', 'Dental examination (Q27E)',
            'Vision check (Q27D)', 'Mental-health service received (Q27H)']
    _w('Figure 4 - Preventive services by provider group',
       _pct_block('T30_preventive_descriptive', prev,
                  rename={m: m.split(' (Q')[0] for m in prev}), 'Fig 4 preventive')

    # ---------------------------------------------------------------- Figure A2
    _w('Figure A2 - Preventive services adjusted',
       _forest_block('T31_preventive_adjusted', 'private hospital OPD/ER'), 'Fig A2 preventive adj')

    # ---------------------------------------------------------------- Figure 5
    t = pd.read_csv(f'{TAB}/T50_experience_by_usual_group.csv')
    t['domain'] = t['Measure'].str.split(' — ').str[0]
    t['item'] = t['Measure'].str.split(' — ').str[1]
    dorder = ['Access & process', 'Interpersonal', 'Continuity',
              'Perceived competence & readiness', 'Global rating']
    t['__o'] = t['domain'].map({d: i for i, d in enumerate(dorder)})
    t = t.sort_values(['__o', 'item'])
    blk = pd.DataFrame({'Item': t['item'].values})
    for g in prep.GROUPS:
        blk[SHORT[g]] = [round(_parse(v)[2], 1) for v in t[g]]
    blk[''] = ''
    blk['Domain'] = t['domain'].values
    for g in prep.GROUPS:
        blk[f'{SHORT[g]} — n/N'] = [f'{_parse(v)[0]}/{_parse(v)[1]}' for v in t[g]]
    _w('Figure 5 - Visit experience by domain', blk, 'Fig 5 experience')

    # ---------------------------------------------------------------- Figure 7
    t = pd.read_csv(f'{TAB}/T80_thailand_india_indicators.csv')
    th = [float(s.split(' ')[0]) for s in t['Thailand (this survey), % (95% CI)']]
    lo = [float(s.split('(')[1].split('-')[0]) for s in t['Thailand (this survey), % (95% CI)']]
    hi = [float(s.split('-')[1].rstrip(')')) for s in t['Thailand (this survey), % (95% CI)']]
    _w('Figure 7 - Thailand vs India health security', pd.DataFrame({
        'Indicator': t['Indicator'].values,
        'Thailand (this survey)': th,
        'India (PVS round 1)': t['India (Kruk 2024), %'].values,
        '15-country PVS average': t['15-country average, %'].values,
        '': '',
        'Thailand — 95% CI low': lo,
        'Thailand — 95% CI high': hi,
        'Thailand error bar — minus': [round(a - l, 1) for a, l in zip(th, lo)],
        'Thailand error bar — plus': [round(h - a, 1) for a, h in zip(th, hi)],
    }), 'Fig 7 Thailand vs India')

    # ---------------------------------------------------------------- Figure 6
    _w('Figure 6 - Adjusted differences private hospital users',
       _forest_block('T90_all_adjusted_combined', 'private hospital OPD/ER'), 'Fig 6 adjusted overview')

    # ---------------------------------------------------------------- Figure 1
    prof = ['Aged under 50', 'Lives in a municipality', 'Upper-secondary education or above',
            'Household income ฿30,000+ / month', 'Social Security (SSS)',
            'Universal Coverage (UCS)', 'Owns private health insurance',
            'Self-rated health good or better', 'Chronic condition ≥ 6 months',
            'High patient activation']
    _w('Figure 1 - Profile by provider group',
       _pct_block('T24_profile_binary', prof), 'Fig 1 profile')

    # ---------------------------------------------------------------- Figure 2
    reasons = ['Covered by my insurance scheme', 'Short waiting time', 'Close to home',
               'Has medicines and equipment', 'Low cost', 'Provider skill']
    _w('Figure 2 - Reason for choosing provider',
       _pct_block('T25_reasons_binary', reasons), 'Fig 2 reasons')

    # ---------------------------------------------------------------- Figure 3
    qorder = ['<15 min', '15-29 min', '30-59 min', '1-2 h', '2-3 h', '3-4 h', '4 h+']
    t = pd.read_csv(f'{TAB}/T22_access_by_group.csv')
    t['Measure'] = t['Measure'].astype(str).str.strip()
    a = pd.DataFrame({'Provider group': [SHORT[g] for g in prep.GROUPS]})
    for q in qorder:
        row = t[t['Measure'] == q]
        a[q] = [round(_parse(row.iloc[0][g])[2], 1) if len(row) else np.nan for g in prep.GROUPS]
    _w('Figure 3a - Waiting time at the facility', a, 'Fig 3a waiting')
    util = ['Walked in without an appointment', 'Waited 1 hour or more at the facility',
            'Used only one facility (of those with >1 visit)', 'Admitted overnight in 12 months',
            'Received a home visit', 'Reported an unmet health-care need']
    _w('Figure 3b - Pattern of service use',
       _pct_block('T26_utilisation_binary', util), 'Fig 3b service use')

    # ---------------------------------------------------------------- workbook
    xlsx = f'{DAT}/All figure data.xlsx'
    with pd.ExcelWriter(xlsx, engine='openpyxl') as xw:
        def _key(name):
            import re as _re
            m = _re.match(r'Fig (A?)(\d+)([ab]?)', name)
            return (1 if m.group(1) else 0, int(m.group(2)), m.group(3)) if m else (2, 0, '')
        for sheet in sorted(SHEETS, key=_key):
            df = SHEETS[sheet]
            df.to_excel(xw, sheet_name=sheet[:31], index=False)
            ws = xw.sheets[sheet[:31]]
            ws.column_dimensions['A'].width = 42
            for col in list('BCDEFGHIJK'):
                ws.column_dimensions[col].width = 15
            ws.freeze_panes = 'B2'
    print(f'  All figure data.xlsx  ({len(SHEETS)} sheets)')

    with open(f'{DAT}/README.md', 'w') as fh:
        fh.write(README)
    print(f'\nDone. {len(SHEETS)} datasets in {DAT}/')


README = """# Figure data

The numbers behind every figure, laid out for pasting straight into a PowerPoint chart.

Generated by `src/pvs/figure_data.py` **from the same tables the figures are drawn
from**, so a figure and its data file cannot disagree. Re-run with:

    .venv/bin/python -m pvs figure_data

## How to use it in PowerPoint

1. Open `All figure data.xlsx` (or the individual CSV named after the figure).
2. Select the **plotting block** — column A plus the coloured-in series columns, up to the
   blank spacer column. Copy.
3. In PowerPoint: **Insert > Chart**, pick the chart type, and in the small data sheet that
   opens, select cell A1 and paste. Delete any leftover sample rows or columns.

Column A always holds the category labels and each following column is one series, with the
series name in row 1 — the shape PowerPoint expects.

Everything to the right of the **blank spacer column** is extra: confidence bounds, counts,
p-values, significance flags. Leave it out of the selection unless you want it.

## Which chart type

The file names match the figure numbers in
`../Report - Customers of private hospitals in the Thai health system.docx`. Figures A1 and A2
are not in the report itself — A1 appears in the sampling appendix and A2 in the analytical
supplement.

| File | Suggested chart | Notes |
|---|---|---|
| Figure 1 - Profile by provider group | Clustered bar | Four series; CI columns available for error bars |
| Figure 2 - Reason for choosing provider | Clustered bar | Four series |
| Figure 3a - Waiting time at the facility | **100% stacked bar** | Rows are groups, columns are time bands; they sum to 100 |
| Figure 3b - Pattern of service use | Clustered bar | Four series |
| Figure 4 - Preventive services by provider group | Clustered bar | Four series |
| Figure 5 - Visit experience by domain | Clustered bar or dot plot | Sorted by domain; the Domain column is for grouping labels |
| Figure 6 - Adjusted differences private hospital users | Bar or scatter, log X axis | The full forest plot; add a vertical line at 1 for "no difference" |
| Figure 7 - Thailand vs India health security | Clustered bar | Three series; Thailand error-bar columns supplied |
| Figure A1 - Planned vs achieved sample | Clustered bar | Two series: Planned, Achieved |
| Figure A2 - Preventive services adjusted | Bar or scatter, log X axis | Plot "Adjusted odds ratio"; add a vertical line at 1 |

## Error bars

For **Figure 6** and **Figure A2** (the two forest plots) use **Custom error bars** and point PowerPoint at the columns
`Error bar — minus` and `Error bar — plus`. These are already lengths relative to the
estimate, which is what PowerPoint wants — not the CI bounds themselves. The bounds are
supplied separately as `95% CI low` / `95% CI high` if you need to label them.

For Figures 1, 2, 4 and 3b the `95% CI low` / `95% CI high` columns are bounds; subtract the
estimate yourself if you want error bars. Figure 7 already supplies Thailand's as lengths.

## Reading the values

* Percentage columns are percentages of the eligible respondents in that group, not counts.
  Denominators differ between rows wherever a question was asked of a subset — the `n/N`
  columns in RF4, and the source tables in `../tables/`, give them.
* `Adjusted odds ratio` compares each group with **public hospital OPD/ER**, adjusted for age
  band, sex, education, income, municipality, coverage scheme, self-rated health and chronic
  illness, with cluster-robust standard errors.
* `Difference (percentage points)` is the difference in average predicted probability. **Use
  this for magnitude in a slide, not the odds ratio** — an odds ratio is not a probability
  ratio and reads as far larger than the real difference.
* `Significant after BH (1 = yes)` marks Benjamini-Hochberg adjusted p < 0.05 within that
  outcome family. A 0 means not detected, which is not the same as no difference.
"""


if __name__ == '__main__':
    main()
