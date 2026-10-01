"""Sampling audit: planned vs achieved, read from the Thai report's own Table 1."""
from __future__ import annotations
import os
import re
from pathlib import Path
import pandas as pd, numpy as np
from . import preparation as prep
from .paths import DATA

THAI_REPORT = DATA / 'reference' / 'thai_report.docx'

# Provinces named in the Thai report, in health-region order 1-13.
SAMPLED_PROVINCES = ['เชียงราย', 'พิษณุโลก', 'นครสวรรค์', 'พระนครศรีอยุธยา', 'กาญจนบุรี',
                     'สมุทรปราการ', 'ขอนแก่น', 'อุดรธานี', 'นครราชสีมา', 'อุบลราชธานี',
                     'สุราษฎร์ธานี', 'สงขลา', 'กรุงเทพมหานคร']


def planned_allocation(path=None):
    """Parse planned n per health region x municipality from Thai report Table 1."""
    path = Path(path if path is not None else os.environ.get('PVS_THAI_REPORT', THAI_REPORT)).expanduser()
    if not path.is_file():
        raise FileNotFoundError(
            f'Thai sampling report not found: {path}. Place it at '
            'data/reference/thai_report.docx or set PVS_THAI_REPORT to its path.'
        )
    from docx import Document
    tb = Document(path).tables[0]
    rows = []
    for r in tb.rows:
        cells = []
        for c in r.cells:
            t = c.text.strip().replace('\n', ' ')
            if not cells or cells[-1] != t:
                cells.append(t)
        m = re.match(r'เขตที่\s*(\d+)', cells[0])
        if not m:
            continue
        nums = [int(x.replace(',', '')) for x in cells[1:] if re.fullmatch(r'[\d,]+', x)]
        reg = int(m.group(1))
        if reg == 13:                      # Bangkok row is merged in the source
            pop_tot, pop_mun, pop_non = nums[0], nums[0], 0
            plan_mun, plan_non = 165, 0
        else:
            pop_tot, pop_mun, pop_non, plan_mun, plan_non = nums[:5]
        rows.append({'Health region': reg, 'Population': pop_tot,
                     'Planned municipal': plan_mun, 'Planned non-municipal': plan_non,
                     'Planned total': plan_mun + plan_non})
    return pd.DataFrame(rows)


def planned_vs_achieved(d, planned):
    """Region x municipality: planned, achieved, deviation."""
    ach = (d.assign(reg=d['region_no'].astype(int))
             .pivot_table(index='reg', columns='municipality', values='order',
                          aggfunc='count', observed=True).fillna(0).astype(int))
    for c in ['municipal', 'non-municipal']:
        if c not in ach.columns:
            ach[c] = 0
    t = planned.set_index('Health region').join(
        ach.rename(columns={'municipal': 'Achieved municipal',
                            'non-municipal': 'Achieved non-municipal'}))
    t['Achieved total'] = t['Achieved municipal'] + t['Achieved non-municipal']
    t['Deviation (total)'] = t['Achieved total'] - t['Planned total']
    t['Planned % of sample'] = (100 * t['Planned total'] / t['Planned total'].sum()).round(1)
    t['Achieved % of sample'] = (100 * t['Achieved total'] / t['Achieved total'].sum()).round(1)
    t['Deviation (pp)'] = (t['Achieved % of sample'] - t['Planned % of sample']).round(1)
    t['Population % of Thailand'] = (100 * t['Population'] / t['Population'].sum()).round(1)
    t['Province sampled'] = SAMPLED_PROVINCES[:len(t)]
    return t.reset_index()


def quota_audit(d):
    """The two stated field quotas (sex 1:1; age 15-59 vs 60+ at 3:1) against achieved."""
    rows = []
    n = len(d)
    # --- sex quota
    for lab, val in [('Male', 'male'), ('Female', 'female')]:
        k = int((d['sex'] == val).sum())
        rows.append({'Quota dimension': 'Sex (planned 1:1)', 'Category': lab,
                     'Planned %': 50.0, 'Achieved n': k, 'Achieved %': round(100*k/n, 1),
                     'Deviation (pp)': round(100*k/n - 50.0, 1)})
    for lab, mask in [('Other sex', d['sex'] == 'other'),
                      ('Refused to state sex', d['gender'].astype('object')
                       .str.startswith('999', na=False))]:
        k = int(mask.sum())
        rows.append({'Quota dimension': 'Sex (planned 1:1)', 'Category': lab,
                     'Planned %': np.nan, 'Achieved n': k, 'Achieved %': round(100*k/n, 1),
                     'Deviation (pp)': np.nan})
    # --- age quota. NB the plan says 15-59 but the instrument screens out under-18s.
    for lab, val, plan in [('18-59 (plan says 15-59)', '18-59', 75.0), ('60+', '60+', 25.0)]:
        k = int((d['age_quota'] == val).sum())
        rows.append({'Quota dimension': 'Age (planned 3:1)', 'Category': lab,
                     'Planned %': plan, 'Achieved n': k, 'Achieved %': round(100*k/n, 1),
                     'Deviation (pp)': round(100*k/n - plan, 1)})
    # --- municipality
    for lab, val, plan in [('Municipal', 'municipal', 34.3), ('Non-municipal', 'non-municipal', 65.7)]:
        k = int((d['municipality'] == val).sum())
        rows.append({'Quota dimension': 'Municipality (planned 686:1,314)', 'Category': lab,
                     'Planned %': plan, 'Achieved n': k, 'Achieved %': round(100*k/n, 1),
                     'Deviation (pp)': round(100*k/n - plan, 1)})
    return pd.DataFrame(rows)


def quota_cells(d):
    """Actual achieved sex x age quota cells — the unit recruiters worked to."""
    t = pd.crosstab(d['age_quota'], d['sex'], margins=True, margins_name='All')
    return t


def cluster_structure(d):
    """PSU structure available in the data, for the variance-estimation discussion."""
    rows = []
    rows.append({'Level': 'Health region (stratum)', 'Distinct units': d['region_no'].nunique(),
                 'Median n per unit': int(d.groupby('region_no').size().median())})
    rows.append({'Level': 'Province (one per region)', 'Distinct units': d['prov'].nunique(),
                 'Median n per unit': int(d.groupby('prov').size().median())})
    rows.append({'Level': 'District', 'Distinct units': d['dist'].nunique(),
                 'Median n per unit': int(d.groupby('dist').size().median())})
    rows.append({'Level': 'Subdistrict (PPS-selected PSU)', 'Distinct units': d['subdist'].nunique(),
                 'Median n per unit': int(d.groupby('subdist').size().median())})
    per_region = d.groupby('region_no')['prov'].nunique()
    rows.append({'Level': 'Provinces per region (single-PSU check)',
                 'Distinct units': f'min {per_region.min()}, max {per_region.max()}',
                 'Median n per unit': ''})
    sub_per_prov = d.groupby('prov')['subdist'].nunique()
    rows.append({'Level': 'Subdistricts per province',
                 'Distinct units': f'min {sub_per_prov.min()}, max {sub_per_prov.max()}',
                 'Median n per unit': ''})
    return pd.DataFrame(rows)
