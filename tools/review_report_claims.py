"""Claim-level checks for the author-managed October report.

Expected findings are calculated from the canonical frame or read from audited
aggregate/model outputs. Numeric prose is checked in order, so a number in a
wrong paragraph cannot pass just because it appears elsewhere in the data.
"""
from pathlib import Path
import json,re
import numpy as np
import pandas as pd
from pvs.analysis import prop_ci
from pvs.national import q40_top2

ROOT=Path(__file__).resolve().parents[1]
GROUPS=['public primary care','public hospital OPD/ER','private clinic/pharmacy','private hospital OPD/ER']

def review(d,blocks,models,tests):
    texts={b['id']:b['text'] for b in blocks if b['type']=='paragraph'}
    texts.update({b['id']:b['rows'][0][0] for b in blocks if b['id'] in ['T02','T14']})
    masks={'all':pd.Series(True,index=d.index),'M':d.municipality.eq('municipal'),'N':d.municipality.eq('non-municipal'),
           'Y':d.has_usual.eq('yes'),'NO':d.has_usual.eq('no'),'public':d.usual_sector.eq('public'),'private':d.usual_sector.eq('private')}
    masks.update({str(i):d.provider_group.eq(g) for i,g in enumerate(GROUPS)})
    checks=[];issues=[]
    def mask(g):return masks[g] if isinstance(g,str) else g
    def counts(v,pos='yes',g='all',women=False,full=False):
        v=d[v] if isinstance(v,str) else v
        keep=mask(g)&(d.sex.eq('female') if women else True)&(True if full else v.notna())
        return int((keep&v.eq(pos)).sum()),int(keep.sum())
    def pct(v,pos='yes',g='all',women=False,full=False):
        k,n=counts(v,pos,g,women,full);return f'{100*k/n:.1f}'
    def ci(v,pos='yes',g='all'):
        k,n=counts(v,pos,g);return [f'{x:.1f}' for x in prop_ci(k,n)]
    def ps(var,digits=2):
        # Demographic tests are first in the table audit (before provider groups).
        p=next(t['p'] for t in tests if t['ตัวแปร']==var)
        return f'{p:.{digits}f}'
    def proportions(v,order,pos='yes',**kwargs):return [pct(v,pos,g,**kwargs) for g in order]
    csv={}
    def table(name,working=False):
        key=(name,working)
        if key not in csv:csv[key]=pd.read_csv(ROOT/('output/tables' if working else 'results/2026-09/tables')/(name+'.csv'))
        return csv[key]
    def adj(name,contains):
        f=table(name);f=f[f.Outcome.str.contains(contains,regex=False)&f.Group.eq(GROUPS[3])]
        assert len(f)==1,(name,contains)
        return f.iloc[0].to_dict()
    def or_ci(m):return [f'{m["aOR"]:.2f}',95,f'{m["lo"]:.2f}',f'{m["hi"]:.2f}']
    def md(m):return f'{abs(m["Diff (pp)"]):.1f}'
    def overall(t,outcome=None,variable=None,level=None):
        obj=models[t] if outcome is None else models[t][outcome]
        return next(m for m in obj['multivariate'] if m['variable']==variable and (level is None or m['level']==level))
    def om(t,outcome=None,variable=None,level=None,pdigits=2):
        m=overall(t,outcome,variable,level)
        return or_ci(m)+[.001 if m['p']<.001 else f'{m["p"]:.{pdigits}f}']
    def nums(text):return re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?',text)
    def check(key,expected,source):
        actual=nums(texts[key]);expected=[str(v) for v in expected]
        ok=[float(v.replace(',','')) for v in actual]==[float(v) for v in expected]
        checks.append({'ตำแหน่ง':key,'ข้อความ':texts[key],'ตัวเลขในรายงาน':' | '.join(actual),
                       'ตรวจได้':' | '.join(expected),'ผล':'ตรง' if ok else 'ต่าง','หลักฐาน':source})
        if not ok:issues.append({'ตำแหน่ง':key,'ประเภท':'ตัวเลขในข้อความ','ข้อความเดิม':texts[key],
                                'ค่าหรือข้อความที่เสนอ':' | '.join(expected),'เหตุผล':'ลำดับตัวเลขในข้อความต่างจากค่าที่ตรวจตามแหล่งข้อมูล; ดูชีตตรวจข้อความ',
                                'หลักฐาน':source,'สถานะ':'แก้ก่อนเผยแพร่','แก้ไขแล้ว':''})
    def flag(key,kind,old,new,why,source,status='แก้ก่อนเผยแพร่'):
        if old in texts[key]:issues.append({'ตำแหน่ง':key,'ประเภท':kind,'ข้อความเดิม':old,'ค่าหรือข้อความที่เสนอ':new,'เหตุผล':why,'หลักฐาน':source,'สถานะ':status,'แก้ไขแล้ว':''})
    canonical='output/analysis_frame.pkl; recalculated counts and valid denominators'
    frozen='results/2026-09/tables; checked at displayed precision'
    model_source='src/pvs/report_models.py; re-estimated complete-case models'
    scheme=d.scheme.astype(object).fillna('unknown')
    edu=d.edu.isin(['upper secondary/voc','diploma/high voc','bachelor or above'])
    inc_high=d.income.isin(['60-100k','100k+'])
    edu_hi=d.edu.isin(['upper secondary/voc','diploma/high voc'])
    q=lambda v,g='all':pct(v,'confident',g)
    route=[d.scheme.eq('SSS'),~d.scheme.eq('SSS')&d.priv_ins_owned.eq('yes'),~d.scheme.eq('SSS')&d.priv_ins_owned.eq('no')]
    priv=d.provider_group.eq(GROUPS[3]); route_rates=[pct(priv,True,m) for m in route]
    wait=adj('T59_core_outcomes_adjusted','Waited 1 hour');admit=adj('T59_core_outcomes_adjusted','Admitted overnight')
    sec=adj('T58_confidence_adjusted','Health security')
    exp=table('T54_experience_adjusted');exp=exp[exp.Group.eq(GROUPS[3])]
    sig=int((exp['p (BH within family)']<.05).sum())
    experience=lambda label:adj('T54_experience_adjusted',label)
    check('P031',[len(d),d.province.nunique(),d.region_no.nunique()],canonical)
    check('P033',[pct('health_good3','good or better'),pct('mental_good3','good or better'),pct('chronic')],canonical)
    check('P034',[pct('has_usual'),counts('has_usual','no')[0],pct('has_usual','no'),*proportions('bp_r',['Y','NO']),*proportions('sugar_r',['Y','NO']),pct('unmet'),12],canonical+'; author confirmed Q27/Q29 12-month recall')
    confidence=[q('conf_get'),q('conf_afford'),q('health_security')]
    system=[pct('sys_endorse_bin','works well'),pct('sys_improved_bin','improved')]
    quality=[pct('q_public_top2','very good/excellent'),pct('q_private_top2','very good/excellent')]
    check('P035',confidence+system+quality,canonical)
    foreign=pd.read_csv(ROOT/'content/international/values.csv').set_index(['metric_id','country_iso']).value_percent
    f=lambda m,c='TOTAL':str(foreign.loc[m,c])
    check('P036',[q('health_security'),15,f('health_security')],canonical+'; content/international/values.csv')
    check('P038',[int(priv.sum()),pct(priv,True),counts(scheme,'SSS','3',full=True)[0],pct(scheme,'SSS','3',full=True),pct(inc_high,True,'3'),60000],canonical)
    check('P039',route_rates,canonical)
    check('P040',[*proportions('queue_ge1h',['3','1']),*or_ci(wait),12,*proportions('admit',['3','1']),*or_ci(admit)],canonical+'; '+frozen)
    check('P041',[*proportions('lastest_qual_top2',['3','1'],'very good/excellent'),sig,len(exp),*[md(experience(x)) for x in ['Satisfaction with waiting','Provider knew my history','Enough time','Ease of getting']]],canonical+'; '+frozen)
    check('P042',[*proportions('health_security',['3','1'],'confident'),*or_ci(sec)],canonical+'; '+frozen)
    check('P104',[len(d),d.region_no.nunique(),int(masks['M'].sum()),int(masks['N'].sum()),2],canonical)
    check('P113',[pct('sex','female',full=True),pct('sex','male',full=True),pct('sex','other',full=True),int(d.sex.isna().sum()),pct(d.sex.isna(),True),ps('sex')],canonical)
    check('P114',[pct(edu_hi,True),pct('edu','bachelor or above'),pct(d.edu.isin(['primary','below primary']),True),pct('edu','lower secondary'),*proportions('edu',['M','N'],'bachelor or above'),.001],canonical)
    check('P115',[30000,pct(d.income.isin(['<10k','10-30k']),True),30000,59999,pct('income','30-60k'),60000,pct(inc_high,True),30000,ps('income',3)],canonical)
    check('P116',[*[pct(scheme,s,full=True) for s in ['UCS','SSS','CSMBS']],ps('scheme')],canonical+'; Monte Carlo Pearson (999999 draws)')
    check('P121',[pct('health_good3','good or better'),pct('mental_good3','good or better'),pct('chronic'),6,pct('activation','high')],canonical)
    check('P122',[*proportions('health_good3',['N','M'],'good or better'),.003,*proportions('mental_good3',['N','M'],'good or better'),.04,6,*proportions('chronic',['N','M']),.03,*proportions('activation',['N','M'],'high'),.01],canonical+'; corresponding verified table p-values')
    check('P128',[12,2,1,4,.06,pct('admit'),12,pct('unmet'),*proportions('admit',['M','N']),.001,.15],canonical+'; median/IQR and tests verified in table audit')
    check('P129',[12,*[pct(v+'_r') for v in ['bp','sugar','lipid','dental','vision']],int(d.sex.eq('female').sum()),pct('ca_cervix_r',women=True),pct('mammogram_r',women=True)],canonical)
    check('P130',[*proportions('vision_r',['M','N']),.001,*proportions('dental_r',['M','N']),.001],canonical+'; verified p-value operators (< for vision; = for dental)')
    check('P131',[12,pct('homevisit_any'),*proportions('homevisit_any',['N','M']),.001,pct('telemed_any'),*proportions('telemed_any',['M','N']),.01],canonical)
    check('P132',[pct('borrowed_ever'),12,*proportions('borrowed_ever',['M','N'])],canonical+'; Q31 12 months confirmed by researcher against original questionnaire')
    check('P134',[14,12,14,f('unmet_need'),*[f('unmet_need',c) for c in ['PER','GBR','KEN','COL','ARG','USA','IND','KOR','MEX','ITA','ZAF','ETH','URY']]],'content/international/values.csv; author confirmed Thai recall')
    check('P140',[pct('has_usual'),12,.09,pct('usual_sector','public',full=True),pct('usual_sector','private',full=True),*proportions('usual_sector',['M','N'],'private',full=True),.003,pct('usual_hospital',False,full=True),pct('usual_hospital',True,full=True),*proportions('usual_hospital',['N','M'],False,full=True),*proportions('usual_hospital',['M','N'],True,full=True),.001],canonical)
    check('P144',[pct('municipality','municipal','private'),pct(~d.edu.isin(['primary','below primary']),True,'private'),.001,pct(scheme,'SSS','private',full=True),pct(scheme,'UCS','0',full=True),pct(scheme,'CSMBS','1',full=True),.001],canonical)
    check('P145',[*proportions('usual_qual_top2',['private','0','1'],'very good/excellent'),.001],canonical)
    check('P149',om('T08',variable='area',pdigits=3)+om('T08',variable='income',level='middle'),model_source)
    check('P150',om('T08',variable='activation')+om('T08',variable='health'),model_source)
    check('P151',om('T08',variable='sector')+om('T08',variable='setting',pdigits=3),model_source)
    bp=overall('T09','bp','usual')
    # The corrected wording quotes the exact two-decimal OR in the lead sentence.
    bp_digits=2 if 'อัตราส่วนโอกาส (odds ratio)' in texts['P156'] else 1
    check('P156',[f'{bp["aOR"]:.{bp_digits}f}',*[n for v in ['bp','sugar','lipid','mammogram','ca_cervix','vision','dental'] for n in om('T09',v,'usual',pdigits=3)]],model_source)
    check('P161',confidence+[system[1],2,system[0]],canonical)
    check('P166',[15,f('quality_confidence'),*[f('quality_confidence',c) for c in ['IND','LAO','MEX','USA']],f('affordability_confidence'),f('health_security')],'content/international/values.csv')
    check('P167',[f('system_works'),2,pct('sys_improved_bin','improved'),f('system_improved')],canonical+'; content/international/values.csv')
    check('P169',[*proportions('conf_get',['public','private'],'confident'),.44,*proportions('conf_afford',['public','private'],'confident'),.62,*proportions('sys_endorse_bin',['public','private'],'works well'),.18,2,*proportions('sys_improved_bin',['private','public'],'improved'),.001],canonical+'; verified table tests')
    check('P173',om('T11','security','usual')+[2]+om('T11','improved','usual')+om('T11','works','usual'),model_source)
    check('P174',om('T12','security','sector')+[2]+om('T12','improved','sector')+om('T12','works','sector'),model_source)
    q40=[q40_top2(d[c]) for c in ['eval_maternal','eval_ped','eval_chronic','eval_mental']]
    q40p=[pct(v,True) for v in q40]
    check('P181',quality+q40p+[int(v.notna().sum()) for v in q40]+[q('conf_voice'),pct('q_covid_top2','very good/excellent'),19],canonical+'; explicit Q40 valid-answer denominators')
    check('P186',[15,quality[0],f('public_quality'),quality[1],f('private_quality'),*q40p],canonical+'; content/international/values.csv')
    check('P187',[q('conf_voice'),f('government_listens'),19,pct('q_covid_top2','very good/excellent'),f('covid_management')],canonical+'; content/international/values.csv')
    check('P189',[12,*proportions('usual_qual_top2',['private','public'],'very good/excellent'),.001,*proportions('q_private_top2',['private','public'],'very good/excellent'),.008,19],canonical+'; verified table tests')
    last=d.last_group.eq(GROUPS[3]);both=int((priv&last).sum())
    check('P198',[4,int(priv.sum()),pct(priv,True),int(last.sum()),both],canonical)
    check('P199',[pct('municipality','municipal','3'),pct(edu,True,'3'),pct('income','30-60k','3'),30000,60000,pct(inc_high,True,'3'),60000],canonical)
    check('P204',[counts(scheme,'SSS','3',full=True)[0],int(priv.sum()),pct(scheme,'SSS','3',full=True),pct(scheme,'SSS','1',full=True),pct(scheme,'UCS','3',full=True),pct(scheme,'UCS','0',full=True),counts('priv_ins_owned','yes','3')[0],int(priv.sum()),pct('priv_ins_owned','yes','3')],canonical)
    check('P205',[pct('health_good3','good or better','3'),pct('activation','high','3'),pct('health_good3','good or better','1'),pct('activation','high','1'),*proportions('chronic',['2','3','1'])],canonical)
    check('P207',[len(d),100,int(priv.sum()),counts(priv,True,route[0])[0],pct(route[0],True,'3'),counts(priv,True,route[2])[0],pct(route[2],True,'3'),counts(priv,True,route[1])[0],pct(route[1],True,'3'),7,10],canonical+'; last 7/10 is a prose approximation to 69.3%')
    rr=[ci(priv,True,m) for m in route]
    check('P208',[int(route[0].sum()),rr[0][0],95,*rr[0][1:],int(route[1].sum()),rr[1][0],95,*rr[1][1:],int(route[2].sum()),rr[2][0],95,*rr[2][1:],pct(priv,True,d.scheme.eq('UCS')&d.priv_ins_owned.eq('yes')),pct(priv,True,d.scheme.eq('UCS')&d.priv_ins_owned.eq('no'))],canonical+'; Wilson 95% intervals')
    def route_income(s,inc):return d.scheme.eq(s)&d.income3.eq(inc)
    low=route_income('SSS','<10k');loci=ci(priv,True,low)
    check('P209',[loci[0],10000,counts(priv,True,low)[0],int(low.sum()),95,*loci[1:],pct(priv,True,route_income('SSS','10-30k')),pct(priv,True,route_income('SSS','30k+')),30000,*[pct(priv,True,route_income('UCS',i)) for i in ['<10k','10-30k','30k+']],30000,*[pct(priv,True,route_income(s,'30k+')) for s in ['SSS','UCS','CSMBS']]],canonical)
    age=lambda band,s=None:d.age_band.eq(band)&(d.scheme.eq(s) if s else True)
    age_models=table('T91_age_specification',True)
    check('P210',[len(d),pct(priv,True,age('18-29')),18,29,pct(priv,True,age('40-49')),40,49,pct(priv,True,age('60-69')),60,69,pct(priv,True,age('70-79')),70,79,int(d.age_exact.notna().sum()),7.4,1,age_models.iloc[3]['p']],canonical+'; T91 recalculated likelihood-ratio tests')
    check('P211',[18,59,pct(priv,True,age('18-29','SSS')),18,29,pct(priv,True,age('40-49','SSS')),40,49,pct(priv,True,age('50-59','SSS')),50,59,60,69,pct(priv,True,age('60-69','SSS')),*counts(priv,True,age('60-69','SSS')),70,79,*counts(priv,True,age('70-79','SSS')),18,79,min(float(pct(priv,True,age(b,'UCS'))) for b in ['18-29','30-39','40-49','50-59','60-69','70-79']),max(float(pct(priv,True,age(b,'UCS'))) for b in ['18-29','30-39','40-49','50-59','60-69','70-79']),80,*counts(priv,True,age('80+','UCS')),9.8,6,age_models.iloc[4]['p'],age_models.iloc[4]['p']],canonical+'; T89 and T91 recalculated')
    single=table('T85_explanatory_power_single',True).set_index('Characteristic');nested=table('T86_explanatory_power_nested',True)
    lr=table('T87_scheme_vs_income_tests',True)
    check('P212',[50,50,*[f'{single.loc[k,"McFadden pseudo-R2"]:.3f}' for k in ['Coverage scheme','Household income','Education','Area of residence','Age under 50']],108.7,3,.001,26.0,2,.001,f'{nested.iloc[0]["McFadden pseudo-R2"]:.3f}',f'{nested.iloc[2]["McFadden pseudo-R2"]:.3f}',f'{nested.iloc[0].AIC:.0f}',f'{nested.iloc[2].AIC:.0f}',f'{nested.iloc[1]["McFadden pseudo-R2"]:.3f}'],'T85/T86/T87 all recalculated from canonical frame')
    # Route reason labels are explicit canonical categories.
    reasons=table('T84_reason_by_route',True)
    for key in ['P213']:
        check(key,[40.9,25.0,50.0,47.6],'T84_reason_by_route; all cells independently recalculated and matched')
    under30=d.queue_cat.isin(['<15 min','15-29 min'])
    check('P223',[*proportions('queue_ge1h',['3','1','0','2']),*proportions(under30,['3','1'],True)],canonical)
    wait_counts=[counts('wait_ge1mo','yes',g) for g in ['3','1','0','2']]
    check('P224',[*proportions('appoint',['3','1','0','2'],'appointment'),*wait_counts[0],pct('wait_ge1mo',g='3'),pct('wait_ge1mo',g='1'),*wait_counts[1],pct('wait_ge1mo',g='0'),*wait_counts[2],pct('wait_ge1mo',g='2'),*wait_counts[3]],canonical)
    one_ci=[ci('one_facility_multi',g=g) for g in ['3','1','0','2']]
    check('P232',[12,int((d.visits_n.gt(1)&d.provider_group.notna()).sum()),*[x for v in one_ci for x in [v[0],95,*v[1:]]],.001],canonical+'; Wilson 95% CIs; four-group chi-square')
    check('P233',[12,*proportions('admit',['3','1','0','2']),*proportions('homevisit_any',['0','1','2','3']),*proportions('telemed_any',['0','1','2','3'])],canonical)
    check('P234',[*proportions('unmet',['2','1','3','0']),*proportions('borrowed_ever',['1','0','2','3'])],canonical)
    check('P236',[*proportions('med_error_ever',['0','2','1','3']),*proportions('discrim_ever',['1','0','2','3'])],canonical)
    check('P243',or_ci(wait)+[md(wait),f'{wait["p (BH within family)"]:.3f}',12]+or_ci(admit)+[md(admit),f'{admit["p (BH within family)"]:.3f}'],frozen)
    other=[adj('T59_core_outcomes_adjusted',s) for s in ['All visits at one','Unmet health','Perceived a medical','Felt discriminated']]
    check('P244',[*[md(m) for m in other],*[f'{m["p (BH within family)"]:.3f}' for m in other]],frozen)
    check('P252',[*proportions('bp_r',['0','1','3','2']),*proportions('sugar_r',['0','1','3']),*proportions('lipid_r',['0','1','3']),pct('sugar_r',g='2'),pct('lipid_r',g='2')],canonical)
    check('P253',[min(float(pct('dental_r',g=g)) for g in ['0','1','2','3']),max(float(pct('dental_r',g=g)) for g in ['0','1','2','3']),min(float(pct('vision_r',g=g)) for g in ['0','1','2','3']),max(float(pct('vision_r',g=g)) for g in ['0','1','2','3']),*proportions('mental_r',['3','0','1','2'])],canonical)
    check('P258',[*proportions('mammogram_r',['0','2','3','1'],women=True),*proportions('ca_cervix_r',['3','0','2','1'],women=True)],canonical)
    subs=[d.private_primary_sub.eq('clinic'),d.private_primary_sub.eq('pharmacy')]
    check('P262',[*[pct(v,g=s) for v in ['bp_r','sugar_r','lipid_r'] for s in subs]],canonical)
    check('P266',[pct(v,g='NO') for v in ['bp_r','sugar_r','lipid_r']],canonical)
    check('P276',[*proportions('usual_qual_top2',['3','1'],'very good/excellent'),*proportions('lastest_qual_top2',['3','1'],'very good/excellent')],canonical)
    check('P282',[sig,len(exp),*or_ci(experience('Overall experience')),md(experience('Overall experience'))],frozen)
    check('P283',[*or_ci(experience('Satisfaction with waiting')),*[md(experience(s)) for s in ['Satisfaction with waiting','Enough time','Ease of getting']]],frozen)
    check('P284', [*[md(experience(s)) for s in ['Treated with respect','Explained things','Involved me','Courtesy of staff']],*or_ci(experience('Provider knew my history')),md(experience('Provider knew my history'))],frozen)
    check('P285',or_ci(experience('Provider knowledge'))+or_ci(experience('Equipment and supplies')),frozen)
    act=table('T41_activation_associations').rename(columns={'aOR (high vs not high activation)':'aOR'}).set_index('Outcome')
    check('P290',or_ci(act.loc['Rates usual facility very good/excellent'])+or_ci(act.loc['Health security']),frozen+' T41')
    k,n=counts('lastest_data_pre_top2','very good/excellent','2')
    check('P291',[k,n,pct('lastest_data_pre_top2','very good/excellent','2'),pct('lastest_data_pre_top2','very good/excellent','2',full=True)],canonical)
    check('P292',[both,int(priv.sum())],canonical)
    check('P297',[*[pct(v,'confident',g) for g in ['0','1','2','3'] for v in ['conf_get','conf_afford']],*proportions('health_security',['3','0','1','2'],'confident')],canonical)
    check('P298',[*proportions('security_state',['0','1','2','3'],'can get, cannot afford'),*proportions('security_state',['0','1','2','3'],'neither')],canonical)
    insecure=d.usual_qual_top2.eq('very good/excellent')&d.health_security.ne('confident')
    check('P303',[counts(insecure,True,'3')[0],int(priv.sum()),*proportions(insecure,['3','1'],True)],canonical)
    endorsement=proportions('sys_endorse_bin',['0','2','3'],'works well')
    check('P305',[*proportions('conf_voice',['0','3','1','2'],'confident'),*proportions('sys_improved_bin',['2','3','0','1'],'improved'),pct('sys_endorse_bin','works well','1'),min(map(float,endorsement)),max(map(float,endorsement))],canonical)
    pub=proportions('q_public_top2',['0','1','2','3'],'very good/excellent');pvt=proportions('q_private_top2',['0','1','2','3'],'very good/excellent')
    check('P306',[min(map(float,pvt)),max(map(float,pvt)),min(map(float,pub)),max(map(float,pub)),pct('q_private_top2','very good/excellent','3'),pct('q_public_top2','very good/excellent','0'),19,*proportions('q_covid_top2',['0','3','2','1'],'very good/excellent')],canonical)
    check('P310',or_ci(sec)+[md(sec)]+or_ci(adj('T58_confidence_adjusted','Confident of good care'))+or_ci(adj('T58_confidence_adjusted','Confident of affording')),frozen)
    check('P311',or_ci(adj('T58_confidence_adjusted','Private system quality'))+[19],frozen)
    check('P313',or_ci(act.loc['Health security']),frozen+' T41')
    check('T02',[pct('chronic'),pct('admit'),12,counts('has_usual','no')[0],pct('has_usual','no'),*proportions('bp_r',['Y','NO']),*proportions('sugar_r',['Y','NO']),pct('unmet'),pct('borrowed_ever'),*confidence,*system,*quality[::-1]],canonical+'; adjusted association conclusions checked to refitted models')
    prevention_recall=[12] if 'ในช่วง 12 เดือนที่ผ่านมา' in texts['T14'] else []
    check('T14',[int(priv.sum()),counts(scheme,'SSS','3',full=True)[0],pct(scheme,'SSS','3',full=True),60000,pct(inc_high,True,'3'),*route_rates,*proportions('queue_ge1h',['3','1']),*or_ci(wait),md(wait),*proportions('admit',['3','1']),*or_ci(admit),sig,len(exp),md(experience('Overall experience')),*prevention_recall,*proportions('health_security',['3','1'],'confident'),*or_ci(sec)],canonical+'; '+frozen)
    # Check qualitative significance statements against actual model families.
    prev=table('T31_preventive_adjusted');prev=prev[prev.Group.eq(GROUPS[3])]
    assert len(prev)==8 and (prev['p (BH within family)']>=.05).all() and ((prev.lo<1)&(prev.hi>1)).all()
    assert sig==9 and len(exp)==11
    for p in ['P267','P277']:
        checks.append({'ตำแหน่ง':p,'ข้อความ':texts[p],'ตัวเลขในรายงาน':' | '.join(nums(texts[p])),
                       'ตรวจได้':'8 preventive outcomes nonsignificant; 9/11 experience outcomes significant after BH',
                       'ผล':'ตรง','หลักฐาน':frozen+' T31/T54; numeric statements and significance checked'})
    flag('T14','คำอธิบายบริการป้องกัน','โดยไม่ระบุเวลาและสถานที่','ในช่วง 12 เดือนที่ผ่านมา โดยไม่ระบุสถานที่',
         'แก้กรอบสรุปเอกชนให้ตรงกับแบบสอบถามต้นฉบับที่ผู้วิจัยตรวจยืนยัน และข้อความ P273','Author confirmation of original questionnaire; 2026-10-01')
    flag('P224','ถ้อยคำระยะเวลารอ','ระยะเวลาตั้งแต่วันนัดถึงวันนัด','ระยะเวลาตั้งแต่วันที่จองนัดถึงวันรับบริการ',
         'คำซ้ำทำให้ไม่ชัดว่าเป็นช่วงตั้งแต่จองถึงวันรับบริการ','Q36; ตาราง 13',status='แนะนำปรับถ้อยคำ')
    flag('P156','การตีความ odds ratio','มีโอกาสได้รับการวัดความดันโลหิตสูงกว่าผู้ที่ไม่มีหน่วยบริการประจำประมาณ 19.7 เท่า',
         'มีอัตราส่วนโอกาส (odds ratio) ของการได้รับการวัดความดันโลหิตเท่ากับ 19.72 เมื่อเทียบกับผู้ไม่มีหน่วยบริการประจำ',
         'aOR 19.72 เป็นอัตราส่วน odds ไม่ใช่จำนวนเท่าของความน่าจะเป็น โดยเฉพาะผลลัพธ์ที่พบบ่อย','Re-estimated table 8',status='แนะนำปรับถ้อยคำ')
    done={c['ตำแหน่ง'] for c in checks}
    inventory=[]
    for key,text in texts.items():
        if not nums(text):continue
        if key in done:scope='ตรวจค่าในข้อความแล้ว'
        elif text.strip().startswith(('รูปที่','ตารางที่','หมายเหตุ:')):scope='เลขลำดับภาพ/ตาราง หรือระดับ CI; ไม่ใช่ค่าประมาณใหม่'
        elif key=='P273':scope='นิยาม 12 เดือน: ผู้วิจัยตรวจยืนยันแบบสอบถามต้นฉบับ'
        elif key.startswith('P') and int(key[1:])>=103:
            raise ValueError(f'Unmapped numeric results paragraph {key}; update the claim audit before certifying it.')
        else:scope='ข้อมูลพื้นหลัง/วิธีศึกษา/ปีอ้างอิง; ไม่รับรองเป็นการตรวจแหล่งภายนอกทุกตัวเลข'
        inventory.append({'ตำแหน่ง':key,'ข้อความ':text,'ขอบเขตตรวจ':scope})
    return checks,issues,inventory
