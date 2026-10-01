"""
Canonical data preparation for the 2026-09 revision of the PVS Thailand analysis.

Everything downstream (audit, tables, figures, models, reports) is built from
`build()`, so no number is typed independently anywhere.

Design decisions, all deliberate and documented in
archive/legacy/output/revision_2026-09/correction_and_limitations_log.md:

* Refusal codes are missing, not categories.   Q5 "999. ปฏิเสธตอบ" was previously
  mapped to the literal string "999" and entered tables as a sex category.
* Self-rated health keeps its ordinal form.    map_health_level.csv assigns
  "3. ดีมาก" (very good) to `bad`. Every dichotomy is now named and explicit.
* Age uses the fully-observed band (Q4).       Q3 exact age is missing for 308 of
  2,017; Q4 is complete. Exact-age summaries carry their own denominator.
* Recall periods are attached to variables.    Several items ("ที่ผ่านมา", "เคย")
  carry no recall window at all; see RECALL.
* Screening items keep sex-specific denominators and an unverified-wording flag.
"""
from __future__ import annotations
import os, warnings
import pandas as pd, numpy as np

warnings.filterwarnings('ignore')
from .paths import DATA, OUTPUT
SHEET = 'ส่งงาน'

# --------------------------------------------------------------------------
# Provider groups
# --------------------------------------------------------------------------
# Descriptive labels only. Q15 distinguishes hospital OPD/ER from non-hospital
# settings; it does NOT establish secondary vs tertiary, so "secondary" is gone.
GROUPS = ['public primary care', 'public hospital OPD/ER',
          'private clinic/pharmacy', 'private hospital OPD/ER']
GROUP_SHORT = {'public primary care': 'Public\nprimary care',
               'public hospital OPD/ER': 'Public hospital\nOPD/ER',
               'private clinic/pharmacy': 'Private clinic\n/pharmacy',
               'private hospital OPD/ER': 'Private hospital\nOPD/ER'}

_SETTING = {'1.': 'health centre/รพ.สต.', '2.': 'family-doctor clinic',
            '3.': 'clinic outside hospital', '4.': 'pharmacy',
            '5.': 'hospital ER', '6.': 'hospital OPD', '7.': 'other'}
# 1-4 are non-hospital settings, 5-6 are hospital OPD/ER, 7 ("other") is unclassifiable.
_SETTING_IS_HOSPITAL = {'1.': False, '2.': False, '3.': False, '4.': False,
                        '5.': True, '6.': True}
_SECTOR = {'1.': 'public', '2.': 'private', '3.': 'non-profit', '4.': 'other'}

