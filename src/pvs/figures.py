"""Figures for the 2026-09 revision. Every value is read from the exported tables."""
from __future__ import annotations
import os, re
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from . import preparation as prep

from .paths import OUTPUT as OUT
TAB, FIG = f'{OUT}/tables', f'{OUT}/figures'
PAL = {'public primary care': '#5598e7', 'public hospital OPD/ER': '#184f95',
       'private clinic/pharmacy': '#e8853f', 'private hospital OPD/ER': '#a8400c'}
SHORT = {'public primary care': 'Public primary care',
         'public hospital OPD/ER': 'Public hospital OPD/ER',
         'private clinic/pharmacy': 'Private clinic/pharmacy',
         'private hospital OPD/ER': 'Private hospital OPD/ER'}
INK, SEC, MUT, GRID = '#0b0b0b', '#52514e', '#898781', '#e1e0d9'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.edgecolor': '#c3c2b7',
                     'text.color': INK, 'axes.labelcolor': SEC, 'xtick.color': MUT,
                     'ytick.color': SEC, 'figure.facecolor': '#fff', 'axes.facecolor': '#fff'})


def _parse(cell):
    """'123/456 (27.0; 23.1-31.2)' -> (123, 456, 27.0, 23.1, 31.2)"""
    if not isinstance(cell, str):
        return (np.nan,)*5
    m = re.match(r'(\d+)/(\d+) \(([\d.]+)(?:; ([\d.]+)-([\d.]+))?\)', cell.strip())
    if not m:
        return (np.nan,)*5
    g = m.groups()
    return (int(g[0]), int(g[1]), float(g[2]),
            float(g[3]) if g[3] else np.nan, float(g[4]) if g[4] else np.nan)


def _clean(ax, xmax=100):
    ax.set_xlim(0, xmax*1.10)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.set_axisbelow(True)
    ax.grid(axis='x', color=GRID, linewidth=0.6, zorder=0)


def _legend(ax, ncol=4):
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.005), ncol=ncol, frameon=False,
              fontsize=8.2, handlelength=1.0, columnspacing=1.1, handletextpad=0.4)


