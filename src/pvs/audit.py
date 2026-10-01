"""Priority-0 audit: cohort flow, provider definitions, coding, denominators."""
from __future__ import annotations
import pandas as pd, numpy as np
from scipy import stats
from . import preparation as prep

from .paths import TABLES as OUT, MAPPINGS


# ---------------------------------------------------------------- cohort
def q14_q15_crosstab(raw_df):
    """Original Q14 x Q15 labels against the final classification."""
    ct = pd.crosstab(raw_df['mhos_type'].fillna('(not asked — Q13 = no)'),
                     raw_df['fhos_type'].fillna('(not asked — Q13 = no)'), margins=True,
                     margins_name='All')
    return ct


def classification_map(d):
    """Every Q14 x Q15 combination, its n, and where it lands."""
    rows = []
    sub = d[d['has_usual'] == 'yes']
    for (sec, setg), g in sub.groupby([sub['mhos_type'].astype('object'),
                                       sub['fhos_type'].astype('object')], dropna=False):
        grp = g['provider_group'].dropna().unique()
        rows.append({'Q14 (sector)': sec, 'Q15 (setting)': setg, 'n': len(g),
                     'Classified as': grp[0] if len(grp) else 'EXCLUDED',
                     'Exclusion reason': g['exclusion_reason'].dropna().unique()[0]
                     if g['exclusion_reason'].notna().any() else ''})
    return pd.DataFrame(rows).sort_values(['Q14 (sector)', 'Q15 (setting)'])


def usual_vs_last(d):
    """Three different 'match' definitions the English report conflated."""
    coh = d[d['provider_group'].notna()]
    out = []
    for g in prep.GROUPS:
        s = coh[coh['provider_group'] == g]
        n = len(s)
        same_sector = (s['concordant_sector'] == 'yes').sum()
        same_group = (s['concordant_group'] == 'yes').sum()
        same_settingtype = s['last_hospital'].eq(s['usual_hospital']).sum()
        out.append({'Usual source group': g, 'n': n,
                    'Last visit: same SECTOR, n (%)': f'{same_sector} ({100*same_sector/n:.1f})',
                    'Last visit: same SETTING TYPE, n (%)': f'{same_settingtype} ({100*same_settingtype/n:.1f})',
                    'Last visit: same SECTOR *and* SETTING, n (%)': f'{same_group} ({100*same_group/n:.1f})'})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- coding
def health_coding_impact(d, raw_df):
    """Before/after for self-rated health; separates threshold from coding error."""
    import os
    m = pd.read_csv(MAPPINGS / 'map_health_level.csv')
    old = dict(zip(m['health_level'], m['parameter_map']))
    old_lab = raw_df['health_level'].astype('object').map(old)
    rows = []
    n = raw_df['health_level'].notna().sum()
    rows.append({'Definition': 'Project map as used in Thai report / Sections 4-6 '
                               '(map_health_level.csv: ดี + ดีเยี่ยม = good)',
                 '"good" n': int((old_lab == 'good').sum()),
                 '% of 2,017': round(100 * (old_lab == 'good').sum() / len(raw_df), 1)})
    rows.append({'Definition': 'Corrected top-3 (ดี, ดีมาก, ดีเยี่ยม) — matches map_mental_level.csv',
                 '"good" n': int((d['health_good3'] == 'good or better').sum()),
                 '% of 2,017': round(100 * (d['health_good3'] == 'good or better').sum() / len(d), 1)})
    rows.append({'Definition': 'Top-2 box (ดีมาก, ดีเยี่ยม) — matches how quality items are dichotomised',
                 '"good" n': int((d['health_top2'] == 'very good/excellent').sum()),
                 '% of 2,017': round(100 * (d['health_top2'] == 'very good/excellent').sum() / len(d), 1)})
    rows.append({'Definition': 'Mental health, top-3 (for comparison; unchanged)',
                 '"good" n': int((d['mental_good3'] == 'good or better').sum()),
                 '% of 2,017': round(100 * (d['mental_good3'] == 'good or better').sum() / len(d), 1)})
    return pd.DataFrame(rows)


