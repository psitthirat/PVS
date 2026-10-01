"""Item-by-item questionnaire inventory and PVS-framework coverage matrix."""
from __future__ import annotations
import pandas as pd, numpy as np
from . import preparation as prep

# The inventory below was transcribed from the fielded Thai questionnaire.
# It does not load a questionnaire document at runtime.

# (item id, English gloss, data column, construct, framework component,
#  provider/encounter attribution, disposition, reason)
# Framework components follow Figure 1 of the Thai report:
#   F = Foundations, P = Processes, O = Outcomes, D = Design/administrative
ITEMS = [
 ('consent','Consent to participate','consent','Administrative','D','n/a','Analysed','Screening; all 2,017 consented'),
 ('Q1a-c','Province / district / subdistrict','prov, dist, subdist','Geography','D','n/a','Analysed','Sampling audit; PSU identifiers'),
 ('Q2','Type of area of residence (4 options)','area','Urbanicity','F','n/a','Analysed','Collapsed to municipal/non-municipal to match the sampling plan'),
 ('Q3','Age in years','age','Age','F','n/a','Analysed','Missing for 308/2,017; exact-age summaries carry their own denominator'),
 ('Q4','Age band (7 bands)','age_range','Age','F','n/a','Analysed','Complete for all 2,017; primary age variable in this revision'),
 ('Q5','Sex','gender','Sex','F','n/a','Analysed','4 categories incl. "other" (47) and refusal (15); refusal set to missing'),
 ('Q6','Main public health-coverage scheme','insr','Coverage (ownership)','F','n/a','Analysed','"999 don\'t know" (20) set to missing'),
 ('Q7.1','Privately purchased health insurance','insr_private','Coverage (ownership)','F','n/a','Analysed','Ownership only — NOT evidence of payment at any encounter'),
 ('Q7.2','Employer-purchased health insurance','insr_employer','Coverage (ownership)','F','n/a','Analysed','Ownership only'),
 ('Q7.3','No supplementary coverage','insr_none2','Coverage (ownership)','F','n/a','Reported','Complement of Q7.1/7.2'),
 ('Q7.4','No supplementary coverage but pays out of pocket sometimes','insr_oop','Financing (self-report)','F','n/a','Reported','Closest item to payment; refers to general practice, not a specific encounter'),
 ('Q8','Highest education (6 levels)','edu','Socioeconomic','F','n/a','Analysed','6 levels retained; collapsed explicitly where needed'),
 ('Q9','Self-rated physical health','health_level','Health status','F','n/a','Analysed','Coding error corrected — see correction log C-02'),
 ('Q10','Self-rated mental health','mental_level','Health status','F','n/a','Analysed',''),
 ('Q11','Chronic condition >= 6 months','illness_6mo','Health status / need','F','n/a','Analysed','Non-specific; NOT a disease-specific diagnosis'),
 ('Q12a','Confidence managing own health','confidence_selfcare','Patient activation','F','n/a','Analysed','Component of the activation indicator; NOT health literacy'),
 ('Q12b','Confidence voicing concerns unprompted','confidence_selfreport','Patient activation','F','n/a','Analysed','Component of the activation indicator'),
 ('Q13','Has a usual source of care (12 months)','mhos','Use / preferred source','O','Usual source','Analysed','Cohort-defining'),
 ('Q14','Sector of usual source','mhos_type','Use / preferred source','O','Usual source','Analysed','Cohort-defining'),
 ('Q15','Setting of usual source','fhos_type','Use / preferred source','O','Usual source','Analysed','Cohort-defining'),
 ('Q15a','Type of non-hospital clinic','fhos_type_clinic','Use / preferred source','O','Usual source','Reported','Free text; used for private clinic vs pharmacy heterogeneity'),
 ('Q16','Main reason for choosing usual source','fhos_reason','Expectations / choice','F','Usual source','Analysed','Stated reason only — not a payment or registration record'),
 ('Q17','Quality of usual source, past 12 months','fhos_qual','Competent care (perceived)','P','Usual source','Analysed',''),
 ('Q18','Number of outpatient visits','provider_n','Utilisation','O','Not attributed','Analysed','Excludes inpatient nights, telemedicine, self-care AND pharmacy purchases'),
 ('Q19','Visit-count band if Q18 unanswerable','provider_n_gr','Utilisation','O','Not attributed','Reported','Fallback item; small n'),
 ('Q20','All visits at the same facility','provider_n_facility','Continuity','P','Not attributed','Analysed','Structural skip: asked only when Q18>1 or Q19 in 2-4'),
 ('Q21','Number of different facilities used','provider_n_facility_n','Continuity','P','Not attributed','Unusable','Answered by 519/2,017; conditional on Q20 = no'),
 ('Q22','Number of home visits','homevisit_n','Utilisation','O','Not attributed','Analysed',''),
 ('Q23','Number of telemedicine contacts','telemed_n','Utilisation','O','Not attributed','Analysed',''),
 ('Q24','Reason for most recent telemedicine contact','telemed_reason','Utilisation','O','Telemedicine','Reported','n=146 with any telemedicine'),
 ('Q25','Quality of telemedicine','telemed_qual','Competent care (perceived)','P','Telemedicine','Reported','n too small for provider-group models'),
 ('Q26','Admitted overnight, past 12 months','admit','Utilisation','O','NOT attributed to any facility','Analysed','Facility of admission was NOT collected'),
 ('Q27A','Blood pressure measured','bp','Health-promoting care','P','Not attributed','Analysed','Past 12 months; researcher verified original questionnaire on 2026-10-01'),
 ('Q27B','Breast examination / mammogram','mammogram','Health-promoting care','P','Not attributed','Analysed','Sex-restricted denominator applied; 52 men answered "received"'),
 ('Q27C','Cervical cancer screening','ca_cervix','Health-promoting care','P','Not attributed','Analysed','Sex-restricted denominator applied; 47 men answered "received"'),
 ('Q27D','Vision check','vision','Health-promoting care','P','Not attributed','Analysed',''),
 ('Q27E','Dental examination','dental','Health-promoting care','P','Not attributed','Analysed',''),
 ('Q27F','Blood sugar test','sugar','Health-promoting care','P','Not attributed','Analysed',''),
 ('Q27G','Blood lipid test','lipid','Health-promoting care','P','Not attributed','Analysed',''),
 ('Q27H','Received mental-health services','mental','Health-promoting care','P','Not attributed','Analysed','Service receipt, NOT screening — label corrected'),
 ('Q28a','Perceived medical error (ever)','exp_medicalerr','Safe care','P','NOT attributed','Analysed','Patient report; no recall window; no facility attribution'),
 ('Q28b','Felt discriminated against (ever)','exp_injustice','Respect / voice','P','NOT attributed','Analysed','Patient report; no recall window; no facility attribution'),
 ('Q29','Unmet health-care need','unmet_need','Access / non-use','O','Not attributed','Analysed','Past 12 months; original questionnaire confirmation supersedes abbreviated export header'),
 ('Q30','Main reason for unmet need','unmet_reason','Access / non-use','O','Not attributed','Analysed','Conditional on Q29 = yes'),
 ('Q31','Borrowed or sold assets to pay for care (past 12 months)','unmet_financial','Financial hardship','O','NOT attributed','Analysed','Closest available financial-protection item; recall confirmed by researcher from original questionnaire'),
 ('Q32','Sector of most recent facility','lastest','Use / preferred source','O','Last visit','Analysed','Different encounter from Q14; no recall window'),
 ('Q33','Setting of most recent facility','lastest_type','Use / preferred source','O','Last visit','Analysed',''),
 ('Q33a','Type of non-hospital clinic, last visit','lastest_type_clinic','Use','O','Last visit','Reported','Free text'),
 ('Q34','Main reason for most recent visit','lastest_reason','Use','O','Last visit','Analysed',''),
 ('Q35','Most recent visit by appointment','lastest_appoint','Timely care','P','Last visit','Analysed',''),
 ('Q36','Days between booking and being seen','lastest_waiting','Timely care','P','Last visit','Analysed','Structural skip: appointment-holders only (n=738)'),
 ('Q37','Waiting time at facility','lastest_queue','Timely care','P','Last visit','Analysed','Ordered categories; midpoints are approximations only'),
 ('Q38a','Overall quality of care received','lastest_qual','Global rating','P','Last visit','Analysed','Not an independent measure of clinical competence'),
 ('Q38b','Provider knowledge and skill','lastest_knowledge','Competent care (perceived)','P','Last visit','Analysed',''),
 ('Q38c','Readiness of equipment and supplies','lastest_readiness','Competent system','P','Last visit','Analysed',''),
 ('Q38d','Respect shown by provider','lastest_respect','User experience: respect','P','Last visit','Analysed',''),
 ('Q38e','Provider knew previous treatment/results','lastest_data_pre','Continuity / coordination','P','Last visit','Analysed','Has explicit "no prior visit/don\'t know" code (n=355)'),
 ('Q38f','Explained information understandably','lastest_inform','User experience: communication','P','Last visit','Analysed',''),
 ('Q38g','Involved respondent in decisions','lastest_engage','User experience: voice','P','Last visit','Analysed',''),
 ('Q38h','Time the provider spent','lastest_duration','User experience: customer service','P','Last visit','Analysed',''),
 ('Q38i','Time waited before seeing provider','lastest_sat-queue','Timely care','P','Last visit','Analysed',''),
 ('Q38j','Courtesy/helpfulness of OTHER staff','lastest_polite','User experience: customer service','P','Last visit','Analysed','Has explicit "no other staff" code (n=229)'),
 ('Q38k','Time waited to obtain this appointment','lastest_queue-appoint','Timely care','P','Last visit','Analysed',''),
 ('Q39','Likelihood to recommend (0-10)','lastest_suggest','Endorsement of provider','O','Last visit','Analysed',''),
 ('Q40a','Quality of public maternal care','eval_maternal','Competent system','P','Public primary care (system)','Analysed','Has "cannot evaluate" code'),
 ('Q40b','Quality of public child care','eval_ped','Competent system','P','Public primary care (system)','Analysed','Has "cannot evaluate" code'),
 ('Q40c','Quality of public chronic-disease care','eval_chronic','Competent system','P','Public primary care (system)','Analysed','Has "cannot evaluate" code'),
 ('Q40d','Quality of public mental-health care','eval_mental','Competent system','P','Public primary care (system)','Analysed','Has "cannot evaluate" code'),
 ('Q41a','Confident of good care if seriously ill','eval_qual','Confidence / security','O','System','Analysed','Conditional framing: "if you were seriously ill"'),
 ('Q41b','Confident of affording care if seriously ill','eval_afford','Confidence / security','O','System','Analysed','Conditional framing'),
 ('Q41c','Government listens to public opinion on health','eval_comment','Voice / responsiveness','O','System','Analysed','Direct measure of government responsiveness'),
 ('Q42','Overall quality of the public health system','eval_public','System quality','P','System','Analysed',''),
 ('Q43','Overall quality of the for-profit private system','eval_private','System quality','P','System','Analysed',''),
 ('Q44','Overall quality of the non-profit system','eval_nonprofit','System quality','P','System','Reported','Not used in provider-group models'),
 ('Q45','System direction over past 2 years','eval_2yr','Endorsement: direction','O','System','Analysed',''),
 ('Q46','Endorsement of current system','eval_current','Endorsement: current','O','System','Analysed',''),
 ('Q47','Government COVID-19 management','eval_covid','Government competence','O','System','Analysed',''),
 ('Q48','Vignette 1: low-quality consultation','expect_1','Population expectations','F','Vignette','Unreported','Vignette pair fielded but not analysed in either report'),
 ('Q49','Vignette 2: thorough consultation','exPect_2','Population expectations','F','Vignette','Unreported','Vignette pair fielded but not analysed in either report'),
 ('Q50','Mother tongue','language','Individual characteristics','F','n/a','Unreported','Available; not used'),
 ('Q51','Monthly household income','income','Socioeconomic','F','n/a','Analysed',''),
 ('Q52a','Voted for constituency MP','mop_cons','Political context','F','n/a','Unreported','Out of scope for this revision'),
 ('Q52b','Voted for party-list MP','mop_partylist','Political context','F','n/a','Unreported','Out of scope for this revision'),
]