# --------------------------------------------------------------------------
# Recall period / universe of each analysed item. Q27/Q29/Q31 use 12 months,
# confirmed by the researcher against the original questionnaire on 2026-10-01.
# Abbreviated spreadsheet headers omit that stem; see content/questionnaire/.
# "none stated" is a finding, not an omission on our part.
# --------------------------------------------------------------------------
RECALL = {
    'mhos':        ('past 12 months', 'all respondents'),
    'mhos_type':   ('past 12 months', 'Q13 = yes'),
    'fhos_type':   ('past 12 months', 'Q13 = yes'),
    'fhos_reason': ('n/a (choice of usual source)', 'Q13 = yes'),
    'fhos_qual':   ('past 12 months', 'Q13 = yes'),
    'provider_n':  ('past 12 months (stated in Q19; Q18 header omits it)',
                    'all; EXCLUDES inpatient nights, telemedicine, self-care, pharmacy purchases'),
    'provider_n_facility': ('past 12 months',
                            'fielded to everyone with Q18 >= 1 (Q18 is complete in the cohort); '
                            'the analysis restricts to Q18 > 1'),
    'homevisit_n': ('past 12 months', 'all respondents'),
    'telemed_n':   ('past 12 months', 'all respondents'),
    'admit':       ('past 12 months', 'all respondents'),
    'bp':          ('past 12 months', 'all respondents'),
    'sugar':       ('past 12 months', 'all respondents'),
    'lipid':       ('past 12 months', 'all respondents'),
    'mammogram':   ('past 12 months', 'asked of all; item wording unverified'),
    'ca_cervix':   ('past 12 months', 'asked of all; item wording unverified'),
    'vision':      ('past 12 months', 'all respondents'),
    'dental':      ('past 12 months', 'all respondents'),
    'mental':      ('past 12 months', 'all respondents'),
    'exp_medicalerr': ('NONE STATED ("เคย" = ever)', 'all; NO facility attribution'),
    'exp_injustice':  ('NONE STATED ("เคย" = ever)', 'all; NO facility attribution'),
    'unmet_need':     ('past 12 months', 'all respondents'),
    'unmet_reason':   ('past 12 months', 'Q29 = yes'),
    'unmet_financial':('past 12 months', 'all respondents'),
    'lastest':        ('NONE STATED (most recent visit, unbounded)', 'all respondents'),
    'lastest_type':   ('NONE STATED', 'all respondents'),
    'lastest_appoint':('most recent visit', 'all respondents'),
    'lastest_waiting':('most recent visit', 'Q35 = made an appointment — structural skip'),
    'lastest_queue':  ('most recent visit', 'all respondents'),
    'lastest_suggest':('most recent visit', 'all respondents'),
}
# Q38.1-.10 + Q38 stem all describe the most recent visit, asked of all respondents.
EXP_ITEMS = {
    'lastest_qual':          'Overall experience',
    'lastest_knowledge':     'Provider knowledge and skill',
    'lastest_readiness':     'Equipment and supplies ready',
    'lastest_respect':       'Treated with respect',
    'lastest_data_pre':      'Provider knew my history',
    'lastest_inform':        'Explained things clearly',
    'lastest_engage':        'Involved me in decisions',
    'lastest_duration':      'Enough time in the consultation',
    'lastest_sat-queue':     'Satisfaction with waiting time',
    'lastest_polite':        'Courtesy of staff',
    'lastest_queue-appoint': 'Ease of getting an appointment',
}
# Interpretive grouping (NOT a validated scale — see analytical supplement).
EXP_DOMAIN = {
    'lastest_queue-appoint': 'Access & process', 'lastest_sat-queue': 'Access & process',
    'lastest_duration': 'Access & process',
    'lastest_respect': 'Interpersonal', 'lastest_polite': 'Interpersonal',
    'lastest_inform': 'Interpersonal', 'lastest_engage': 'Interpersonal',
    'lastest_knowledge': 'Perceived competence & readiness',
    'lastest_readiness': 'Perceived competence & readiness',
    'lastest_data_pre': 'Continuity',
    'lastest_qual': 'Global rating',
}
SCALE5 = {'แย่': 0, 'พอใช้': 1, 'ดี': 2, 'ดีมาก': 3, 'ดีเยี่ยม': 4}   # 0..4
# Q38 offers two extra codes that are NOT ratings and NOT item non-response:
#   item e ("provider knew my previous results") -> "5. no prior visit / don't know"
#   item j ("courtesy of OTHER staff")           -> "6. no other staff present"
# They are structural inapplicability and are reported as their own category.
EXP_NA_CODE = {'lastest_data_pre': 'ไม่มีประวัติการมาตรวจมาก่อน/ไม่ทราบ (เฉพาะข้อ e)',
               'lastest_polite':   'ไม่มีเจ้าหน้าที่อื่น (เฉพาะข้อ j)'}
EXP_NA_LABEL = {'lastest_data_pre': 'no prior visit / did not know',
                'lastest_polite':   'no other staff involved'}
# Q40 (public primary care quality) offers "5. cannot evaluate".
Q40_NA_CODE = 'ไม่สามารถประเมินได้'
YESNO = {'ได้รับ': 'yes', 'ไม่ได้รับ': 'no'}
SCREENING = ['bp', 'sugar', 'lipid', 'mental', 'dental', 'vision', 'mammogram', 'ca_cervix']
# Items whose Q27 sub-item wording is NOT recoverable from available files.
SCREENING_SEX_RESTRICTED = ['mammogram', 'ca_cervix']


def load(verbose=False):
    """Clean the raw export with the project pipeline, bypassing its input() prompt."""
    from .cleaning import DataHandler, DataCleaning

    raw = pd.read_excel(DATA / 'survey.xlsx', sheet_name=SHEET)
    dict_path = DataHandler.create_dictionary(raw, 'survey', str(DATA))
    df = DataCleaning.update_column_name(raw, dict_path)
    df, _ = DataCleaning.update_column_type(df, str(DATA), 'survey',
                                            str(OUTPUT), export_df=False)
    df = DataCleaning.remove_duplicates(df, keep='last')
    return raw, df


