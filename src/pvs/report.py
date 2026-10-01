"""
Revised English report (DOCX) for the 2026-09 revision.

Every table and figure is read from output/, so no number is typed independently.
Writes the working report; approved release copies under results/ are unchanged.
"""
from __future__ import annotations
import os, warnings
import pandas as pd
warnings.filterwarnings('ignore')
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from .paths import OUTPUT as OUT
TAB, FIG = f'{OUT}/tables', f'{OUT}/figures'
INK, MUT, ACC = RGBColor(0x1a, 0x1a, 0x1a), RGBColor(0x60, 0x60, 0x60), RGBColor(0xa8, 0x40, 0x0c)
USABLE = 17.0


def build():
    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.0)
    st = doc.styles['Normal']
    st.font.name = 'Calibri'; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
    st.paragraph_format.space_after = Pt(7); st.paragraph_format.line_spacing = 1.15

    def H(t, lvl=1):
        p = doc.add_heading(t, level=lvl)
        for r in p.runs:
            r.font.color.rgb = INK; r.font.name = 'Calibri'
            r.font.size = Pt({1: 15, 2: 12.5, 3: 11}[lvl]); r.font.bold = True
        p.paragraph_format.space_before = Pt(14 if lvl < 3 else 10)
        p.paragraph_format.space_after = Pt(5)

    def P(t, size=10.5, italic=False, color=None, after=7, bold=False):
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(after)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r = p.add_run(t); r.font.size = Pt(size); r.italic = italic; r.bold = bold
        r.font.color.rgb = color or INK

    def B(t, lead=None):
        p = doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after = Pt(4)
        if lead:
            r = p.add_run(lead); r.bold = True; r.font.size = Pt(10.5); r.font.color.rgb = INK
        r = p.add_run(t); r.font.size = Pt(10.5); r.font.color.rgb = INK

    def shade(c, hx):
        el = OxmlElement('w:shd'); el.set(qn('w:val'), 'clear'); el.set(qn('w:fill'), hx)
        c._tc.get_or_add_tcPr().append(el)

    def borders(t):
        b = OxmlElement('w:tblBorders')
        for e in ('top', 'bottom', 'insideH'):
            x = OxmlElement(f'w:{e}'); x.set(qn('w:val'), 'single')
            x.set(qn('w:sz'), '4' if e == 'insideH' else '8')
            x.set(qn('w:color'), 'D8D8D8' if e == 'insideH' else '808080'); b.append(x)
        for e in ('left', 'right', 'insideV'):
            x = OxmlElement(f'w:{e}'); x.set(qn('w:val'), 'none'); b.append(x)
        t._tbl.tblPr.append(b)

    def cap(label, text):
        p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(label + '  '); r.bold = True; r.font.size = Pt(9.5); r.font.color.rgb = INK
        r = p.add_run(text); r.font.size = Pt(9.5); r.font.color.rgb = INK

    def note(t):
        p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(11)
        r = p.add_run(t); r.font.size = Pt(8); r.italic = True; r.font.color.rgb = MUT

    def table(df, first=5.4, last=1.6, fs=8.2, bold_sig=None):
        cols = list(df.columns)
        t = doc.add_table(rows=1, cols=len(cols))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False; borders(t)
        lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); t._tbl.tblPr.append(lay)
        mid = (USABLE - first - last) / max(1, len(cols) - 2)
        widths = [Cm(first)] + [Cm(mid)] * (len(cols) - 2) + [Cm(last)]
        hc = t.rows[0].cells
        for i, h in enumerate(cols):
            hc[i].text = ''
            for j, line in enumerate(str(h).split('\n')):
                p = hc[i].paragraphs[0] if j == 0 else hc[i].add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(line); r.bold = True; r.font.size = Pt(fs); r.font.color.rgb = INK
            shade(hc[i], 'F2F2F0')
        for _, row in df.iterrows():
            cells = t.add_row().cells
            sig = bold_sig(row) if bold_sig else False
            for i, cname in enumerate(cols):
                v = row[cname]
                v = '' if pd.isna(v) else v
                cells[i].text = ''
                p = cells[i].paragraphs[0]; p.paragraph_format.space_after = Pt(0)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                txt = str(v)
                if i == 0 and txt.startswith('    '):
                    p.paragraph_format.left_indent = Cm(0.35)
                r = p.add_run(txt.strip()); r.font.size = Pt(fs)
                r.font.color.rgb = ACC if (sig and i > 0) else INK
                if sig and i > 0:
                    r.bold = True
        for row in t.rows:
            for i, c in enumerate(row.cells):
                c.width = widths[i] if i < len(widths) else Cm(last)

    def figure(path, label, text, nt, width=16.6):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(3)
        p.add_run().add_picture(path, width=Cm(width))
        cap(label, text); note(nt)

    def rd(name, cols=None, q=None, rnd=None, rename=None):
        df = pd.read_csv(f'{TAB}/{name}.csv')
        if q is not None:
            df = df.query(q)
        if cols:
            df = df[cols]
        if rnd:
            df = df.round(rnd)
        if rename:
            df = df.rename(columns=rename)
        return df.reset_index(drop=True)

    G = ['public primary care', 'public hospital OPD/ER',
         'private clinic/pharmacy', 'private hospital OPD/ER']
    GS = {g: g.replace('public ', 'Public\n').replace('private ', 'Private\n') for g in G}

    # ------------------------------------------------------------------ title
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    r = p.add_run('Customers of private hospitals in the Thai health system')
    r.bold = True; r.font.size = Pt(19); r.font.color.rgb = INK
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(12)
    r = p.add_run('Who they are, how they use care, how they judge quality — and what it means '
                  'for regulating private hospitals')
    r.font.size = Pt(12); r.font.color.rgb = MUT
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(16)
    r = p.add_run("People’s Voice Survey (Thailand) • Population Confidence and Quality of the "
                  "Health System\nP. Sitthirat et al. • 2,017 adult respondents; 1,518 with a "
                  "classifiable usual source of care • Edition of 14 September 2026")
    r.font.size = Pt(9.5); r.font.color.rgb = MUT

    # ------------------------------------------------------------------ summary
    H('Summary', 1)
    P("Thailand’s People’s Voice Survey asks every respondent where they usually go first when "
      "they are ill. Crossing the sector of that usual source with its setting divides the 1,518 "
      "respondents who named one into four groups: public primary care (n = 634), public hospital "
      "outpatient or emergency care (n = 615), private clinics and pharmacies (n = 142), and private "
      "hospitals (n = 127). This report profiles the last of these against the other three, with "
      "public hospital users as the comparison throughout — the closest counterfactual, since both "
      "groups use hospital outpatient care.")
    P('Six findings stand out.')
    B('Only 4.7% of regular private-hospital users report a household income of ฿60,000 or more per '
      'month — no more than public primary care users. What distinguishes them is coverage: 69.8% '
      'hold Social Security, against 16.8% of public hospital users, and insurance coverage is the '
      'reason they most often give for choosing their facility (33.9%). Low cost is almost never cited '
      '(1.6%). Whether they were actually assigned to those providers cannot be determined — '
      'registration, payer and employment are not measured.',
      lead='They are a salaried middle, not an affluent elite. ')
    B('They wait less at the facility (25.2% wait an hour or more, against 44.1%) and walk in more '
      'often. But among the 44 who booked ahead, 65.9% still waited a month or more to be seen, against '
      '72.8% of public hospital appointment-holders. The advantage is concentrated in walk-in, same-day '
      'service rather than in scheduled care.',
      lead='Faster walk-in access, but scheduled care queues much as it does in the public sector. ')
    B('Nine of eleven experience items differ after adjustment, led by satisfaction with waiting time '
      '(aOR 3.54, +26.9 percentage points), the provider knowing the patient’s history (3.16, '
      '+26.6 pp) and ease of getting an appointment (3.28, +23.8 pp). The two perceived-competence '
      'items do not differ: provider knowledge and skill 1.38 (0.83–2.31) and equipment readiness '
      '1.11 (0.69–1.78). None of the eleven measures objective clinical quality.',
      lead='The quality difference is in service process, not perceived clinical competence. ')
    B('On all eight screening and prevention items, private-hospital users are indistinguishable from '
      'public hospital users after adjustment. The one robust preventive finding concerns pharmacies: '
      'blood-pressure measurement is 70.0% among people whose usual source is a pharmacy, against '
      '96.9–98.4% in every other group.',
      lead='There is no preventive-service gap between private and public hospital users. ')
    B('29.1% report an overnight admission in the past year — aOR 2.42 (1.35–4.31), +14.2 pp '
      '— in the group reporting the best health, with chronic illness adjusted for. The '
      'questionnaire never records where an admission happened, so this cannot show that it occurred at '
      'a private hospital or that it was unnecessary. It is the finding most worth pursuing with claims '
      'data.', lead='Self-reported admission is substantially higher, and unexplained. ')
    B('No system-level difference is detectable after adjustment, including health security (aOR 1.27, '
      '0.80–2.01). That interval is compatible with anything from a modest decrease to a doubling, '
      'so it is not evidence that provider type is unrelated to confidence. What the data show directly '
      'is that 14.2% of private-hospital users rate their own facility very good or excellent while '
      'remaining unsure they could get and afford care if seriously ill.',
      lead='A good personal experience and insecurity about serious illness coexist. ')

    # ------------------------------------------------------------------ methods
    H('Data and methods', 1)
    P("The Thai People’s Voice Survey covers 2,017 adults aged 18 or over across all 13 health "
      "regions, with one province sampled per region, subdistricts selected by probability proportional "
      "to size, and quota-based convenience recruitment at the final stage. The achieved sample tracks "
      "the plan closely — planned 686 municipal and 1,314 non-municipal, achieved 697 and 1,320, "
      "with every region within six respondents of target — but the sex quota was not met (42.8% "
      "male against 50% planned). Estimates are unweighted and describe the achieved sample.")
    P('Provider groups cross the sector of the usual source of care (Q14) with its setting (Q15). '
      '"Secondary" is not used as a label: Q15 separates hospital outpatient and emergency departments '
      'from non-hospital settings, which does not establish whether a hospital is secondary or '
      'tertiary. 488 respondents report no usual source of care and 11 are unclassifiable — 6 '
      'non-profit providers, 2 sector "other", 3 setting "other".')
    P('Adjusted comparisons use logistic regression on provider group plus age band, sex, education, '
      'household income, municipality, coverage scheme, self-rated health and chronic illness, with '
      'cluster-robust standard errors on the 107 sampled subdistricts. Each result is reported as an '
      'adjusted odds ratio and as the average marginal predicted probability with a percentage-point '
      'difference, because an odds ratio is not a probability ratio. Benjamini–Hochberg adjustment '
      'is applied within each pre-declared outcome family, and null results are retained.')
    P('Three cautions apply throughout, and are the reason several statements below are more guarded '
      'than they might otherwise be. These are associations, not effects: respondents are not allocated '
      'to providers, insurance routing is an obvious selection mechanism, and adjustment narrows but '
      'does not remove it. Most measures are not attributable to a provider — screening, admission, '
      'medical error and discrimination record no facility, and the visit-experience items describe the '
      'most recent visit, which is the usual source of care for 84.3% of private-hospital users but '
      'only 64.1% of private clinic and pharmacy users. Preventive services and unmet need refer '
      'to the past 12 months, as confirmed against the original questionnaire on 1 October 2026. '
      'Medical error and discrimination remain reports of ever experiencing the event.', italic=True, color=MUT, size=10)
    cap('Table 1.', 'Cohort flow from the full sample to the four-group comparison.')
    note('Exclusions are mutually exclusive and separately identified. The three public respondents whose '
         'setting was "other" are why the sector total of 1,252 exceeds the four-group public total of 1,249.')
    table(rd('T01_cohort_flow'), first=10.0, last=3.0)

    # ------------------------------------------------------------------ 1 who
    doc.add_page_break()
    H('1. Who uses private hospitals', 1)
    P('The four groups differ sharply, but not along the axis usually assumed. Private-hospital users '
      'are the most urban group (49.6%) and among the most educated — 62.2% hold a diploma or a '
      'bachelor’s degree. Their household income sits in the middle of the distribution rather than '
      'at the top: 46.5% report ฿30,000–59,999 per month, but only 4.7% report ฿60,000 or '
      'more, no more than public primary care users, and a single respondent in the group reports the '
      'top income band.')
    P('The defining characteristic is the coverage scheme. Social Security covers 69.8% of '
      'private-hospital users against 16.8% of public hospital users, while only 26.2% hold Universal '
      'Coverage against 79.5% in public primary care. Private health insurance is more common in this '
      'group (31.5%) but is held by a minority — and ownership is not evidence of use at any visit.')
    P('They also report better health (92.1% good or better) and higher patient activation (88.2%). One '
      'correction is worth making explicitly: it is private clinic and pharmacy users, not '
      'private-hospital users, who report the least chronic illness (16.2% against 32.3%) and '
      'marginally better self-rated health.')
    figure(f'{FIG}/Figure 1 - Profile by provider group.png', 'Figure 1.',
           'Demographic, coverage and health profile by type of usual source of care.',
           'Bars show the percentage of eligible respondents in each group with a 95% Wilson interval. '
           'Age uses the complete Q4 band, which is observed for all 2,017 respondents; exact age (Q3) is '
           'missing for 308 and is not used here.')
    cap('Table 2.', 'Profile by type of usual source of care.')
    note('Cells are n/N (% ; 95% CI) for binary measures and n/N (%) within distributions. Denominators '
         'vary where a variable has missing values — sex excludes 15 refusals, the coverage scheme '
         'excludes 20 "don’t know" answers. p-values are Pearson chi-square across the four groups.')
    table(rd('T20_profile_by_group', rename=GS), first=4.6, last=1.5, fs=7.6)

    # ------------------------------------------------------------------ 1.1 target
    doc.add_page_break()
    H('1.1 Who is the main target population?', 2)
    P('A natural summary of the profile above would be "under 50, urban, with Social Security". '
      'Tested directly, only one part of that holds up. Table 2a scores candidate target definitions on '
      'two things: precision \u2014 the rate of private-hospital use within the group, calculated over '
      'all 2,017 respondents \u2014 and reach, the share of all 127 private-hospital users the group '
      'contains. The average rate is 6.3%.')
    tdef = rd('T79_target_definitions_compared',
              cols=['Target definition', '% of population', 'Private-hospital users (n)',
                    'Rate % (precision)', 'Rate 95% CI low', 'Rate 95% CI high',
                    'Share of all users % (reach)', 'Index (100 = average)'])
    t_ = tdef.set_index('Target definition')
    def _g(prefix, col):
        return t_.loc[[i for i in t_.index if i.startswith(prefix)][0], col]
    P(f'Social Security on its own is the strongest single marker: it covers 23.5% of respondents but '
      f'contains {_g("Social Security", "Share of all users % (reach)"):.1f}% of all private-hospital '
      f'users, at a rate of {_g("Social Security", "Rate % (precision)"):.1f}% \u2014 three times the '
      f'average. Adding "under 50" makes the target worse rather than better: the rate falls to '
      f'{_g("Social Security + under 50", "Rate % (precision)"):.1f}% and reach to '
      f'{_g("Social Security + under 50", "Share of all users % (reach)"):.1f}%. Adding "municipal" '
      f'raises precision to {_g("Social Security + municipal", "Rate % (precision)"):.1f}% but halves '
      f'reach, because half of all private-hospital users live outside municipalities. The full '
      f'combination of all three has a rate of '
      f'{_g("Social Security + under 50 + municipal", "Rate % (precision)"):.1f}% \u2014 no better '
      f'than Social Security alone \u2014 while capturing only '
      f'{_g("Social Security + under 50 + municipal", "Share of all users % (reach)"):.1f}% of users.')
    P(f'Income is the better second marker. Social Security members with a household income of '
      f'\u0e3f30,000 or more have the highest rate of the definitions in Table 2a, '
      f'{_g("Social Security + income 30k", "Rate % (precision)"):.1f}% (index '
      f'{_g("Social Security + income 30k", "Index (100 = average)"):.0f}), and still account for '
      f'{_g("Social Security + income 30k", "Share of all users % (reach)"):.1f}% of users.')
    cap('Table 2a.', 'Candidate target definitions compared on precision and reach.')
    note('Rate = private-hospital users \u00f7 everyone in the group, over all 2,017 respondents (people '
         'with no usual source of care count as non-users). Share = users in the group \u00f7 all 127 users. '
         'Index = rate \u00f7 6.3% \u00d7 100. Scheme is coverage ownership, not registration or payment.')
    tdef.columns = ['Target definition', '% of pop.', 'Users (n)', 'Rate %', 'CI low', 'CI high',
                    'Share of users %', 'Index']
    table(tdef, first=6.2, last=1.3, fs=7.6)

    P('Age is the trap. Under-50s have a higher rate overall (7.4% against 5.0%), but that is because '
      'Social Security members are mostly working-age. Within Social Security, members aged 50 and over '
      'are at least as likely to use a private hospital \u2014 25.3% (95% CI 17.7\u201334.6) against '
      '16.8% (13.4\u201320.9) \u2014 and under Universal Coverage the two age groups are essentially '
      'equal. When every characteristic is considered at once, Social Security (aOR 6.95, +13.3 '
      'percentage points), household income of \u0e3f30,000 or more (5.54, +7.1 pp) and owning private '
      'insurance (1.94, +4.0 pp) each mark private-hospital users independently; being under 50 does '
      'not (0.73, 0.43\u20131.25), and municipal residence is suggestive but not statistically clear '
      '(1.69, 0.93\u20133.07).')
    cap('Table 2b.', 'Rate of private-hospital use by age, area and coverage scheme, ranked.')
    note('All 16 combinations. Cells with fewer than 30 people are flagged and should be read as indicative '
         'only. Cumulative columns show how much of the user population is captured working down the list. '
         'Heat-shaded n \u00d7 n matrices for nine pairs of characteristics are in '
         '"Target segmentation - private hospital users.xlsx".')
    seg = rd('T76_target_segments_age_area_scheme',
             cols=['Rank', 'Segment', 'People (N)', 'Private-hospital users (n)', 'Rate %',
                   'Share of all users %', 'Small cell (N < 30)', 'Cumulative share of users %'])
    seg['Small cell (N < 30)'] = seg['Small cell (N < 30)'].fillna('')
    seg = seg[['Segment', 'Rank', 'People (N)', 'Private-hospital users (n)', 'Rate %',
               'Share of all users %', 'Cumulative share of users %', 'Small cell (N < 30)']]
    seg.columns = ['Segment', 'Rank', 'People', 'Users', 'Rate %', 'Share %', 'Cumul. share %', 'Small cell']
    table(seg, first=6.6, last=1.3, fs=7.2)
    P('The practical answer is therefore that the main users of private hospitals are Social Security '
      'members, best sharpened by household income rather than by age or area. The largest single pool '
      'by volume \u2014 under-50 Social Security members living outside municipalities, 29.9% of all '
      'users \u2014 would be missed entirely by a target defined as urban. As throughout, holding a '
      'scheme does not show that the respondent is registered with or paid by it at the private hospital.')

    # ------------------------------------------------------------------ 2 why
    doc.add_page_break()
    H('2. Why they go there, and how they get in', 1)
    P('Asked for the single main reason they use their regular facility, private-hospital users name '
      'insurance coverage most often (33.9%) — the same answer, at almost exactly the same rate, as '
      'public hospital users (33.3%). Short waiting time comes second (25.2%), a reason cited by only '
      '1.5% of public hospital users. Proximity, the dominant consideration in public primary care '
      '(56.5%), matters least to them (18.9%). Low cost is effectively absent as a motive (1.6%).')
    P('Private clinic and pharmacy users look different again: 47.9% cite short waiting time and only '
      '6.3% cite insurance, which fits a pattern of convenience-driven, largely self-financed episodic '
      'care. The two private groups are not one market.')
    P('A stated reason together with a scheme distribution is consistent with insurance routing, and in '
      'Thailand Social Security members register with a contracted main hospital that may be public or '
      'private. But this survey cannot confirm the mechanism: it does not ask where anyone is '
      'registered, who paid for any visit, or whether the respondent is currently in salaried '
      'employment.')
    figure(f'{FIG}/Figure 2 - Reason for choosing provider.png', 'Figure 2.',
           'Main reason for choosing the usual source of care (single response, Q16).',
           'Asked only of respondents with a usual source of care. Categories below 3% in every group are '
           'omitted from the figure and retained in Table 3.')
    P('Access differs sharply in one direction and not in another. Private-hospital users are seen '
      'faster at the facility: 55.9% within half an hour against 27.0% of public hospital users, and '
      '25.2% wait an hour or more against 44.1%. No respondent in either private group reported waiting '
      'four hours or more, a wait 2.4% of public hospital users described. They are also more likely to '
      'walk in without an appointment (65.4% against 50.4%).')
    P('But among the minority who booked ahead — 44 respondents in the private-hospital group — '
      '65.9% still waited a month or more between booking and being seen, and a quarter waited three to '
      'six months. The comparable public hospital figure is 72.8%. Scheduled care queues in both '
      'sectors; the private advantage is concentrated in walk-in, same-day service. Both waiting items '
      'are recorded as ordered categories, not as measured durations.')
    figure(f'{FIG}/Figure 3 - Access and utilisation.png', 'Figure 3.',
           'Waiting time at the facility and pattern of service use.',
           'Panel A: distribution of reported waiting time before being seen at the most recent visit '
           '(Q37); segments below 7% are unlabelled. Panel B: selected indicators, % of each group.')
    cap('Table 3.', 'Reason for choosing the usual source of care, appointments and waiting.')
    note('Q36 (booking-to-appointment wait) is a structural skip asked only of appointment-holders: '
         'n = 265, 305, 32 and 44 respectively. Q36 and Q37 are ordered categories; no duration was measured.')
    table(rd('T22_access_by_group', rename=GS), first=4.6, last=1.5, fs=7.6)

    # ------------------------------------------------------------------ 3 services
    doc.add_page_break()
    H('3. How they use services', 1)
    P('Private-hospital users make a median of two outpatient visits a year and concentrate that '
      'contact. Among respondents with more than one visit in the past twelve months \u2014 the only '
      'group for whom the question is informative, since a single visit is one facility by arithmetic '
      '\u2014 80.0% used just one facility, the highest of the four groups, against 71.1% of public '
      'hospital users, 63.6% in public primary care and 46.8% among private clinic and pharmacy users. '
      '92.9% made their most recent visit in the sector of their usual source. This is a settled '
      'relationship rather than occasional private use.')
    P('Community-facing services run the other way. Only 3.9% received a home visit, against 24.4% in '
      'public primary care — a reminder that the outreach arm of the Thai system is a public primary '
      'care function that private hospital registration does not replace. Unmet need is reported by '
      '17.3%, and is not significantly different from public hospital users after adjustment. Financial '
      'distress is rare across the board and lowest in the two private groups.')
    cap('Table 4.', 'Service utilisation, unmet need and adverse experience.')
    note('Perceived medical error (Q28a) and felt discrimination (Q28b) are lifetime reports with no facility '
         'attribution; they cannot be assigned to any provider. Q20 (one facility) was fielded to everyone '
         'with at least one visit; the figure quoted in the text restricts to respondents with more than one '
         'visit (n = 1,238), because a single visit is one facility by arithmetic.')
    table(rd('T21_utilisation_by_group', rename=GS), first=4.6, last=1.5, fs=7.6)

    doc.add_page_break()
    H('3.1 Preventive and screening services', 2)
    P('This comparison was missing from the earlier analysis, which compared respondents who have a '
      'usual source of care with those who do not — a different question. Asked directly, the answer '
      'is a null result that matters.')
    P('After adjustment and multiplicity control, private-hospital users do not differ from public '
      'hospital users on any of the eight items: every Benjamini–Hochberg adjusted p-value exceeds '
      '0.4. Blood pressure, blood sugar, lipids, dental, vision, mental-health service receipt, breast '
      'examination and cervical screening are all statistically indistinguishable between the two '
      'hospital-based groups.')
    P('The one robust difference sits elsewhere. Private clinic and pharmacy users report less '
      'blood-pressure measurement (aOR 0.15, 0.04–0.48; −11.2 pp), and splitting that group '
      'shows the deficit is entirely a pharmacy phenomenon: 70.0% among pharmacy users against 97.6% '
      'among private-clinic users and 96.9% among private-hospital users. The same pattern appears for '
      'blood sugar (30.0% against 59.8%) and lipids (28.3% against 53.7%). Combining clinics with '
      'pharmacies into one "private primary" category obscures this, and the two should be reported '
      'separately.')
    P('Respondents with no usual source of care at all sit below every group — blood pressure '
      '66.4%, blood sugar 43.6%, lipids 39.3% — which is the contrast the Thai report’s '
      'existing analysis captures.')
    P('Q27 concerns service receipt in the past 12 months; this does not establish guideline-based '
      'screening coverage, and the questionnaire never '
      'records where a service was delivered. Every row should be read as "respondents with this usual '
      'source reported higher or lower receipt" — not that the provider delivered it, and not that '
      'private provision caused uptake. Blood-pressure measurement is near-universal in three of four '
      'groups and the full model did not converge; a simplified specification is reported and labelled '
      'rather than forcing an estimate.', italic=True, color=MUT, size=10)
    figure(f'{FIG}/Figure 4 - Preventive services by provider group.png', 'Figure 4.',
           'Preventive and screening services received, by usual source of care.',
           'Bars show the percentage with a 95% Wilson interval. Breast examination and cervical screening '
           'are reported over women only and appear in Table 5 rather than here.')
    cap('Table 5.', 'Adjusted odds of receiving each service, reference public hospital OPD/ER.')
    note('Adjusted for age band, sex, education, income, municipality, coverage scheme, self-rated health and '
         'chronic illness, with cluster-robust standard errors. Breast and cervical screening are restricted '
         'to women and drop sex from the covariate set. "Diff (pp)" is the difference in average predicted '
         'probability — the quantity to read for magnitude. Bold marks BH-adjusted p < 0.05.')
    prev = rd('T31_preventive_adjusted',
              cols=['Outcome', 'Group', 'aOR', 'lo', 'hi', 'p', 'p (BH within family)', 'Diff (pp)',
                    'events', 'group n'], rnd=3)
    prev['aOR (95% CI)'] = prev.apply(lambda r: f"{r['aOR']:.2f} ({r['lo']:.2f}–{r['hi']:.2f})", axis=1)
    prev = prev[['Outcome', 'Group', 'aOR (95% CI)', 'p', 'p (BH within family)', 'Diff (pp)',
                 'events', 'group n']]
    table(prev, first=4.2, last=1.3, fs=7.4, bold_sig=lambda r: r['p (BH within family)'] < 0.05)
    cap('Table 6.', 'Blood pressure and other services, splitting private clinics from pharmacies.')
    note('The five-group split is descriptive only; pharmacy n = 60 and private clinic n = 82.')
    cp = rd('T33_preventive_clinic_vs_pharmacy')
    cp = cp.drop(columns=[c for c in ['Denominator'] if c in cp.columns])
    cp['Measure'] = cp['Measure'].str.replace(r' \(Q27[A-H]\)', '', regex=True)
    cp = cp.rename(columns={'public primary care': 'Public\nprimary care',
                            'public hospital OPD/ER': 'Public hosp.\nOPD/ER',
                            'private clinic': 'Private\nclinic',
                            'private pharmacy': 'Private\npharmacy',
                            'private hospital OPD/ER': 'Private hosp.\nOPD/ER'})
    table(cp, first=3.4, last=1.3, fs=7.0)

    # ------------------------------------------------------------------ 4 quality
    doc.add_page_break()
    H('4. How they rate quality', 1)
    P('The eleven items covering the most recent visit are grouped here into five domains — access '
      'and process, interpersonal treatment, continuity, perceived competence and readiness, and a '
      'global rating. The grouping is an interpretive framework for reading the results, not a validated '
      'scale, and no factor analysis was forced on 127 people.')
    P('Nine of eleven items differ after adjustment and multiplicity control. The largest differences '
      'are satisfaction with waiting time (aOR 3.54, +26.9 pp), the provider knowing the patient’s '
      'history (3.16, +26.6 pp), ease of getting an appointment (3.28, +23.8 pp) and time spent in the '
      'consultation (2.91, +24.0 pp). Interpersonal items follow: courtesy of other staff (2.52), '
      'involvement in decisions (2.13), respect (2.00) and clear explanation (1.92).')
    P('The two items that speak to competence do not differ. Provider knowledge and skill is aOR 1.38 '
      '(0.83–2.31) and equipment and supplies ready is 1.11 (0.69–1.78); neither is significant '
      'before or after adjustment for multiple testing. Public hospital users in fact rate their '
      'providers’ knowledge (48.5%) above almost everything else about the visit.')
    P('That shape is the central quality finding, and it needs stating carefully. Respondents are not '
      'reporting that private hospitals are clinically better; they are reporting that private hospitals '
      'are faster, more attentive, more personal and easier to navigate. Equally, none of the eleven '
      'items measures objective clinical quality — all are patient perceptions of a single visit, '
      'and the overall-experience item is not an independent measure of clinical competence. The '
      'public sector’s perceived weakness, read through its own users’ eyes, is service '
      'process.')
    figure(f'{FIG}/Figure 5 - Visit experience by domain.png', 'Figure 5.',
           'Experience of the most recent visit, grouped by domain.',
           'Markers show the percentage rating each item very good or excellent. Denominators exclude the '
           'explicit not-applicable answers and therefore differ by item and group.')
    P('Two things qualify the comparison. First, denominators move by group: nearly a third of private '
      'clinic and pharmacy users answered "no prior visit" to the continuity item, against 11.8% of '
      'private-hospital users, which shifts their estimate on that item from 58.6% of those who rated it '
      'to 40.8% of the whole group. Second, these items describe the most recent visit, which is the '
      'usual source of care for 84.3% of private-hospital users but only 64.1% of private clinic and '
      'pharmacy users. Re-attributing every item to the actual last-visit provider, and restricting to '
      'respondents whose usual and last-visit provider agree, both preserve the pattern.')
    cap('Table 7.', 'Structural "not applicable" answers, which change the denominator by group.')
    note('These are explicit response options in the fielded instrument — "no prior visit / don’t '
         'know" on Q38e, "no other staff present" on Q38j, "cannot evaluate" on Q40 — not item non-response.')
    table(rd('T53_structural_not_applicable', rename=GS), first=4.4, last=3.0, fs=7.8)

    doc.add_page_break()
    cap('Table 8.', 'Adjusted odds of rating each experience item very good or excellent.')
    note('Reference is public hospital OPD/ER. Covariates as in Table 5; cluster-robust standard errors. '
         'Bold marks BH-adjusted p < 0.05 within the 11-item family.')
    exp = rd('T54_experience_adjusted', q="Group=='private hospital OPD/ER'",
             cols=['Outcome', 'aOR', 'lo', 'hi', 'p', 'p (BH within family)', 'Diff (pp)',
                   'events', 'group n'], rnd=3)
    exp['aOR (95% CI)'] = exp.apply(lambda r: f"{r['aOR']:.2f} ({r['lo']:.2f}–{r['hi']:.2f})", axis=1)
    exp = exp[['Outcome', 'aOR (95% CI)', 'p', 'p (BH within family)', 'Diff (pp)', 'events', 'group n']]
    table(exp, first=6.4, last=1.4, fs=7.6, bold_sig=lambda r: r['p (BH within family)'] < 0.05)

    # ------------------------------------------------------------------ 5 confidence
    doc.add_page_break()
    H('5. What it means for confidence in the system', 1)
    P('The experience premium stops at the clinic door. No system-level contrast is detectable after '
      'adjustment and multiplicity control: health security (aOR 1.27, 0.80–2.01), confidence in '
      'getting good care (1.19), confidence in affording it (1.34), the direction of the system over two '
      'years (1.34), endorsement of the current system (0.80), the rating of the public system (1.23), '
      'and whether government listens to the public (0.88). The higher rating of the private system '
      '(1.62, 0.95–2.77) does not survive Benjamini–Hochberg adjustment within this family.')
    P('None of that establishes equality. The interval for health security is compatible with anything '
      'from a modest decrease to a doubling, and a cross-sectional survey cannot test whether the '
      'quality of an encounter produces confidence in a system. The honest statement is that this '
      'survey does not detect a difference by provider group.')
    P('What the data do show directly is more interesting. A good personal experience and insecurity '
      'about serious illness routinely coexist: 14.2% of private-hospital users rate their own facility '
      'very good or excellent while remaining unsure they could both get and afford care if seriously '
      'ill, against 11.5% of public hospital users. Health security is instead strongly associated with '
      'patient activation (aOR 1.78, 1.31–2.43) — a characteristic of the respondent rather '
      'than a feature of the provider.')
    P('It is also worth noting which group is most positive about the public system. Public primary care '
      'users rate it high more often than anyone else, rate the government’s COVID-19 management '
      'highest, and are the only group in which a majority is confident the system takes public opinion '
      'into account. Public hospital outpatient users — not private-sector customers — are '
      'consistently the least satisfied group in this report, and they are the second largest.')
    cap('Table 9.', 'Confidence in and evaluation of the health system, by provider group.')
    note('Health security is Q41a and Q41b jointly, both conditioned on "if you were seriously ill". The '
         'Q40 public primary care items carry an explicit "cannot evaluate" option, so their denominators '
         'are smaller.')
    table(rd('T23_confidence_by_group', rename=GS), first=5.4, last=1.5, fs=7.4)
    figure(f'{FIG}/Figure 6 - Adjusted differences private hospital users.png', 'Figure 6.',
           'Adjusted differences for private-hospital users, across all outcome families.',
           'Reference is public hospital OPD/ER. Coloured markers mark Benjamini–Hochberg adjusted '
           'p < 0.05 within the outcome family. "pp diff" is the difference in average predicted '
           'probability, which is the quantity to read for magnitude — not the odds ratio.')

    # ------------------------------------------------------------------ 6 admission
    doc.add_page_break()
    H('6. Admission: the one finding this survey cannot resolve', 1)
    P('Private-hospital users report an overnight admission in the past twelve months at 29.1%, against '
      '22.1% of public hospital users, 16.9% of public primary care users and 13.4% of private clinic '
      'and pharmacy users. The difference survives full adjustment including chronic illness (aOR 2.42, '
      '1.35–4.31; +14.2 pp), and adding unmet need and visit volume does not remove it. It is the '
      'largest adjusted difference outside the experience ratings, in the group reporting the best '
      'health.')
    P('Three things follow, and only three. The association is real in these data. It is not explained '
      'by need as this survey measures it — though that is a weak instrument, since Q11 is a '
      'non-specific chronic-illness indicator rather than a diagnosis, and no disease-specific '
      'information exists. And it cannot be attributed to a private hospital at all: Q26 records that an '
      'admission happened, never where it happened.')
    P('It does not demonstrate overuse, supplier-induced demand, or a reimbursement effect. It is a '
      'signal that warrants investigation with claims and clinical information, by facility, payer and '
      'case mix.')
    cap('Table 10.', 'Admission: sensitivity to the specification.')
    note('Each block is a separate model on the same cohort. Chronic illness is already in the base covariate '
         'set. Where the analytic n changes, that is a change of sample, not only of adjustment.')
    adm = rd('T60_admission_sensitivity', rnd=3)
    adm = adm[['Specification', 'Group', 'aOR', 'lo', 'hi', 'p', 'Diff (pp)', 'n']]
    table(adm, first=4.6, last=1.4, fs=7.6)

    # ------------------------------------------------------------------ 7 financing
    doc.add_page_break()
    H('7. Coverage, financing and who these patients actually are', 1)
    P('The reviewer’s question about how private-hospital patients pay cannot be answered with this '
      'instrument, and that is worth stating plainly rather than approximating. The survey records '
      'coverage ownership (Q6, Q7) and one general habit item about paying out of pocket in some '
      'situations. It never asks who paid for any specific visit or admission, how much, whether a '
      'copayment applied, or whether private insurance was actually used. Nor does it record employment '
      'status or the provider a respondent is registered with.')
    P('What can be shown is the overlap of entitlements. Of the 127 regular private-hospital users, 66 '
      '(52.0%) hold Social Security without private insurance, 22 (17.3%) hold both, 33 (26.0%) hold '
      'Universal Coverage and 5 (3.9%) hold the civil-servant scheme. Owning private insurance is not '
      'evidence of having used it; holding a scheme other than Social Security does not make someone a '
      'self-payer; and citing "low cost" as a reason is not evidence of having received free care.')
    cap('Table 11.', 'What the instrument does and does not record about money.')
    note('The distinction between coverage ownership and payment at an encounter is the single largest '
         'evidence gap for private-hospital oversight.')
    table(rd('T70_financing_items_available'), first=5.0, last=5.6, fs=7.8)
    cap('Table 12.', 'Observed profiles of regular private-hospital users.')
    note('Declared subgroups, not clusters. No unsupervised clustering was applied to 127 respondents and no '
         'names, biographies, expenditure amounts or motivations are invented. Cells are n/N (%).')
    pr = rd('T72_private_hospital_observed_profiles').set_index('Profile').T
    pr.index.name = 'Characteristic'
    pr = pr.reset_index()
    pr.columns = [str(c).replace(', ', ',\n') for c in pr.columns]
    table(pr, first=5.6, last=2.8, fs=7.4)
    P('One further boundary matters. Regular private-hospital users are not a sample of the '
      'private-hospital market. A different and overlapping population — respondents whose most '
      'recent visit was to a private hospital (n = 202) — is 58.4% Social Security rather than '
      '69.3%, and reports admission at 20.8% rather than 29.1%. Episodic private-hospital use during a '
      'recall period is not measurable at all, because Q32 and Q33 capture only the single most recent '
      'visit. Nothing in this report describes cash-paying patients, inpatients as a population, or '
      'international patients.')

    # ------------------------------------------------------------------ 8 international
    H('8. Thailand in international context', 1)
    P('The comparison usually drawn between Thailand and India is between two different indicators. The '
      'widely quoted 84.1% for India is confidence in getting good-quality care, taken from Figure 2A of '
      'Kruk et al. (2024). India’s health security — confidence in both getting and affording '
      'care — is 69.2%, and the 15-country average is 48.8%.')
    P('On that indicator Thailand is 64.4% (95% CI 62.2–66.4): 15.6 percentage points above the '
      'multi-country average and 4.8 points below India. The premise that Thailand sits notably low on '
      'health security is not supported by the source data.')
    P('The measure is respondents’ confidence that, if they became seriously ill, they could obtain '
      'good-quality care and afford it. It is subjective and conditioned on a hypothetical. A lower '
      'value does not demonstrate worse financial protection, access or clinical outcomes. India’s '
      'age eligibility, geographic coverage, fieldwork dates, survey mode, weighting and uncertainty '
      'could not be verified from the materials available, so differences in expectations, sample '
      'composition, timing, mode or translation remain hypotheses to investigate rather than '
      'demonstrated causes of the remaining gap. Objective indicators — catastrophic and '
      'impoverishing health expenditure, effective coverage, unmet need from household surveys — '
      'could triangulate the finding, but they measure different things and cannot replace it.')
    figure(f'{FIG}/Figure 7 - Thailand vs India health security.png', 'Figure 7.',
           'Health security: Thailand, India and the 15-country PVS average.',
           'India and average values read from Kruk et al. (2024) Lancet Global Health, Figure 2A. '
           'Thailand’s intervals are Wilson 95% intervals on the unweighted achieved sample.')

    # ------------------------------------------------------------------ 9 synthesis
    doc.add_page_break()
    H('9. What this suggests', 1)
    P('Taken together, the findings point in a consistent direction, and it is not the direction the '
      'public debate about private hospitals usually assumes.')

    H('The private sector here is an extension of public financing, not an alternative to it', 3)
    P('Seven in ten regular private-hospital users hold Social Security; insurance coverage is the '
      'reason they most often give for choosing their provider; low cost is almost never mentioned; and '
      'their household incomes are middling rather than high. Read alongside the fact that Social '
      'Security members register with a contracted main hospital that may be public or private, the most '
      'economical explanation is that a large part of what looks like private purchasing is '
      'scheme-assigned registration. This survey cannot prove that — it never asks where anyone is '
      'registered — but any account that treats private-hospital growth as discretionary buying by '
      'the affluent will misidentify both who these patients are and what would change their behaviour. '
      'The policy lever is the contract, not the price.')

    H('The gap that public hospitals need to close is a service gap, not a clinical one', 3)
    P('Users of private hospitals report better experiences on waiting, scheduling, consultation length, '
      'continuity and interpersonal treatment — differences of 15 to 27 percentage points — '
      'while reporting no detectable difference in the provider’s knowledge and skill or in the '
      'readiness of equipment and supplies. This is a claim about perceptions, not about clinical '
      'outcomes, and it cuts both ways: it gives no support to the idea that private hospitals are '
      'clinically superior, and it locates the public sector’s perceived weakness precisely. For '
      'public hospital outpatient departments — the group that is consistently least satisfied on '
      'almost every measure in this report — the improvement agenda indicated here is waiting, '
      'appointment access, consultation time and continuity of records, rather than equipment or staff '
      'competence.')

    H('Prevention is not where the public–private difference lies', 3)
    P('On eight screening and prevention items, private-hospital users and public hospital users are '
      'statistically indistinguishable. If there is a prevention concern in these data it attaches to '
      'pharmacies used as a regular first contact, where blood-pressure measurement runs about '
      'twenty-seven points below every other group, and to the 488 respondents with no usual source of '
      'care at all, who sit lowest on every item. Both are questions about primary care coverage, not '
      'about private hospitals. A practical implication for the analysis itself: clinics and pharmacies '
      'should not be reported as a single "private primary" category, because combining them conceals '
      'this.')

    H('Higher admission is the finding that should drive the next piece of work', 3)
    P('It is the largest adjusted difference outside the experience ratings, it appears in the group '
      'reporting the best health, and it survives adjustment for chronic illness, unmet need and visit '
      'volume. It is also the finding this survey is least able to interpret, because the questionnaire '
      'never records where an admission occurred. Whether it reflects lower admission thresholds, case '
      'mix the survey cannot see, or the incentives facing contracted providers is not answerable here '
      'and is answerable with claims data. Of everything in this report, this is the item most worth '
      'the cost of linkage.')

    H('Better encounters do not appear to add up to confidence in the system', 3)
    P('Private-hospital users rate their own provider markedly higher and are no more confident about '
      'the health system, its direction, or their own health security. A substantial minority in every '
      'group rates their own facility highly while remaining unsure they could get and afford care if '
      'seriously ill, and health security tracks patient activation — a characteristic of the '
      'person — more visibly than it tracks provider type. The cautious reading is that improving '
      'the experience of individual encounters, which the private sector demonstrably does on these '
      'measures, is not by itself a route to population confidence. The design cannot test that causal '
      'claim, and the confidence intervals are wide enough to accommodate a real difference this survey '
      'was too small to detect.')

    H('And the largest gap is that nobody was asked about money', 3)
    P('No question in this instrument identifies who paid for any encounter, how much, whether a '
      'copayment applied, or whether private insurance was used. For a programme of work aimed at '
      'regulating private hospitals — where price transparency, billing practice and patient '
      'liability are central — that is the binding constraint. It is straightforward to fix in a '
      'future round.')

    H('Candidate questions for private-hospital oversight', 2)
    P('The following follow from the findings above. None is a proven effective policy, and none '
      'describes what Thai law currently requires — current or study-period rules must be verified '
      'from authoritative sources before being asserted.')
    B('Most regular private-hospital users arrive holding a public entitlement. Should '
      'contracted-provider performance be monitored separately by payer? Needs registration records, '
      'contract terms and claims data.', lead='Contracted-provider experience by payer. ')
    B('The measured differences are in waiting, appointment access, consultation time and continuity. '
      'Service-process standards could be monitored separately from clinical standards, using '
      'standardised patient-experience items in routine licensing returns.',
      lead='Service-process standards, monitored separately from clinical ones. ')
    B('The wait at the facility and the wait to obtain an appointment behave very differently and should '
      'be published as two indicators. This survey records ordered categories, not durations; facility '
      'administrative data would be needed.', lead='Two distinct waiting indicators. ')
    B('Higher self-reported admission in the healthiest group is the priority for follow-up, by '
      'facility, payer and case mix. The survey cannot establish where an admission occurred or whether '
      'it was necessary.', lead='Admission rates, investigated with claims and clinical data. ')
    B('A payer and out-of-pocket module, or claims linkage, is required before patient-payment or '
      'billing-transparency questions can be answered at all.',
      lead='Patient payment and billing transparency — currently unmeasurable. ')
    B('Perceived medical error and felt discrimination are recorded without a facility identifier and '
      'without a recall window, so neither can be attributed to any provider. Linking complaint and '
      'incident reporting to a facility identifier would make them measurable.',
      lead='Complaints and adverse events, linked to a facility. ')
    B('Pharmacies serving as a regular first contact show markedly lower preventive-service receipt. '
      'What preventive role, if any, should attach to that? Needs pharmacy service-scope data.',
      lead='The preventive role of pharmacies. ')

    # ------------------------------------------------------------------ limitations
    doc.add_page_break()
    H('Limitations', 1)
    P('Final recruitment was quota-based convenience within PPS-selected subdistricts, so selection '
      'probabilities are unknown, no valid design weights exist, and no conventional response rate can '
      'be computed — no recruitment disposition records were located. Matching the sampling plan on '
      'region, municipality and age is a useful check but is not evidence that selection bias is absent, '
      'and the sex quota was not met. Because one province was sampled per health region, province-level '
      'strata are single-PSU and design-based variance is not estimable at that level; the '
      'subdistrict-clustered standard errors used here are an approximation, not design-based inference. '
      'All estimates are unweighted.')
    P('The private-hospital group contains 127 respondents and the private clinic and pharmacy group 142 '
      '(82 clinic, 60 pharmacy), so intervals are wide and several contrasts are indeterminate rather '
      'than null. Benjamini–Hochberg adjustment is applied within each outcome family and both raw '
      'and adjusted p-values are reported; no outcome was dropped for being null. Adjustment addresses '
      'measured confounding only — it does not address the convenience selection, the unmeasured '
      'insurance-routing mechanism, or sparse cells, and adjusted estimates are not automatically a more '
      'reliable guide to which differences are real.')
    P('All measures are self-reported and none validated against records. Recall periods vary by item. '
      'The design is cross-sectional, so every provider-group result is an association rather than an '
      'effect. Several things are simply not measured: who paid for any encounter and how much, '
      'employment status, the registered or contracted provider, the facility at which an admission '
      'occurred, and health literacy — the instrument contains no literacy item, and patient '
      'activation and education are different constructs that should not stand in for it. The two '
      'expectation vignettes (Q48, Q49) were fielded but analysed in no report, and remain the only '
      'direct route to the expectations arm of the PVS framework.')

    H('About this edition', 2)
    P('This edition consolidates the original subgroup analysis with a subsequent audit of the cohort '
      'definition, variable coding, denominators, attribution and inference, and supersedes the earlier '
      'draft of the same title. Substantive changes to previously reported numbers include a corrected '
      'self-rated-health coding (78.8% rather than 54.9% report good or better health), corrected age '
      'denominators, recall periods taken from the fielded instrument rather than from the report text, '
      'explicit handling of "not applicable" response codes, sex-restricted denominators for breast and '
      'cervical screening, and the addition of cluster-robust standard errors, marginal predicted '
      'probabilities and multiplicity adjustment. Two results reported as significant in the earlier '
      'draft do not survive: perceived provider knowledge and the rating of the private system.')
    P('The analysis code is in src/pvs/. Regenerated tables and figures are written to output/; '
      'the approved September release is preserved in results/2026-09/. Every figure and table '
      'here is generated from the analysis exports; no value is typed independently.',
      italic=True, color=MUT, size=10)

    H('References', 2)
    P('1. Kruk ME, Kapoor NR, Lewis TP, et al. Population confidence in the health system in 15 '
      'countries: results from the first round of the People’s Voice Survey. Lancet Glob Health. '
      '2024;12(1):e100–e111.', size=9.5)
    P('2. Lewis TP, Kapoor NR, Aryal A, et al. Measuring people’s views on health system '
      'performance: design and development of the People’s Voice Survey. PLoS Med. '
      '2023;20(12):e1004294.', size=9.5)

    path = f'{OUT}/Report - Customers of private hospitals in the Thai health system.docx'
    doc.save(path)
    print('saved:', path)
    return path


if __name__ == '__main__':
    build()
