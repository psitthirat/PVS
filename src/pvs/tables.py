"""
Reproduce every table in the 2026-09 revision.

    .venv/bin/python -m pvs tables

Inputs : data/survey.xlsx (sheet ส่งงาน), data/data_dict-survey.xlsx,
         data/mappings/*.csv, the Thai report (Table 1) for the planned allocation.
Outputs: output/tables/*.csv  and  results.pkl
No random seed is used: every estimate is deterministic.
"""
from __future__ import annotations
import os, pickle, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')

from . import preparation as prep
from . import audit, sampling, inventory, analysis

from .paths import OUTPUT as OUT
TAB = f'{OUT}/tables'
R = {}


def w(name, df, index=False):
    os.makedirs(TAB, exist_ok=True)
    df.to_csv(f'{TAB}/{name}.csv', index=index, encoding='utf-8-sig')
    R[name] = df
    print(f'  wrote {name}.csv  ({len(df)} rows)')


# ---------------------------------------------------------------- descriptives
def desc_table(df, spec, group='provider_group', groups=None):
    """spec: list of (var, positive, label) or (var, None, label) for a whole distribution."""
    groups = groups or prep.GROUPS
    rows = []
    for var, pos, lab in spec:
        if pos is None:                                   # full distribution
            sub = df[[var, group]].dropna()
            ct = pd.crosstab(sub[var], sub[group]).reindex(columns=groups).fillna(0).astype(int)
            from scipy import stats as st
            try:
                p = st.chi2_contingency(ct)[1]
            except Exception:
                p = np.nan
            rows.append({'Measure': lab, **{g: '' for g in groups}, 'p': _p(p),
                         'Denominator': 'see rows below'})
            for cat in ct.index:
                r = {'Measure': f'    {cat}'}
                for g in groups:
                    k, n = int(ct.loc[cat, g]), int(ct[g].sum())
                    r[g] = f'{k}/{n} ({100*k/n:.1f})' if n else '--'
                r['p'] = ''
                r['Denominator'] = ''
                rows.append(r)
        else:
            cells, p, sparse = analysis.describe_binary(df, var, pos, group, groups)
            r = {'Measure': lab}
            for g in groups:
                r[g] = cells[g]['fmt']
            r['p'] = _p(p) + (' †' if sparse else '')
            r['Denominator'] = prep.RECALL.get(var.replace('_r', '').replace('_ord', ''),
                                               ('most recent visit', ''))[1] or 'all in group'
            rows.append(r)
    return pd.DataFrame(rows)


def _p(p):
    return '--' if p != p else ('<0.001' if p < 0.001 else f'{p:.3f}')