def fig_sampling():
    t = pd.read_csv(f'{TAB}/T10_planned_vs_achieved_region.csv')
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    y = np.arange(len(t))
    ax.barh(y+0.19, t['Planned total'], height=0.36, color='#c3c2b7', zorder=3, label='Planned')
    ax.barh(y-0.19, t['Achieved total'], height=0.36, color='#184f95', zorder=3, label='Achieved')
    for i, r in t.iterrows():
        ax.text(max(r['Planned total'], r['Achieved total'])+4, i,
                f"{int(r['Achieved total'])} ({r['Deviation (total)']:+d})",
                va='center', fontsize=8, color=SEC)
    ax.set_yticks(y)
    ax.set_yticklabels([f"Region {int(r['Health region'])} — {r['Province sampled']}"
                        for _, r in t.iterrows()], fontsize=9)
    ax.invert_yaxis(); _clean(ax, t['Planned total'].max())
    ax.set_xlabel('Respondents', fontsize=9)
    ax.set_title('Planned versus achieved sample, by health region',
                 loc='left', fontweight='bold', fontsize=12.5, color=INK, pad=26)
    _legend(ax, 2)
    fig.text(0.005, -0.03, 'Planned allocation from Table 1 of the Thai report (2,000). Achieved 2,017. '
             'One province was sampled per region; the region label names that province.',
             fontsize=7.6, style='italic', color=MUT)
    fig.savefig(f'{FIG}/Figure A1 - Planned vs achieved sample.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def _grouped_from_desc(path, measures, title, subtitle, fname, xmax=100, note=''):
    t = pd.read_csv(path)
    t = t[t['Measure'].isin(measures)].set_index('Measure').reindex(measures)
    fig, ax = plt.subplots(figsize=(9.8, 0.72*len(measures)+2.4))
    n = len(prep.GROUPS); h = 0.8/n; y = np.arange(len(t))
    for i, g in enumerate(prep.GROUPS):
        vals, los, his = [], [], []
        for _, r in t.iterrows():
            k, N, p, lo, hi = _parse(r[g])
            vals.append(p); los.append(lo); his.append(hi)
        off = -(n-1)/2*h + i*h
        ax.barh(y+off, vals, height=h*0.86, color=PAL[g], zorder=3, label=SHORT[g])
        ax.errorbar(vals, y+off, xerr=[np.array(vals)-np.array(los), np.array(his)-np.array(vals)],
                    fmt='none', ecolor='#00000055', elinewidth=0.9, capsize=1.6, zorder=4)
        for yy, v in zip(y+off, vals):
            if v == v:
                ax.text(v+1.4, yy, f'{v:.0f}', va='center', fontsize=7.8, color=SEC)
    ax.set_yticks(y); ax.set_yticklabels(t.index, fontsize=9.3)
    ax.invert_yaxis(); _clean(ax, xmax)
    ax.set_xlabel('% of the eligible respondents in each group (95% CI)', fontsize=9)
    ax.set_title(title, loc='left', fontweight='bold', fontsize=12.5, color=INK, pad=32)
    _legend(ax)
    fig.text(0.005, -0.02, note or subtitle, fontsize=7.6, style='italic', color=MUT)
    fig.savefig(f'{FIG}/{fname}', dpi=200, bbox_inches='tight')
    plt.close(fig)


def fig_preventive():
    _grouped_from_desc(
        f'{TAB}/T30_preventive_descriptive.csv',
        ['Blood pressure measured (Q27A)', 'Blood sugar tested (Q27F)',
         'Blood lipids tested (Q27G)', 'Dental examination (Q27E)',
         'Vision check (Q27D)', 'Mental-health service received (Q27H)'],
        'Preventive and screening services received, by usual source of care',
        '', 'Figure 4 - Preventive services by provider group.png',
        note=('Q27 refers to receipt in the past 12 months (original questionnaire confirmed on 2026-10-01). '
              '\nThe questionnaire does not record where a '
              'service was delivered, so receipt is not attributable to the usual source of care.'))


def fig_forest(csv, group, title, fname, note='', order=None):
    e = pd.read_csv(csv)
    e = e[e['Group'] == group].copy()
    if order:
        e['__o'] = e['Outcome'].map({o: i for i, o in enumerate(order)})
        e = e.sort_values('__o')
    fig, ax = plt.subplots(figsize=(9.9, 0.42*len(e)+2.6))
    y = np.arange(len(e))[::-1]
    ax.axvline(1, color='#c3c2b7', lw=1.1, zorder=1)
    pcol = 'p (BH within family)' if 'p (BH within family)' in e.columns else 'p'
    for yy, (_, r) in zip(y, e.iterrows()):
        sig = bool(r[pcol] < 0.05)
        col = PAL[group] if sig else MUT
        ax.plot([r['lo'], r['hi']], [yy, yy], color=col, lw=2.2, zorder=3, solid_capstyle='round')
        ax.scatter([r['aOR']], [yy], s=66, color=col, zorder=4, edgecolor='#fff', linewidth=1.2)
        ax.text(11.5, yy, f"{r['aOR']:.2f} ({r['lo']:.2f}–{r['hi']:.2f})", va='center', ha='right',
                fontsize=8, color=INK if sig else MUT, fontweight='bold' if sig else 'normal')
        ax.text(19.5, yy, f"{r['Diff (pp)']:+.1f}", va='center', ha='right',
                fontsize=8, color=INK if sig else MUT)
    ax.set_xscale('log'); ax.set_xlim(0.25, 22)
    ax.set_xticks([0.5, 1, 2, 4, 8]); ax.set_xticklabels(['0.5', '1', '2', '4', '8'])
    ax.set_yticks(y); ax.set_yticklabels(e['Outcome'], fontsize=9.2)
    ax.set_ylim(-0.9, len(e)-0.1)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(axis='y', length=0); ax.set_axisbelow(True)
    ax.grid(axis='x', color=GRID, linewidth=0.6, zorder=0)
    ax.set_xlabel(f'Adjusted odds ratio (log scale) — {SHORT[group]} vs public hospital OPD/ER', fontsize=9)
    ax.set_title(title, loc='left', fontweight='bold', fontsize=12.5, color=INK, pad=30)
    ax.text(0, 1.025, 'Coloured markers: BH-adjusted p < 0.05 within the outcome family.',
            transform=ax.transAxes, fontsize=8.2, color=SEC)
    ax.text(11.5, len(e)-0.55, 'aOR (95% CI)', ha='right', fontsize=8.2, color=SEC, fontweight='bold')
    ax.text(19.5, len(e)-0.55, 'pp diff', ha='right', fontsize=8.2, color=SEC, fontweight='bold')
    fig.text(0.005, -0.03, note, fontsize=7.6, style='italic', color=MUT)
    fig.savefig(f'{FIG}/{fname}', dpi=200, bbox_inches='tight')
    plt.close(fig)


def fig_experience_domains():
    t = pd.read_csv(f'{TAB}/T50_experience_by_usual_group.csv')
    t['domain'] = t['Measure'].str.split(' — ').str[0]
    t['item'] = t['Measure'].str.split(' — ').str[1]
    dorder = ['Access & process', 'Interpersonal', 'Continuity',
              'Perceived competence & readiness', 'Global rating']
    t['__o'] = t['domain'].map({d: i for i, d in enumerate(dorder)})
    t = t.sort_values(['__o', 'item'])
    fig, ax = plt.subplots(figsize=(9.9, 6.4))
    y = np.arange(len(t))
    for i, g in enumerate(prep.GROUPS):
        vals = [_parse(r[g])[2] for _, r in t.iterrows()]
        ax.scatter(vals, y, s=74, color=PAL[g], zorder=4, edgecolor='#fff',
                   linewidth=1.3, label=SHORT[g])
    for i, (_, r) in enumerate(t.iterrows()):
        vals = [_parse(r[g])[2] for g in prep.GROUPS]
        ax.plot([min(vals), max(vals)], [i, i], color=GRID, lw=2.1, zorder=2, solid_capstyle='round')
    ax.set_yticks(y); ax.set_yticklabels(t['item'], fontsize=9.3)
    prev, bounds = None, []
    for i, dm in enumerate(t['domain']):
        if dm != prev:
            bounds.append((i, dm)); prev = dm
    for i, dm in bounds:
        ax.annotate(dm, xy=(-0.42, i), xycoords=('axes fraction', 'data'), fontsize=8.2,
                    fontweight='bold', color=SEC, ha='left', va='center', annotation_clip=False)
        if i:
            ax.axhline(i-0.5, color=GRID, lw=0.8, zorder=1)
    ax.set_xlim(15, 80); ax.invert_yaxis()
    ax.spines[['top', 'right']].set_visible(False); ax.tick_params(axis='y', length=0)
    ax.set_axisbelow(True); ax.grid(axis='x', color=GRID, linewidth=0.6, zorder=0)
    ax.set_xlabel('% rating the item very good or excellent at their most recent visit', fontsize=9)
    ax.set_title('Experience of the most recent visit, grouped by domain',
                 loc='left', fontweight='bold', fontsize=12.5, color=INK, pad=30)
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.005), ncol=2, frameon=False, fontsize=8.4,
              handletextpad=0.3, columnspacing=1.3, scatterpoints=1)
    fig.text(0.005, -0.03,
             'Domain grouping is an interpretive framework, not a validated scale. Denominators exclude the '
             'explicit "not applicable" answers\n(no prior visit; no other staff present) — see table T53. '
             'Items describe the LAST visit, which is not always the usual source of care.',
             fontsize=7.6, style='italic', color=MUT)
    fig.savefig(f'{FIG}/Figure 5 - Visit experience by domain.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def fig_india():
    t = pd.read_csv(f'{TAB}/T80_thailand_india_indicators.csv')
    fig, ax = plt.subplots(figsize=(9.4, 3.9))
    y = np.arange(len(t)); h = 0.24
    th = [float(s.split(' ')[0]) for s in t['Thailand (this survey), % (95% CI)']]
    lo = [float(s.split('(')[1].split('-')[0]) for s in t['Thailand (this survey), % (95% CI)']]
    hi = [float(s.split('-')[1].rstrip(')')) for s in t['Thailand (this survey), % (95% CI)']]
    ax.barh(y+h, th, height=h*0.9, color='#a8400c', zorder=3, label='Thailand (this survey)')
    ax.errorbar(th, y+h, xerr=[np.array(th)-np.array(lo), np.array(hi)-np.array(th)],
                fmt='none', ecolor='#00000066', elinewidth=1, capsize=2, zorder=4)
    ax.barh(y, t['India (Kruk 2024), %'], height=h*0.9, color='#184f95', zorder=3, label='India (PVS round 1)')
    ax.barh(y-h, t['15-country average, %'], height=h*0.9, color='#c3c2b7', zorder=3,
            label='15-country PVS average')
    for yy, v in list(zip(y+h, th)) + list(zip(y, t['India (Kruk 2024), %'])) + \
                 list(zip(y-h, t['15-country average, %'])):
        ax.text(v+1.2, yy, f'{v:.1f}', va='center', fontsize=8.2, color=SEC)
    ax.set_yticks(y); ax.set_yticklabels(t['Indicator'], fontsize=9.4)
    ax.invert_yaxis(); _clean(ax, 100)
    ax.set_xlabel('% of respondents somewhat or very confident', fontsize=9)
    ax.set_title('Health security: Thailand, India and the 15-country PVS average',
                 loc='left', fontweight='bold', fontsize=12.5, color=INK, pad=28)
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.005), ncol=3, frameon=False,
              fontsize=8.4, handlelength=1.1, columnspacing=1.3)
    fig.text(0.005, -0.06,
             'India and average values read from Kruk et al. (2024) Lancet Glob Health, Figure 2A. '
             'The widely quoted 84.1% for India is the\n"can get good-quality care" series, NOT health security. '
             'Comparability was not independently verified — see table T81.',
             fontsize=7.6, style='italic', color=MUT)
    fig.savefig(f'{FIG}/Figure 7 - Thailand vs India health security.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def fig_profile():
    _grouped_from_desc(
        f'{TAB}/T24_profile_binary.csv',
        ['Aged under 50', 'Lives in a municipality', 'Upper-secondary education or above',
         'Household income \u0e3f30,000+ / month', 'Social Security (SSS)',
         'Universal Coverage (UCS)', 'Owns private health insurance',
         'Self-rated health good or better', 'Chronic condition \u2265 6 months',
         'High patient activation'],
        'Who uses each type of usual source of care', '',
        'Figure 1 - Profile by provider group.png',
        note=("People's Voice Survey Thailand, 1,518 respondents with a classifiable usual source of care. "
              "Unweighted, with 95% Wilson intervals.\nAge uses the complete Q4 band; self-rated health uses "
              "the corrected coding; insurance ownership is not evidence of use."))


def fig_reasons():
    _grouped_from_desc(
        f'{TAB}/T25_reasons_binary.csv',
        ['Covered by my insurance scheme', 'Short waiting time', 'Close to home',
         'Has medicines and equipment', 'Low cost', 'Provider skill'],
        'Main reason for choosing the usual source of care', '',
        'Figure 2 - Reason for choosing provider.png', xmax=65,
        note=('Single-response item (Q16), asked only of respondents with a usual source of care. '
              'Categories below 3% in every group are omitted.\nA stated reason is not a record of '
              'registration or of who paid.'))


def fig_utilisation():
    t = pd.read_csv(f'{TAB}/T22_access_by_group.csv')
    qorder = ['<15 min', '15-29 min', '30-59 min', '1-2 h', '2-3 h', '3-4 h', '4 h+']
    seq = ['#cde2fb', '#9ec5f4', '#6da7ec', '#2a78d6', '#1c5cab', '#104281', '#0d366b']
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5))
    ax = axes[0]
    left = np.zeros(len(prep.GROUPS)); ypos = np.arange(len(prep.GROUPS))
    for q, col in zip(qorder, seq):
        row = t[t['Measure'].astype(str).str.strip() == q]
        vals = np.array([_parse(row.iloc[0][g])[2] for g in prep.GROUPS]) if len(row) else np.zeros(4)
        ax.barh(ypos, vals, left=left, height=0.62, color=col, zorder=3, label=q,
                edgecolor='#fff', linewidth=1.2)
        for y, v, l in zip(ypos, vals, left):
            if v >= 7:
                ax.text(l + v/2, y, f'{v:.0f}', ha='center', va='center', fontsize=8,
                        color='#fff' if col in seq[3:] else INK)
        left += vals
    ax.set_yticks(ypos)
    ax.set_yticklabels([SHORT[g].replace(' OPD/ER', '\nOPD/ER').replace('clinic/', 'clinic/\n')
                        for g in prep.GROUPS], fontsize=8.6)
    ax.invert_yaxis(); _clean(ax, 100)
    ax.set_xlabel('% of respondents', fontsize=9)
    ax.set_title('A  Time waited at the facility before being seen', loc='left',
                 fontweight='bold', fontsize=11, color=INK)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=7, frameon=False,
              fontsize=7.4, handlelength=1.0, columnspacing=0.8)
    ax = axes[1]
    u = pd.read_csv(f'{TAB}/T26_utilisation_binary.csv')
    rows = ['Walked in without an appointment', 'Waited 1 hour or more at the facility',
            'Used only one facility (of those with >1 visit)', 'Admitted overnight in 12 months',
            'Received a home visit', 'Reported an unmet health-care need']
    u = u[u['Measure'].isin(rows)].set_index('Measure').reindex(rows)
    n = len(prep.GROUPS); h = 0.8/n; y = np.arange(len(u))
    for i, g in enumerate(prep.GROUPS):
        vals = [_parse(r[g])[2] for _, r in u.iterrows()]
        off = -(n-1)/2*h + i*h
        ax.barh(y+off, vals, height=h*0.86, color=PAL[g], zorder=3, label=SHORT[g])
        for yy, v in zip(y+off, vals):
            ax.text(v+1.3, yy, f'{v:.0f}', va='center', fontsize=7.6, color=SEC)
    ax.set_yticks(y)
    ax.set_yticklabels([r.replace(' at the facility', '\nat the facility')
                         .replace(' (of those with >1 visit)', '\n(of those with >1 visit)').replace(' in 12 months', '\nin 12 months')
                         .replace('without an', 'without an\n') for r in u.index], fontsize=8.6)
    ax.invert_yaxis(); _clean(ax, 100)
    ax.set_xlabel('% of respondents in each group', fontsize=9)
    ax.set_title('B  Pattern of service use', loc='left', fontweight='bold', fontsize=11, color=INK)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False,
              fontsize=8, handlelength=1.1)
    fig.suptitle('How each group reaches and uses care', x=0.005, ha='left',
                 fontweight='bold', fontsize=13, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(f'{FIG}/Figure 3 - Access and utilisation.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def main():
    os.makedirs(FIG, exist_ok=True)
    fig_sampling(); print('  Figure A1 sampling')
    fig_profile(); print('  Figure 1 profile')
    fig_reasons(); print('  Figure 2 reasons')
    fig_utilisation(); print('  Figure 3 access & utilisation')
    fig_preventive(); print('  Figure 4 preventive')
    fig_forest(f'{TAB}/T31_preventive_adjusted.csv', 'private hospital OPD/ER',
               'Preventive services: private hospital users vs public hospital users',
               'Figure A2 - Preventive services adjusted.png',
               note='Adjusted for age band, sex, education, income, municipality, coverage scheme, '
                    'self-rated health and chronic illness; cluster-robust (subdistrict).')
    fig_experience_domains(); print('  Figure 5 experience')
    fig_india(); print('  Figure 7 India')
    allf = []
    for f, fam in [('T54_experience_adjusted', 'Visit experience'),
                   ('T59_core_outcomes_adjusted', 'Care & utilisation'),
                   ('T58_confidence_adjusted', 'System confidence')]:
        e = pd.read_csv(f'{TAB}/{f}.csv'); allf.append(e)
    comb = pd.concat(allf, ignore_index=True)
    comb.to_csv(f'{TAB}/T90_all_adjusted_combined.csv', index=False, encoding='utf-8-sig')
    fig_forest(f'{TAB}/T90_all_adjusted_combined.csv', 'private hospital OPD/ER',
               'What differs for private-hospital users, after adjustment',
               'Figure 6 - Adjusted differences private hospital users.png',
               note='Reference: public hospital OPD/ER. Adjusted for age band, sex, education, income, '
                    'municipality, coverage scheme, self-rated health and chronic illness;\ncluster-robust '
                    '(subdistrict) standard errors. Benjamini-Hochberg adjustment applied within each '
                    'outcome family. pp diff = difference in average predicted probability.')
    print('  Figure 6 overview')


if __name__ == '__main__':
    main()