FRAMEWORK = {
 'F': 'Foundations (expectations, health status, individual characteristics)',
 'P': 'Processes (competent system, competent care, positive user experience)',
 'O': 'Outcomes (confidence, trust, endorsement, use / preferred source)',
 'D': 'Design / administrative',
}

# Constructs the reviewer asked us to look for. Presence here is the SEARCH LIST,
# not evidence of measurement.
SOUGHT = [
 ('Population expectations', 'PARTIAL', 'Q48/Q49 vignettes were fielded but never analysed; Q16 captures stated reason for provider choice. No direct expectation scale.'),
 ('Health literacy', 'NOT MEASURED', 'No health-literacy, digital-literacy or health-knowledge item exists. Q12a/Q12b measure patient activation; Q8 measures education. These are three different constructs.'),
 ('Coordination / referral', 'NOT MEASURED', 'No referral, follow-up or care-transition item.'),
 ('Continuity', 'PARTIAL', 'Q20 (same facility for all visits) and Q38e (provider knew previous results) are proxies; no provider-continuity or relationship-duration item.'),
 ('Confidentiality', 'PARTIAL', 'Named only as an example inside the Q28a medical-error stem; no standalone item.'),
 ('Discrimination', 'MEASURED', 'Q28b, lifetime recall, no facility attribution.'),
 ('Medical errors', 'MEASURED', 'Q28a, lifetime recall, no facility attribution; patient perception, not adjudicated events.'),
 ('Financial barriers / hardship', 'PARTIAL', 'Q30 reason "cost" and Q31 borrowing (past 12 months). No out-of-pocket amount, no catastrophic-expenditure measure.'),
 ('Reasons for unmet need', 'MEASURED', 'Q30, conditional on Q29.'),
 ('Participation / voice', 'MEASURED', 'Q41c (government listens) and Q38g (involved in decisions).'),
 ('Actual payer / payment at an encounter', 'NOT MEASURED', 'No question asks who paid for any specific visit or admission, nor any amount. Q7 records coverage OWNERSHIP only.'),
 ('Employment status', 'NOT MEASURED', 'Not asked. SSS membership is not a substitute.'),
 ('Registered / contracted provider', 'NOT MEASURED', 'Not asked. Q14/Q15 record where the respondent usually goes, not where they are registered.'),
 ('Facility of overnight admission', 'NOT MEASURED', 'Q26 records that an admission happened, never where.'),
]