def main():
    R.clear()
    # Check the external sampling input before preparing data or writing results.
    pl = sampling.planned_allocation()
    os.makedirs(TAB, exist_ok=True)
    print('Loading and preparing data …')
    raw_df, clean = prep.load()
    d = prep.build(clean)
    coh, flow = prep.cohort(d)
    d.to_pickle(f'{OUT}/analysis_frame.pkl')
    print(f'  {len(d)} respondents; {len(coh)} in the four-group cohort')

    # ================================================== P0 audit
    print('\nPriority 0 — audit')
    w('T01_cohort_flow', flow)
    w('T02_classification_map', audit.classification_map(d))
    w('T03_usual_vs_last_visit', audit.usual_vs_last(d))
    w('T04_health_coding_impact', audit.health_coding_impact(d, clean))
    w('T05_age_denominator_audit', audit.age_denominator_audit(d))
    w('T06_denominator_rules', audit.denominator_rules(d))
    cc, cc_grp = audit.complete_case_audit(d, analysis.COVARIATES + ['subdist'])
    w('T07_complete_case_audit', cc)
    w('T07b_complete_cases_by_group', cc_grp.rename('n').reset_index())

    # ================================================== sampling
    print('\nPriority 1A — sampling and denominators')
    w('T10_planned_vs_achieved_region', sampling.planned_vs_achieved(d, pl))
    w('T11_quota_audit', sampling.quota_audit(d))
    w('T12_quota_cells', sampling.quota_cells(d).reset_index())
    w('T13_cluster_structure', sampling.cluster_structure(d))
    full = [('sex', 'female', 'Female'), ('sex', 'other', 'Sex: other'),
            ('age_band', None, 'Age band (Q4, complete)'),
            ('area4', None, 'Type of area (Q2, 4 categories)'),
            ('edu', None, 'Education (Q8, 6 levels)'),
            ('income', None, 'Household income (Q51)'),
            ('scheme', None, 'Main public scheme (Q6)'),
            ('priv_ins_owned', 'yes', 'Owns private health insurance (Q7.1)'),
            ('health_good3', 'good or better', 'Self-rated health good or better (CORRECTED)'),
            ('health_top2', 'very good/excellent', 'Self-rated health very good/excellent'),
            ('mental_good3', 'good or better', 'Self-rated mental health good or better'),
            ('chronic', 'yes', 'Chronic condition >= 6 months'),
            ('activation', 'high', 'High patient activation (both Q12 items)'),
            ('activation_strict', 'high', 'Activation, strict rule (very confident on both)'),
            ('has_usual', 'yes', 'Has a usual source of care')]
    w('T14_full_sample_descriptives',
      desc_table(d, full, group='municipality', groups=['municipal', 'non-municipal']))

    # ================================================== inventory
    print('\nPriority 1B — questionnaire inventory')
    w('questionnaire_inventory', inventory.inventory_df(d))
    w('framework_matrix', inventory.framework_matrix(d, coh))
    w('framework_sought_constructs', inventory.sought_constructs_df())

    # ================================================== profile by group
    print('\nFour-group descriptive tables')
    prof = [('age_band', None, 'Age band (Q4, complete for all)'),
            ('sex', None, 'Sex (Q5)'),
            ('municipality', 'municipal', 'Municipal residence'),
            ('edu', None, 'Education (Q8)'),
            ('income', None, 'Household income (Q51)'),
            ('scheme', None, 'Main public scheme (Q6)'),
            ('priv_ins_owned', 'yes', 'Owns private health insurance'),
            ('health_good3', 'good or better', 'Self-rated health good or better'),
            ('mental_good3', 'good or better', 'Mental health good or better'),
            ('chronic', 'yes', 'Chronic condition >= 6 months'),
            ('activation', 'high', 'High patient activation')]
    w('T20_profile_by_group', desc_table(coh, prof))

    # binary profile indicators, for the consolidated report's opening figure
    cb = coh.assign(
        age_u50x=coh['age_u50'],
        edu_hi=prep._bin(coh['edu_gr'].notna(),
                         coh['edu_gr'] == 'upper secondary or above', 'yes', 'no'),
        inc30=prep._bin(coh['income3'].notna(), coh['income3'] == '30k+', 'yes', 'no'))
    w('T24_profile_binary', desc_table(cb, [
        ('age_u50x', 'yes', 'Aged under 50'),
        ('municipality', 'municipal', 'Lives in a municipality'),
        ('edu_hi', 'yes', 'Upper-secondary education or above'),
        ('inc30', 'yes', 'Household income \u0e3f30,000+ / month'),
        ('scheme', 'SSS', 'Social Security (SSS)'),
        ('scheme', 'UCS', 'Universal Coverage (UCS)'),
        ('priv_ins_owned', 'yes', 'Owns private health insurance'),
        ('health_good3', 'good or better', 'Self-rated health good or better'),
        ('chronic', 'yes', 'Chronic condition \u2265 6 months'),
        ('activation', 'high', 'High patient activation')]))

    util = [('visits_cat', None, 'Outpatient visits, past 12 months (Q18)'),
            ('one_facility_multi', 'yes',
             'All visits at one facility (Q20; respondents with >1 visit)'),
            ('admit', 'yes', 'Admitted overnight, past 12 months (Q26)'),
            ('homevisit_any', 'yes', 'Any home visit (Q22)'),
            ('telemed_any', 'yes', 'Any telemedicine (Q23)'),
            ('unmet', 'yes', 'Unmet health-care need (Q29)'),
            ('unmet_reason_lab', None, 'Main reason for unmet need (Q30)'),
            ('borrowed_ever', 'yes', 'Borrowed/sold assets for care, past 12 months (Q31)'),
            ('med_error_ever', 'yes', 'Perceived medical error, ever (Q28a)'),
            ('discrim_ever', 'yes', 'Felt discriminated against, ever (Q28b)'),
            ('last_group', None, 'Provider group at most recent visit (Q32/Q33)'),
            ('last_reason', None, 'Reason for most recent visit (Q34)')]
    w('T21_utilisation_by_group', desc_table(coh, util))

    acc = [('usual_reason', None, 'Main reason for choosing usual source (Q16)'),
           ('appoint', 'appointment', 'Most recent visit by appointment (Q35)'),
           ('queue_cat', None, 'Waiting time at facility (Q37)'),
           ('queue_ge1h', 'yes', 'Waited 1 hour or more (Q37)'),
           ('wait_cat', None, 'Booking-to-appointment wait (Q36, appointment-holders only)'),
           ('wait_ge1mo', 'yes', 'Waited 1 month or more for the appointment (Q36)')]
    w('T22_access_by_group', desc_table(coh, acc))
    w('T25_reasons_binary', desc_table(coh, [
        ('usual_reason', r, l) for r, l in
        [('covered by my insurance scheme', 'Covered by my insurance scheme'),
         ('short waiting time', 'Short waiting time'),
         ('close to home', 'Close to home'),
         ('medicines & equipment', 'Has medicines and equipment'),
         ('low cost', 'Low cost'),
         ('provider skill', 'Provider skill')]]))
    w('T26_utilisation_binary', desc_table(coh, [
        ('appoint', 'walk-in', 'Walked in without an appointment'),
        ('queue_ge1h', 'yes', 'Waited 1 hour or more at the facility'),
        ('one_facility_multi', 'yes', 'Used only one facility (of those with >1 visit)'),
        ('admit', 'yes', 'Admitted overnight in 12 months'),
        ('homevisit_any', 'yes', 'Received a home visit'),
        ('unmet', 'yes', 'Reported an unmet health-care need')]))

    conf = [('conf_get', 'confident', 'Confident of good care if seriously ill (Q41a)'),
            ('conf_afford', 'confident', 'Confident of affording care if seriously ill (Q41b)'),
            ('health_security', 'confident', 'Health security (Q41a AND Q41b)'),
            ('security_state', None, 'Health-security state (four-way decomposition)'),
            ('conf_voice', 'confident', 'Government listens to the public (Q41c)'),
            ('sys_improved_bin', 'improved', 'System improved over 2 years (Q45)'),
            ('sys_endorse_bin', 'works well', 'System works well / minor change only (Q46)'),
            ('q_public_top2', 'very good/excellent', 'Public system quality very good/excellent (Q42)'),
            ('q_private_top2', 'very good/excellent', 'Private system quality very good/excellent (Q43)'),
            ('q_covid_top2', 'very good/excellent', 'Government COVID-19 management (Q47)'),
            ('q_maternal_top2', 'very good/excellent', 'Public maternal care (Q40a)'),
            ('q_child_top2', 'very good/excellent', 'Public child care (Q40b)'),
            ('q_chronic_top2', 'very good/excellent', 'Public chronic care (Q40c)'),
            ('q_mentalhealth_top2', 'very good/excellent', 'Public mental-health care (Q40d)')]
    w('T23_confidence_by_group', desc_table(coh, conf))

    # ============================================ 1D preventive services
    print('\nPriority 1D — preventive services by provider group')
    screen_all = [('bp_r', 'yes', 'Blood pressure measured (Q27A)'),
                  ('sugar_r', 'yes', 'Blood sugar tested (Q27F)'),
                  ('lipid_r', 'yes', 'Blood lipids tested (Q27G)'),
                  ('dental_r', 'yes', 'Dental examination (Q27E)'),
                  ('vision_r', 'yes', 'Vision check (Q27D)'),
                  ('mental_r', 'yes', 'Mental-health service received (Q27H)')]
    screen_fem = [('mammogram_r', 'yes', 'Breast examination/mammogram (Q27B) — women only'),
                  ('ca_cervix_r', 'yes', 'Cervical screening (Q27C) — women only')]
    w('T30_preventive_descriptive', desc_table(coh, screen_all))
    fem = coh[coh['sex'] == 'female']
    w('T30b_preventive_descriptive_women', desc_table(fem, screen_fem))
    w('T30c_screening_by_sex_all_respondents',
      desc_table(d, [('mammogram_r', 'yes', 'Breast examination/mammogram (Q27B)'),
                     ('ca_cervix_r', 'yes', 'Cervical screening (Q27C)')],
                 group='sex', groups=['male', 'female', 'other']))
    E1, N1 = analysis.run_family(coh, screen_all, 'Preventive services (all respondents)')
    # sex is constant among women, so it is dropped from the covariate set
    E2, N2 = analysis.run_family(fem, screen_fem, 'Preventive services (women only)',
                                 covariates=analysis.COV_FORMULA_NO_SEX)
    Eprev = pd.concat([E1, E2], ignore_index=True)
    w('T31_preventive_adjusted', Eprev)
    w('T32_preventive_model_notes', pd.concat([N1, N2], ignore_index=True))

    # private clinic vs pharmacy heterogeneity inside "private clinic/pharmacy"
    sub = coh.copy()
    sub['provider_group5'] = sub['provider_group'].astype('object')
    sub.loc[sub['private_primary_sub'] == 'pharmacy', 'provider_group5'] = 'private pharmacy'
    sub.loc[sub['private_primary_sub'] == 'clinic', 'provider_group5'] = 'private clinic'
    g5 = ['public primary care', 'public hospital OPD/ER', 'private clinic',
          'private pharmacy', 'private hospital OPD/ER']
    w('T33_preventive_clinic_vs_pharmacy',
      desc_table(sub, screen_all, group='provider_group5', groups=g5))

    # five-group analysis including people with NO usual source, kept separate
    alt = d.copy()
    alt['group_incl_none'] = alt['provider_group'].astype('object')
    alt.loc[alt['has_usual'] == 'no', 'group_incl_none'] = 'no usual source of care'
    gi = prep.GROUPS + ['no usual source of care']
    w('T34_preventive_incl_no_usual_source',
      desc_table(alt[alt['group_incl_none'].notna()], screen_all,
                 group='group_incl_none', groups=gi))

    # ============================================ 1C activation
    print('\nPriority 1C — patient activation (NOT literacy)')
    act = [('act_selfcare', 'confident', 'Q12a: confident managing own health'),
           ('act_voice', 'confident', 'Q12b: confident voicing concerns unprompted'),
           ('activation', 'high', 'Activation indicator (project rule: confident on both)'),
           ('activation_strict', 'high', 'Activation, strict (very confident on both)')]
    w('T40_activation_by_group', desc_table(coh, act))
    w('T40b_activation_components_full_sample',
      desc_table(d, act, group='municipality', groups=['municipal', 'non-municipal']))
    act_out = [('bp_r', 'yes', 'Blood pressure measured'),
               ('sugar_r', 'yes', 'Blood sugar tested'),
               ('unmet', 'yes', 'Unmet health-care need'),
               ('usual_qual_top2', 'very good/excellent', 'Rates usual facility very good/excellent'),
               ('health_security', 'confident', 'Health security')]
    rows = []
    for col, pos, lab in act_out:
        dd = coh.dropna(subset=[col, 'activation', 'subdist'] + analysis.COVARIATES).copy()
        dd['y'] = (dd[col] == pos).astype(int)
        import statsmodels.formula.api as smf
        f = ('y ~ C(activation, Treatment(reference="not high"))'
             + analysis.COV_FORMULA
             + ' + C(provider_group, Treatment(reference="public hospital OPD/ER"))')
        try:
            m = smf.logit(f, data=dd).fit(disp=0, maxiter=200,
                                          cov_type='cluster',
                                          cov_kwds={'groups': dd['subdist'].astype('category').cat.codes})
            i = [k for k, nm in enumerate(m.params.index) if nm.startswith('C(activation')][0]
            b, se = float(np.asarray(m.params)[i]), float(np.asarray(m.bse)[i])
            rows.append({'Outcome': lab, 'aOR (high vs not high activation)': np.exp(b),
                         'lo': np.exp(b - 1.96*se), 'hi': np.exp(b + 1.96*se),
                         'p': float(np.asarray(m.pvalues)[i]), 'n': int(m.nobs)})
        except Exception as e:
            rows.append({'Outcome': lab, 'aOR (high vs not high activation)': np.nan,
                         'lo': np.nan, 'hi': np.nan, 'p': np.nan, 'n': 0})
    A = pd.DataFrame(rows)
    A['p (BH)'] = analysis.bh(A['p'].values)
    w('T41_activation_associations', A)

    # does adding activation change the provider-group contrasts?
    base, _ = analysis.run_family(coh, [('usual_qual_top2', 'very good/excellent',
                                         'Rates usual facility very good/excellent')],
                                  'Quality (without activation)')
    plus, _ = analysis.run_family(coh, [('usual_qual_top2', 'very good/excellent',
                                         'Rates usual facility very good/excellent')],
                                  'Quality (with activation)',
                                  extra_terms=' + C(activation, Treatment(reference="not high"))')
    cmp_ = base[['Group', 'aOR', 'lo', 'hi', 'p']].merge(
        plus[['Group', 'aOR', 'lo', 'hi', 'p']], on='Group',
        suffixes=(' — without activation', ' — with activation'))
    w('T42_activation_adjustment_effect', cmp_)

    # ============================================ 1E quality and confidence
    print('\nPriority 1E — meaning of quality, and its relation to confidence')
    exp_spec, exp_rows = [], []
    for col, lab in prep.EXP_ITEMS.items():
        exp_spec.append((col + '_top2', 'very good/excellent',
                         f'{prep.EXP_DOMAIN[col]} — {lab}'))
    w('T50_experience_by_usual_group', desc_table(coh, exp_spec))
    # the same items attributed to the ACTUAL last-visit provider
    lv = coh[coh['last_group'].notna()]
    w('T51_experience_by_last_visit_provider',
      desc_table(lv, exp_spec, group='last_group'))
    # sensitivity: only respondents whose usual and last-visit group agree
    conc = coh[coh['concordant_group'] == 'yes']
    w('T52_experience_concordant_only', desc_table(conc, exp_spec))
    w('T52b_concordance_sample_sizes',
      pd.DataFrame({'Provider group': prep.GROUPS,
                    'Four-group cohort n': [int((coh['provider_group'] == g).sum()) for g in prep.GROUPS],
                    'Concordant n': [int((conc['provider_group'] == g).sum()) for g in prep.GROUPS],
                    'Last-visit-based n': [int((lv['last_group'] == g).sum()) for g in prep.GROUPS]}))
    # structural not-applicable rates, so the reader sees the denominators move
    na_rows = []
    for col, na_lab in prep.EXP_NA_LABEL.items():
        r = {'Item': prep.EXP_ITEMS[col], 'Not-applicable answer': na_lab}
        for g in prep.GROUPS:
            sg = coh[coh['provider_group'] == g]
            k = int(sg[col + '_na'].sum())
            r[g] = f'{k}/{len(sg)} ({100*k/len(sg):.1f})'
        na_rows.append(r)
    for col, lab in [('q_maternal', 'Q40a maternal'), ('q_child', 'Q40b child'),
                     ('q_chronic', 'Q40c chronic'), ('q_mentalhealth', 'Q40d mental health')]:
        r = {'Item': lab, 'Not-applicable answer': 'cannot evaluate'}
        for g in prep.GROUPS:
            sg = coh[coh['provider_group'] == g]
            k = int(sg[col + '_cannot_eval'].sum())
            r[g] = f'{k}/{len(sg)} ({100*k/len(sg):.1f})'
        na_rows.append(r)
    w('T53_structural_not_applicable', pd.DataFrame(na_rows))

    exp_model = [(c + '_top2', 'very good/excellent', f'{prep.EXP_DOMAIN[c]} — {l}')
                 for c, l in prep.EXP_ITEMS.items()]
    Eexp, Nexp = analysis.run_family(coh, exp_model, 'Visit experience (11 items)')
    w('T54_experience_adjusted', Eexp)
    w('T54b_experience_model_notes', Nexp)

    # health security decomposed, and its relation to rating your own provider
    w('T55_security_decomposition',
      desc_table(coh, [('security_state', None, 'Health-security state')]))
    sec = coh.dropna(subset=['health_security', 'usual_qual_top2'])
    ct = pd.crosstab(sec['usual_qual_top2'], sec['health_security'], margins=True,
                     margins_name='All')
    w('T56_own_provider_rating_x_health_security', ct.reset_index())
    both = []
    for g in prep.GROUPS:
        sg = sec[sec['provider_group'] == g]
        hi = sg['usual_qual_top2'] == 'very good/excellent'
        ins = sg['health_security'] == 'not confident'
        both.append({'Provider group': g, 'n': len(sg),
                     'Rates own facility very good/excellent, %': round(100*hi.mean(), 1),
                     'Health-insecure, %': round(100*ins.mean(), 1),
                     'Rates provider highly BUT health-insecure, n (%)':
                         f'{int((hi & ins).sum())} ({100*(hi & ins).mean():.1f})'})
    w('T57_high_rating_but_insecure', pd.DataFrame(both))
    Econf, Nconf = analysis.run_family(
        coh, [('health_security', 'confident', 'Health security'),
              ('conf_get', 'confident', 'Confident of good care if seriously ill'),
              ('conf_afford', 'confident', 'Confident of affording care'),
              ('sys_improved_bin', 'improved', 'System improved over 2 years'),
              ('sys_endorse_bin', 'works well', 'System works well / minor change'),
              ('q_public_top2', 'very good/excellent', 'Public system quality high'),
              ('q_private_top2', 'very good/excellent', 'Private system quality high'),
              ('conf_voice', 'confident', 'Government listens to the public')],
        'System confidence')
    w('T58_confidence_adjusted', Econf)
    Ecore, Ncore = analysis.run_family(
        coh, [('usual_qual_top2', 'very good/excellent', 'Rates usual facility very good/excellent'),
              ('promoter', 'yes', 'Would recommend provider (0-10 score 9-10)'),
              ('queue_ge1h', 'yes', 'Waited 1 hour or more at the facility'),
              ('admit', 'yes', 'Admitted overnight, past 12 months'),
              ('unmet', 'yes', 'Unmet health-care need'),
              ('med_error_ever', 'yes', 'Perceived a medical error (ever)'),
              ('discrim_ever', 'yes', 'Felt discriminated against (ever)'),
              ('one_facility_multi', 'yes', 'All visits at one facility (>1 visit only)')],
        'Care experience and utilisation')
    w('T59_core_outcomes_adjusted', Ecore)
    w('T59b_core_model_notes', pd.concat([Nconf, Ncore], ignore_index=True))

    # admission: does adding need change it, and does the analytic sample change?
    adm_rows = []
    for lab, extra, cov in [
            ('Base specification', '', analysis.COV_FORMULA),
            ('+ chronic illness already in base (shown for clarity)', '', analysis.COV_FORMULA),
            ('+ unmet need and visit volume', ' + C(unmet, Treatment(reference="no"))'
             ' + C(visits_cat, Treatment(reference="1-2"))', analysis.COV_FORMULA)]:
        fitted, err, ev = analysis.fit_group_model(coh, 'admit', 'yes',
                                                   extra_terms=extra, covariates=cov)
        if err:
            adm_rows.append({'Specification': lab, 'Group': '--', 'aOR': np.nan,
                             'lo': np.nan, 'hi': np.nan, 'p': np.nan, 'n': 0, 'note': err})
            continue
        for r in analysis.group_contrasts(fitted, 'Admitted overnight'):
            adm_rows.append({'Specification': lab, 'Group': r['Group'], 'aOR': r['aOR'],
                             'lo': r['lo'], 'hi': r['hi'], 'p': r['p'],
                             'Diff (pp)': r['Diff (pp)'], 'n': r['n'], 'note': ''})
    w('T60_admission_sensitivity', pd.DataFrame(adm_rows))

    # ============================================ 1F personas and financing
    print('\nPriority 1F — observed profiles of private-hospital users')
    ph = coh[coh['provider_group'] == 'private hospital OPD/ER'].copy()
    # What IS and IS NOT measured about money
    w('T70_financing_items_available', pd.DataFrame([
        {'Concept': 'Public scheme eligibility/ownership (Q6)', 'Measured?': 'YES',
         'Variable': 'scheme', 'Caveat': 'Ownership of an entitlement, not use of it'},
        {'Concept': 'Private insurance ownership (Q7.1)', 'Measured?': 'YES',
         'Variable': 'priv_ins_owned', 'Caveat': 'Ownership only; never linked to an encounter'},
        {'Concept': 'Employer-purchased insurance (Q7.2)', 'Measured?': 'YES',
         'Variable': 'employer_ins_owned', 'Caveat': 'Ownership only'},
        {'Concept': 'Pays out of pocket in some situations (Q7.4)', 'Measured?': 'PARTIAL',
         'Variable': 'insr_oop', 'Caveat': 'General habit, not a specific encounter or amount'},
        {'Concept': 'Registered / contracted provider', 'Measured?': 'NO',
         'Variable': '--', 'Caveat': 'Cannot establish that SSS members were assigned to their provider'},
        {'Concept': 'Payer at the most recent visit', 'Measured?': 'NO',
         'Variable': '--', 'Caveat': "The reviewer's payment question is unanswerable with these data"},
        {'Concept': 'Out-of-pocket amount / copayment', 'Measured?': 'NO', 'Variable': '--',
         'Caveat': 'No expenditure item anywhere in the instrument'},
        {'Concept': 'Employment status', 'Measured?': 'NO', 'Variable': '--',
         'Caveat': 'SSS membership is not evidence of current salaried employment'},
        {'Concept': 'Borrowed/sold assets for care, past 12 months (Q31)', 'Measured?': 'YES',
         'Variable': 'borrowed_ever', 'Caveat': 'Past 12 months; not attributed to any provider'},
    ]))
    # coverage ownership crossed with private insurance — an OVERLAP table, not personas
    ov = pd.crosstab(ph['scheme_gr'], ph['priv_ins_owned'], margins=True, margins_name='All')
    w('T71_private_hospital_users_coverage_overlap', ov.reset_index())
    # observed profiles (declared, not clustered)
    profiles = {
        'SSS member, no private insurance': (ph['scheme_gr'] == 'SSS') & (ph['priv_ins_owned'] == 'no'),
        'SSS member, also owns private insurance': (ph['scheme_gr'] == 'SSS') & (ph['priv_ins_owned'] == 'yes'),
        'UCS member': ph['scheme_gr'] == 'UCS',
        'CSMBS member': ph['scheme_gr'] == 'CSMBS',
    }
    rows = []
    for lab, mask in profiles.items():
        g = ph[mask]
        n = len(g)
        if n == 0:
            continue
        def pc(col, val):
            s = g[col].dropna()
            return f'{int((s == val).sum())}/{len(s)} ({100*(s == val).mean():.0f})' if len(s) else '--'
        rows.append({'Profile': lab, 'n': n, '% of private-hospital users': round(100*n/len(ph), 1),
                     'Median age band': g['age_band'].astype('object').mode().iat[0] if n else '--',
                     'Female': pc('sex', 'female'), 'Municipal': pc('municipality', 'municipal'),
                     'Upper-secondary +': pc('edu_gr', 'upper secondary or above'),
                     'Income 30k+': pc('income3', '30k+'),
                     'Chose provider for insurance coverage': pc('usual_reason', 'covered by my insurance scheme'),
                     'Chose provider for short wait': pc('usual_reason', 'short waiting time'),
                     'Admitted overnight': pc('admit', 'yes'),
                     'Unmet need': pc('unmet', 'yes'),
                     'Borrowed for care (past 12 months)': pc('borrowed_ever', 'yes'),
                     'Rates facility very good/excellent': pc('usual_qual_top2', 'very good/excellent'),
                     'High activation': pc('activation', 'high'),
                     'Health secure': pc('health_security', 'confident')})
    w('T72_private_hospital_observed_profiles', pd.DataFrame(rows))
    # boundary: regular users vs anyone whose LAST visit was a private hospital
    boundary = []
    a = d[d['provider_group'] == 'private hospital OPD/ER']
    b = d[d['last_group'] == 'private hospital OPD/ER']
    both_m = d[(d['provider_group'] == 'private hospital OPD/ER') &
               (d['last_group'] == 'private hospital OPD/ER')]
    for lab, g in [('Usual source is a private hospital (regular users)', a),
                   ('Most recent visit was to a private hospital', b),
                   ('Both', both_m)]:
        boundary.append({'Definition': lab, 'n': len(g),
                         'SSS %': round(100*(g['scheme_gr'] == 'SSS').mean(), 1),
                         'Owns private insurance %': round(100*(g['priv_ins_owned'] == 'yes').mean(), 1),
                         'Admitted overnight %': round(100*(g['admit'] == 'yes').mean(), 1)})
    boundary.append({'Definition': 'NOTE', 'n': '',
                     'SSS %': 'Episodic private-hospital use during the recall period is NOT measurable:',
                     'Owns private insurance %': 'Q32/Q33 capture only the single most recent visit,',
                     'Admitted overnight %': 'and Q26 never records where an admission occurred.'})
    w('T73_private_user_population_boundary', pd.DataFrame(boundary))

    # ============================================ 1G Thailand vs India
    print('\nPriority 1G — Thailand vs India health security')
    kruk = {  # Kruk et al. 2024 Lancet Glob Health, Figure 2A (see supplement §G)
        'Can get good-quality care': {'India': 84.1, '15-country average': 70.7},
        'Can afford care when needed': {'India': 76.4, '15-country average': 56.7},
        'Health security (can get AND afford)': {'India': 69.2, '15-country average': 48.8},
    }
    ours = {
        'Can get good-quality care': 100*(d['conf_get'] == 'confident').mean(),
        'Can afford care when needed': 100*(d['conf_afford'] == 'confident').mean(),
        'Health security (can get AND afford)': 100*(d['health_security'] == 'confident').mean(),
    }
    rows = []
    for k, v in kruk.items():
        n_obs = int(d[{'Can get good-quality care': 'conf_get',
                       'Can afford care when needed': 'conf_afford',
                       'Health security (can get AND afford)': 'health_security'}[k]].notna().sum())
        kk = int(round(ours[k]/100*n_obs))
        pct, lo, hi = analysis.prop_ci(kk, n_obs)
        rows.append({'Indicator': k,
                     'Thailand (this survey), % (95% CI)': f'{pct:.1f} ({lo:.1f}-{hi:.1f})',
                     'Thailand n': n_obs,
                     'India (Kruk 2024), %': v['India'],
                     '15-country average, %': v['15-country average'],
                     'Thailand minus India (pp)': round(pct - v['India'], 1),
                     'Thailand minus average (pp)': round(pct - v['15-country average'], 1)})
    w('T80_thailand_india_indicators', pd.DataFrame(rows))
    w('T81_comparability_checklist', pd.DataFrame([
        {'Dimension': 'Indicator definition', 'Thailand (this survey)':
            'Q41a/Q41b, "if you were seriously ill"; somewhat or very confident',
         'India (PVS round 1)': 'Same two-item PVS construct, per Kruk et al. Figure 2A',
         'Verified?': 'Yes — item wording checked against the fielded Thai instrument and the PVS paper'},
        {'Dimension': 'Age eligibility', 'Thailand (this survey)': '18+ (Q3 screens out under-18s)',
         'India (PVS round 1)': 'Not verified from the paper text available here', 'Verified?': 'NO'},
        {'Dimension': 'Geographic coverage', 'Thailand (this survey)':
            '13 health regions, ONE province sampled per region',
         'India (PVS round 1)': 'Not verified', 'Verified?': 'NO'},
        {'Dimension': 'Fieldwork dates', 'Thailand (this survey)':
            'See survey start/end fields in the raw export',
         'India (PVS round 1)': 'Not verified', 'Verified?': 'NO'},
        {'Dimension': 'Survey mode', 'Thailand (this survey)': 'In-person interview',
         'India (PVS round 1)': 'PVS permits phone/online/in-person; country mode not verified',
         'Verified?': 'NO'},
        {'Dimension': 'Weighting', 'Thailand (this survey)': 'None — unweighted achieved sample',
         'India (PVS round 1)': 'PVS country estimates are described as population-representative',
         'Verified?': 'NO'},
        {'Dimension': 'Language / translation', 'Thailand (this survey)': 'Thai',
         'India (PVS round 1)': 'Not verified', 'Verified?': 'NO'},
        {'Dimension': 'Uncertainty', 'Thailand (this survey)': 'Wilson 95% CI reported here',
         'India (PVS round 1)': 'No CI available from the figure', 'Verified?': 'NO'},
    ]))

    print('\nTarget-population segmentation')
    from . import segments
    segments.main()

    with open(f'{OUT}/results.pkl', 'wb') as fh:
        pickle.dump(R, fh)
    print(f'\nDone. {len(R)} tables in {TAB}/')
    return d, coh, raw_df, clean


if __name__ == '__main__':
    main()