def _bin(valid, cond, yes, no, index=None):
    """np.where that yields NaN where `valid` is False, without dtype promotion errors."""
    idx = index if index is not None else valid.index
    out = pd.Series(np.nan, index=idx, dtype='object')
    v = valid.fillna(False).astype(bool)
    out.loc[v] = np.where(cond.reindex(idx).fillna(False).astype(bool)[v], yes, no)
    return out


def _pfx(series):
    """Leading '<n>.' option code of a Thai response label."""
    return series.astype('object').where(series.notna()).str.slice(0, 2)


def build(df):
    """Return the analysis frame. Every derived variable is documented inline."""
    d = df.copy()

    # ---------------- geography / design ----------------
    # Q2 has FOUR options: 1 city municipality/Bangkok/Pattaya, 2 town municipality,
    # 3 subdistrict municipality, 4 outside any municipality. The planned allocation
    # is municipal vs non-municipal, so 1-3 collapse to "municipal".
    d['area4'] = _pfx(d['area']).map(
        {'1.': 'city municipality / Bangkok / Pattaya', '2.': 'town municipality',
         '3.': 'subdistrict municipality', '4.': 'outside municipality'})
    d['municipality'] = _pfx(d['area']).map({'1.': 'municipal', '2.': 'municipal',
                                             '3.': 'municipal', '4.': 'non-municipal'})
    # hregion_no is the questionnaire-set number, NOT the health region.
    d['region_no'] = d['hregion'].astype('object').str.extract(r'เขตสุขภาพที่\s*(\d+)')[0].astype(float)
    d['region'] = d['hregion'].astype('object')
    d['province'] = d['prov'].astype('object')

    # ---------------- sex / gender ----------------
    # Q5 offers male / female / other / refused. Refusal is missing data.
    d['sex'] = _pfx(d['gender']).map({'0.': 'male', '1.': 'female', '2.': 'other'})
    d['sex_refused'] = _pfx(d['gender']).eq('999'[:2])   # '99' prefix of '999. ปฏิเสธตอบ'
    d.loc[d['gender'].astype('object').str.startswith('999', na=False), 'sex'] = np.nan

    # ---------------- age ----------------
    # Q4 band is complete for all 2,017; Q3 exact age is missing for 308.
    d['age_exact'] = pd.to_numeric(d['age'], errors='coerce')
    d['age_band'] = _pfx(d['age_range']).map(
        {'1.': '18-29', '2.': '30-39', '3.': '40-49', '4.': '50-59',
         '5.': '60-69', '6.': '70-79', '7.': '80+'})
    d['age_band'] = pd.Categorical(
        d['age_band'], categories=['18-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80+'],
        ordered=True)
    # Band-compatible coarse grouping usable for every respondent.
    d['age_cat4'] = pd.Categorical(
        d['age_band'].map({'18-29': '18-29', '30-39': '30-49', '40-49': '30-49',
                           '50-59': '50-59', '60-69': '60+', '70-79': '60+', '80+': '60+'}),
        categories=['18-29', '30-49', '50-59', '60+'], ordered=True)
    d['age_u50'] = _bin(~d['age_band'].isna(), d['age_band'].isin(['18-29', '30-39', '40-49']), 'yes', 'no')
    d['age_quota'] = _bin(~d['age_band'].isna(), d['age_band'].isin(['60-69', '70-79', '80+']), '60+', '18-59')

    # ---------------- socio-economic ----------------
    # Q8 offers SIX levels. (The project map collapses 4+5 into one "high school"
    # category; kept separate here and collapsed explicitly where needed.)
    _EDU = {'1.': 'below primary', '2.': 'primary', '3.': 'lower secondary',
            '4.': 'upper secondary/voc', '5.': 'diploma/high voc', '6.': 'bachelor or above'}
    d['edu'] = pd.Categorical(_pfx(d['edu']).map(_EDU), categories=list(_EDU.values()), ordered=True)
    d['edu_gr'] = _bin(d['edu'].notna(),
                       d['edu'].isin(['upper secondary/voc', 'diploma/high voc',
                                      'bachelor or above']),
                       'upper secondary or above', 'lower secondary or below')
    d['income'] = _pfx(d['income']).map({'1.': '<10k', '2.': '10-30k', '3.': '30-60k',
                                         '4.': '60-100k', '5.': '100k+'})
    d['income'] = pd.Categorical(d['income'], categories=['<10k', '10-30k', '30-60k',
                                                          '60-100k', '100k+'], ordered=True)
    d['income3'] = pd.Categorical(
        d['income'].map({'<10k': '<10k', '10-30k': '10-30k', '30-60k': '30k+',
                         '60-100k': '30k+', '100k+': '30k+'}),
        categories=['<10k', '10-30k', '30k+'], ordered=True)

    # ---------------- coverage (ownership, NOT payment) ----------------
    # Q6 "999. ไม่ทราบ" (n=20) is a don't-know response, not a scheme.
    d['scheme'] = _pfx(d['insr']).map({'1.': 'UCS', '2.': 'SSS', '3.': 'CSMBS', '4.': 'other public'})
    d['scheme_dk'] = d['insr'].astype('object').str.startswith('999', na=False)
    # "other public" n=1 and don't-know n=20 are pooled for modelling only.
    d['scheme_gr'] = d['scheme'].where(d['scheme'].isin(['UCS', 'SSS', 'CSMBS']),
                                       'other/don\'t know')
    # Q7 is a multi-response supplementary-coverage block: ownership only.
    d['priv_ins_owned'] = np.where(d['insr_private'].notna(), 'yes', 'no')
    d['employer_ins_owned'] = np.where(d['insr_employer'].notna(), 'yes', 'no')

    # ---------------- health status ----------------
    # Ordinal retained; every dichotomy named. See correction log C-02.
    d['health_ord'] = _pfx(d['health_level']).map({'0.': 0, '1.': 1, '2.': 2, '3.': 3, '4.': 4})
    d['mental_ord'] = _pfx(d['mental_level']).map({'0.': 0, '1.': 1, '2.': 2, '3.': 3, '4.': 4})
    for src, out in [('health_ord', 'health'), ('mental_ord', 'mental')]:
        d[f'{out}_good3'] = _bin(~d[src].isna(), d[src] >= 2, 'good or better', 'fair or poor')
        d[f'{out}_top2'] = _bin(~d[src].isna(), d[src] >= 3, 'very good/excellent', 'good or worse')
    d['chronic'] = _pfx(d['illness_6mo']).map({'0.': 'no', '1.': 'yes'})

    # ---------------- activation (NOT literacy — see supplement §C) ----------------
    d['act_selfcare_ord'] = _pfx(d['confidence_selfcare']).map({'0.': 0, '1.': 1, '2.': 2, '3.': 3})
    d['act_voice_ord'] = _pfx(d['confidence_selfreport']).map({'0.': 0, '1.': 1, '2.': 2, '3.': 3})
    # Project rule: "confident" on BOTH items (top-2 of 4 on each).
    for a, b in [('act_selfcare_ord', 'act_selfcare'), ('act_voice_ord', 'act_voice')]:
        d[b] = _bin(~d[a].isna(), d[a] >= 2, 'confident', 'not confident')
    both = d[['act_selfcare_ord', 'act_voice_ord']].notna().all(axis=1)
    d['activation'] = _bin(both, (d['act_selfcare_ord'] >= 2) & (d['act_voice_ord'] >= 2),
                           'high', 'not high')
    # Stricter variant: "very confident" on both (top box).
    d['activation_strict'] = _bin(both, (d['act_selfcare_ord'] == 3) & (d['act_voice_ord'] == 3),
                                  'high', 'not high')

    # ---------------- usual source of care (Q13/Q14/Q15) ----------------
    d['has_usual'] = _pfx(d['mhos']).map({'0.': 'no', '1.': 'yes'})
    d['usual_sector'] = _pfx(d['mhos_type']).map(_SECTOR)
    d['usual_setting'] = _pfx(d['fhos_type']).map(_SETTING)
    d['usual_hospital'] = _pfx(d['fhos_type']).map(_SETTING_IS_HOSPITAL)
    grp = pd.Series(np.nan, index=d.index, dtype='object')
    for sec in ['public', 'private']:
        for is_hosp, lab in [(True, 'hospital OPD/ER'),
                             (False, 'primary care' if sec == 'public' else 'clinic/pharmacy')]:
            grp.loc[(d['usual_sector'] == sec) & (d['usual_hospital'] == is_hosp)] = f'{sec} {lab}'
    d['provider_group'] = pd.Categorical(grp, categories=GROUPS)
    # Reason the respondent is outside the four-group comparison (mutually exclusive).
    excl = pd.Series(np.nan, index=d.index, dtype='object')
    excl.loc[d['has_usual'] == 'no'] = 'no usual source of care'
    excl.loc[(d['has_usual'] == 'yes') & (d['usual_sector'] == 'non-profit')] = 'non-profit provider'
    excl.loc[(d['has_usual'] == 'yes') & (d['usual_sector'] == 'other')] = 'sector "other"'
    excl.loc[(d['has_usual'] == 'yes') & d['usual_sector'].isin(['public', 'private'])
             & (d['usual_setting'] == 'other')] = 'setting "other"'
    d['exclusion_reason'] = excl
    # Heterogeneity inside private clinic/pharmacy (pharmacies do not screen).
    d['private_primary_sub'] = _bin(d['provider_group'] == 'private clinic/pharmacy',
                                    d['usual_setting'] == 'pharmacy', 'pharmacy', 'clinic')
    d['usual_reason'] = _pfx(d['fhos_reason']).map(
        {'1.': 'low cost', '2.': 'close to home', '3.': 'short waiting time',
         '4.': 'provider skill', '5.': 'staff respect', '6.': 'medicines & equipment',
         '7.': 'only facility in area', '8.': 'covered by my insurance scheme', '9.': 'other'})
    d['usual_qual_ord'] = _pfx(d['fhos_qual']).map({'0.': 0, '1.': 1, '2.': 2, '3.': 3, '4.': 4})
    d['usual_qual_top2'] = _bin(~d['usual_qual_ord'].isna(), d['usual_qual_ord'] >= 3, 'very good/excellent', 'good or worse')

    # ---------------- most recent visit (Q32-Q39) — a DIFFERENT encounter ----------------
    d['last_sector'] = _pfx(d['lastest']).map(_SECTOR)
    d['last_setting'] = _pfx(d['lastest_type']).map(_SETTING)
    d['last_hospital'] = _pfx(d['lastest_type']).map(_SETTING_IS_HOSPITAL)
    lgrp = pd.Series(np.nan, index=d.index, dtype='object')
    for sec in ['public', 'private']:
        for is_hosp, lab in [(True, 'hospital OPD/ER'),
                             (False, 'primary care' if sec == 'public' else 'clinic/pharmacy')]:
            lgrp.loc[(d['last_sector'] == sec) & (d['last_hospital'] == is_hosp)] = f'{sec} {lab}'
    d['last_group'] = pd.Categorical(lgrp, categories=GROUPS)
    d['concordant_sector'] = _bin(~d['usual_sector'].isna() | d['last_sector'].isna(), d['usual_sector'] == d['last_sector'], 'yes', 'no')
    d['concordant_group'] = _bin(~d['provider_group'].isna() | d['last_group'].isna(), d['provider_group'].astype('object')
                                              == d['last_group'].astype('object'), 'yes', 'no')
    d['last_reason'] = _pfx(d['lastest_reason']).map(
        {'1.': 'new/urgent problem', '2.': 'chronic follow-up',
         '3.': 'check-up/prevention', '4.': 'other'})
    d['appoint'] = _pfx(d['lastest_appoint']).map({'0.': 'walk-in', '1.': 'appointment'})

    # Waiting: ORDERED CATEGORIES are primary. Midpoints exist only for a
    # labelled approximate summary — the survey never measured a duration.
    q_lab = {'1.': '<15 min', '2.': '15-29 min', '3.': '30-59 min', '4.': '1-2 h',
             '5.': '2-3 h', '6.': '3-4 h', '7.': '4 h+'}
    d['queue_cat'] = pd.Categorical(_pfx(d['lastest_queue']).map(q_lab),
                                    categories=list(q_lab.values()), ordered=True)
    d['queue_mid_min_approx'] = _pfx(d['lastest_queue']).map(
        {'1.': 7.5, '2.': 22.5, '3.': 45, '4.': 90, '5.': 150, '6.': 210, '7.': 270})
    d['queue_ge1h'] = _bin(~d['queue_cat'].isna(), d['queue_cat'].isin(['1-2 h', '2-3 h', '3-4 h', '4 h+']), 'yes', 'no')
    w_lab = {'1.': 'same/next day', '2.': '2d-<1wk', '3.': '1-<2wk', '4.': '2wk-<1mo',
             '5.': '1-<2mo', '6.': '2-<3mo', '7.': '3-<6mo', '8.': '6mo+'}
    d['wait_cat'] = pd.Categorical(_pfx(d['lastest_waiting']).map(w_lab),
                                   categories=list(w_lab.values()), ordered=True)
    d['wait_mid_days_approx'] = _pfx(d['lastest_waiting']).map(
        {'1.': 0.5, '2.': 4, '3.': 10.5, '4.': 21, '5.': 45, '6.': 75, '7.': 135, '8.': 200})
    d['wait_ge1mo'] = _bin(~d['wait_cat'].isna(), d['wait_cat'].isin(['1-<2mo', '2-<3mo', '3-<6mo', '6mo+']), 'yes', 'no')

    # Experience items: ordinal 0-4 and top-two-box.
    for col in EXP_ITEMS:
        d[col + '_ord'] = d[col].astype('object').map(SCALE5)
        # flag the structural not-applicable answers so denominators are explicit
        na_code = EXP_NA_CODE.get(col)
        d[col + '_na'] = (d[col].astype('object') == na_code) if na_code else False
        d[col + '_top2'] = _bin(~d[col + '_ord'].isna(), d[col + '_ord'] >= 3, 'very good/excellent', 'good or worse')
    # Two items carry genuine item non-response (Q38.4 "knew my history" n=355,
    # Q38.9 "courtesy" n=229); there is no skip logic on Q38. The score is the mean
    # of observed items and requires >= 9 of 11, which every respondent who answered
    # Q38 at all satisfies. Per-item denominators are reported separately.
    EXP_MIN_ITEMS = 9
    ords = d[[c + '_ord' for c in EXP_ITEMS]]
    d['exp_n_valid'] = ords.notna().sum(axis=1)
    d['exp_score'] = ords.mean(axis=1).where(d['exp_n_valid'] >= EXP_MIN_ITEMS)
    d['nps'] = pd.to_numeric(d['lastest_suggest'], errors='coerce')
    d['nps_gr'] = pd.Categorical(
        pd.cut(d['nps'], bins=[-1, 6, 8, 10], labels=['detractor 0-6', 'passive 7-8', 'promoter 9-10']),
        categories=['detractor 0-6', 'passive 7-8', 'promoter 9-10'], ordered=True)
    d['promoter'] = _bin(~d['nps'].isna(), d['nps'] >= 9, 'yes', 'no')

    # ---------------- utilisation ----------------
    d['visits_n'] = pd.to_numeric(d['provider_n'], errors='coerce')
    d['visits_cat'] = pd.Categorical(
        pd.cut(d['visits_n'], bins=[-1, 0, 2, 5, 1e6], labels=['0', '1-2', '3-5', '6+']),
        categories=['0', '1-2', '3-5', '6+'], ordered=True)
    d['one_facility'] = _pfx(d['provider_n_facility']).map({'0.': 'no', '1.': 'yes'})
    # Q20 was in fact put to everyone with at least one visit, so the 161 respondents
    # who attended exactly once are included and answer "one facility" by definition
    # (91.9% of them do). Restricting to more than one visit gives a denominator that
    # can be stated plainly and removes that arithmetic artefact.
    d['one_facility_multi'] = d['one_facility'].where(d['visits_n'] > 1)
    d['admit'] = _pfx(d['admit']).map({'0.': 'no', '1.': 'yes'})
    d['homevisit_any'] = np.where(pd.to_numeric(d['homevisit_n'], errors='coerce') > 0, 'yes', 'no')
    d['telemed_any'] = np.where(pd.to_numeric(d['telemed_n'], errors='coerce') > 0, 'yes', 'no')
    d['unmet'] = _pfx(d['unmet_need']).map({'0.': 'no', '1.': 'yes'})
    d['unmet_reason_lab'] = _pfx(d['unmet_reason']).map(
        {'1.': 'cost', '2.': 'distance', '3.': 'waiting time', '4.': 'provider skill',
         '5.': 'staff disrespect', '6.': 'no medicines/equipment', '7.': 'symptoms mild',
         '8.': 'other'})
    d['borrowed_ever'] = _pfx(d['unmet_financial']).map({'0.': 'no', '1.': 'yes'})
    d['med_error_ever'] = _pfx(d['exp_medicalerr']).map({'0.': 'no', '1.': 'yes'})
    d['discrim_ever'] = _pfx(d['exp_injustice']).map({'0.': 'no', '1.': 'yes'})
    for s in SCREENING:
        d[s + '_r'] = d[s].astype('object').map(YESNO)

    # ---------------- system confidence & quality ----------------
    conf = {'ไม่มั่นใจเลย': 0, 'ไม่ค่อยมั่นใจ': 1, 'ค่อนข้างมั่นใจ': 2, 'มั่นใจมาก': 3}
    for src, out in [('eval_qual', 'conf_get'), ('eval_afford', 'conf_afford'),
                     ('eval_comment', 'conf_voice')]:
        d[out + '_ord'] = d[src].astype('object').map(conf)
        d[out] = _bin(~d[out + '_ord'].isna(), d[out + '_ord'] >= 2, 'confident', 'not confident')
    both_c = d[['conf_get_ord', 'conf_afford_ord']].notna().all(axis=1)
    d['health_security'] = _bin(both_c, (d['conf_get_ord'] >= 2) & (d['conf_afford_ord'] >= 2),
                                'confident', 'not confident')
    # Four-state decomposition for supplement §E.
    _state = pd.Series(np.nan, index=d.index, dtype='object')
    _state.loc[both_c] = pd.Series(
        np.select([(d['conf_get_ord'] >= 2) & (d['conf_afford_ord'] >= 2),
                   (d['conf_get_ord'] >= 2) & (d['conf_afford_ord'] < 2),
                   (d['conf_get_ord'] < 2) & (d['conf_afford_ord'] >= 2)],
                  ['can get & afford', 'can get, cannot afford', 'cannot get, can afford'],
                  default='neither'), index=d.index).loc[both_c]
    d['security_state'] = _state
    d['sys_improved'] = _pfx(d['eval_2yr']).map({'1.': 'improved', '2.': 'same', '3.': 'worse'})
    d['sys_improved_bin'] = _bin(~d['sys_improved'].isna(), d['sys_improved'] == 'improved', 'improved', 'not improved')
    d['sys_endorse'] = _pfx(d['eval_current']).map(
        {'1.': 'rebuild entirely', '2.': 'major change needed', '3.': 'works well'})
    d['sys_endorse_bin'] = _bin(~d['sys_endorse'].isna(), d['sys_endorse'] == 'works well', 'works well', 'needs change')
    for src, out in [('eval_maternal', 'q_maternal'), ('eval_ped', 'q_child'),
                     ('eval_chronic', 'q_chronic'), ('eval_mental', 'q_mentalhealth')]:
        d[out + '_cannot_eval'] = d[src].astype('object') == Q40_NA_CODE
    for src, out in [('eval_public', 'q_public'), ('eval_private', 'q_private'),
                     ('eval_nonprofit', 'q_nonprofit'), ('eval_covid', 'q_covid'),
                     ('eval_maternal', 'q_maternal'), ('eval_ped', 'q_child'),
                     ('eval_chronic', 'q_chronic'), ('eval_mental', 'q_mentalhealth')]:
        d[out + '_ord'] = _pfx(d[src]).map({'0.': 0, '1.': 1, '2.': 2, '3.': 3, '4.': 4})
        d[out + '_top2'] = _bin(~d[out + '_ord'].isna(), d[out + '_ord'] >= 3, 'very good/excellent', 'good or worse')
    return d


def cohort(d):
    """The four-group analysis frame, plus a documented flow table."""
    flow = [('Respondents in the cleaned export', len(d)),
            ('  consented', int((d['consent'].notna()).sum())),
            ('No usual source of care (Q13 = no)', int((d['has_usual'] == 'no').sum())),
            ('Has a usual source of care (Q13 = yes)', int((d['has_usual'] == 'yes').sum()))]
    for r in ['non-profit provider', 'sector "other"', 'setting "other"']:
        flow.append((f'  excluded: {r}', int((d['exclusion_reason'] == r).sum())))
    flow.append(('Four-group analysis cohort', int(d['provider_group'].notna().sum())))
    for g in GROUPS:
        flow.append((f'  {g}', int((d['provider_group'] == g).sum())))
    return d[d['provider_group'].notna()].copy(), pd.DataFrame(flow, columns=['Step', 'n'])