def inventory_df(d):
    rows = []
    for iid, gloss, col, construct, comp, attrib, dispo, reason in ITEMS:
        first = col.split(',')[0].strip()
        n_obs = int(d[first].notna().sum()) if first in d.columns else np.nan
        rec = prep.RECALL.get(first, (None, None))
        rows.append({
            'Item ID': iid, 'Item (English gloss)': gloss, 'Data column(s)': col,
            'Construct': construct, 'Framework component': FRAMEWORK[comp],
            'Recall period': rec[0] or ('most recent visit' if 'lastest' in first else 'n/a'),
            'Respondent universe': rec[1] or 'all respondents',
            'Observed n (of 2,017)': n_obs,
            'Missing n': int(len(d) - n_obs) if n_obs == n_obs else np.nan,
            'Provider/encounter attribution': attrib,
            'Disposition': dispo, 'Reason / note': reason})
    return pd.DataFrame(rows)


def framework_matrix(d, coh):
    """Framework component x provider group: which measures exist, direct or proxy."""
    rows = []
    for iid, gloss, col, construct, comp, attrib, dispo, reason in ITEMS:
        if comp == 'D' or dispo in ('Unreported', 'Unusable'):
            continue
        rows.append({'Framework component': FRAMEWORK[comp], 'Construct': construct,
                     'Item': f'{iid} {gloss}', 'Measure type':
                         'Direct' if attrib in ('Usual source', 'Last visit', 'System',
                                                'Public primary care (system)') else 'Proxy / unattributed',
                     'Comparable across the 4 provider groups?':
                         'Yes — attributed to the usual source' if attrib == 'Usual source'
                         else ('Yes, but describes the LAST visit, not the usual source'
                               if attrib == 'Last visit'
                               else ('Yes, but the item is about the system, not the respondent\'s provider'
                                     if 'System' in str(attrib) or 'system' in str(attrib)
                                     else 'No — not attributable to any provider')),
                     'Regulatory relevance to private hospitals':
                         _reg_relevance(construct)})
    return pd.DataFrame(rows)