def age_denominator_audit(d):
    """Reproduces the Figure-1 'under 45' discrepancy and shows the fix."""
    coh = d[d['provider_group'].notna()]
    rows = []
    for g in prep.GROUPS:
        s = coh[coh['provider_group'] == g]
        n_all, n_exact = len(s), int(s['age_exact'].notna().sum())
        u45_exact = int((s['age_exact'] < 45).sum())
        # the band-based, fully-observed equivalent
        u50_band = int((s['age_u50'] == 'yes').sum())
        rows.append({'Group': g, 'n (group)': n_all, 'n with exact age': n_exact,
                     '<45 among exact-age, n (%)': f'{u45_exact} ({100*u45_exact/n_exact:.1f})',
                     '<45 / whole group (the figure\'s implicit rule), %': round(100*u45_exact/n_all, 1),
                     'Under 50 by age BAND, n (%) — fully observed':
                         f'{u50_band} ({100*u50_band/n_all:.1f})'})
    return pd.DataFrame(rows)


def denominator_rules(d):
    """Eligible / observed / structurally skipped, for every analysed outcome."""
    coh = d[d['provider_group'].notna()]
    spec = [
        ('has_usual', 'Has a usual source of care', None),
        ('usual_reason', 'Main reason for choosing usual source', 'Q13 = yes'),
        ('usual_qual_top2', 'Rates usual facility very good/excellent', 'Q13 = yes'),
        ('visits_cat', 'Outpatient visits (Q18)', None),
        ('one_facility', 'Used only one facility', 'Q18 > 1 or Q19 in 2-4 (structural skip)'),
        ('admit', 'Admitted overnight, 12 months', None),
        ('unmet', 'Unmet health-care need', None),
        ('med_error_ever', 'Perceived medical error (ever)', None),
        ('discrim_ever', 'Felt discriminated against (ever)', None),
        ('appoint', 'Made an appointment', None),
        ('queue_cat', 'Waiting time at facility', None),
        ('wait_cat', 'Booking-to-appointment wait', 'Q35 = appointment (structural skip)'),
        ('health_security', 'Health security (Q41a & Q41b)', None),
    ]
    for s in prep.SCREENING:
        spec.append((s + '_r', f'Q27 {s}', None))
    for c, lab in prep.EXP_ITEMS.items():
        spec.append((c + '_ord', f'Q38 {lab}', 'excludes structural not-applicable'
                     if c in prep.EXP_NA_CODE else None))
    for c, lab in [('q_maternal', 'Q40 maternal'), ('q_child', 'Q40 child'),
                   ('q_chronic', 'Q40 chronic'), ('q_mentalhealth', 'Q40 mental health')]:
        spec.append((c + '_ord', lab, 'excludes "cannot evaluate"'))
    rows = []
    for col, lab, note in spec:
        if col not in coh.columns:
            continue
        obs = int(coh[col].notna().sum())
        struct = 0
        if col.endswith('_ord'):
            base = col[:-4]
            for suffix in ('_na', '_cannot_eval'):
                flag = base + suffix
                if flag in coh.columns and coh[flag].dtype == bool:
                    struct = int(coh[flag].sum())
                    break
        rows.append({'Variable': col, 'Item': lab, 'Cohort n': len(coh),
                     'Observed (valid) n': obs,
                     'Structural not-applicable n': struct,
                     'Other missing n': len(coh) - obs - struct,
                     'Recall period': prep.RECALL.get(col.replace('_r', '').replace('_ord', ''),
                                                      ('most recent visit', ''))[0],
                     'Note': note or ''})
    return pd.DataFrame(rows)


def complete_case_audit(d, covariates):
    """Why a model has n=X: exclusions variable by variable and by group."""
    coh = d[d['provider_group'].notna()].copy()
    rows = []
    running = pd.Series(True, index=coh.index)
    for c in covariates:
        miss = coh[c].isna()
        rows.append({'Covariate': c, 'Missing in cohort': int(miss.sum()),
                     'Newly excluded': int((miss & running).sum())})
        running = running & ~miss
    rows.append({'Covariate': 'COMPLETE CASES', 'Missing in cohort': '',
                 'Newly excluded': int(running.sum())})
    by_group = coh.loc[running, 'provider_group'].value_counts().reindex(prep.GROUPS)
    return pd.DataFrame(rows), by_group