def _reg_relevance(construct):
    m = {
        'Competent care (perceived)': 'High — perceived clinical quality of a licensed provider',
        'Competent system': 'High — facility readiness and service availability',
        'User experience: respect': 'High — patient-rights and complaints oversight',
        'User experience: communication': 'High — informed-consent and information duties',
        'User experience: voice': 'High — shared decision-making duties',
        'User experience: customer service': 'Medium — service-standard monitoring',
        'Timely care': 'High — access and waiting-time standards',
        'Safe care': 'High — adverse-event reporting',
        'Respect / voice': 'High — anti-discrimination and complaints',
        'Continuity / coordination': 'Medium — records and continuity obligations',
        'Continuity': 'Medium — records and continuity obligations',
        'Health-promoting care': 'High — prevention obligations of contracted providers',
        'Financial hardship': 'High — price transparency and billing oversight',
        'Access / non-use': 'High — access obligations',
        'Coverage (ownership)': 'High — contracted-provider arrangements',
        'Financing (self-report)': 'High — but the item cannot identify payer at an encounter',
        'Endorsement of provider': 'Medium — patient-reported outcome for monitoring',
        'System quality': 'Low — refers to the system, not a regulated entity',
        'Expectations / choice': 'Medium — informs contracting and choice policy',
    }
    return m.get(construct, 'Low / contextual')


def sought_constructs_df():
    return pd.DataFrame(SOUGHT, columns=['Construct the reviewer asked about',
                                         'Status in the fielded instrument',
                                         'Evidence'])
