"""Shared national and international graphics from documented public aggregates."""
from __future__ import annotations

import hashlib
import json
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import ROOT
from .storytelling import ASSETS, CHARTS, DATA, INK, MUTED, GRID, COLORS, clean, finish

NATIONAL = ROOT / 'content/national/national_summary.csv'
INTERNATIONAL = ROOT / 'content/international/values.csv'
METRIC_JOIN = {
    'unmet_need': 'unmet', 'quality_confidence': 'good_care',
    'affordability_confidence': 'afford', 'health_security': 'security',
    'system_improved': 'improved', 'system_works': 'works_well',
    'public_quality': 'public_quality', 'private_quality': 'private_quality',
    'government_listens': 'listens', 'covid_management': 'covid',
    'maternal_quality': 'maternal', 'child_quality': 'child',
    'chronic_quality': 'chronic_care', 'mental_quality': 'mental_care',
}
INTERNATIONAL_NOTE = ('ค่าต่างประเทศคงตามตารางหรือรูปที่ตีพิมพ์ ส่วนตัวอย่างไทยไม่ถ่วงน้ำหนัก วิธีเลือกตัวอย่าง การถ่วงน้ำหนัก และช่วงเวลาเก็บข้อมูลต่างกัน '
                      'ตัวเลขใช้ประกอบบริบท โดยไม่ได้ทดสอบความแตกต่างระหว่างประเทศ อาร์เจนตินาเก็บเฉพาะจังหวัดเมนโดซา')


def national():
    return pd.read_csv(NATIONAL)


def international_values():
    frame = pd.read_csv(INTERNATIONAL)
    thai = national().query("group_id == 'all'").set_index('measure_id')
    for metric, measure in METRIC_JOIN.items():
        row = thai.loc[measure]
        frame.loc[len(frame)] = {
            'metric_id': metric, 'country_iso': 'THA', 'country_en': 'Thailand',
            'country_th': 'ไทย*', 'value_percent': round(float(row.pct), 1),
            'source_id': 'pvs_thailand', 'source_locator': measure,
            'unit_level': 'unweighted_13_province_sample',
            'verification': 'canonical_aggregate', 'origin_local': 'content/national/national_summary.csv',
        }
    return frame


def artifact(identifier, title, caption, *, sources, category, note='', short=None):
    paths = []
    for source in sources:
        source = ROOT / source
        target = DATA / ('international_values.csv' if source == INTERNATIONAL else source.name)
        shutil.copy2(source, target)
        paths.append({'path': str(source.relative_to(ROOT)), 'asset': str(target.relative_to(ROOT / 'site')),
                      'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    return {'id': identifier, 'label': short or title, 'title': title, 'caption': caption,
            'note': note, 'category': category, 'source': 'PVS Thailand' if len(sources) == 1 else 'PVS Thailand; Kruk et al. (2024) / Croke et al. (2024)',
            'png': f'assets/figures/{identifier}.png', 'svg': f'assets/figures/{identifier}.svg',
            'svg_dark': f'assets/figures/{identifier}-dark.svg', 'csv': paths[0]['asset'],
            'source_tables': [], 'source_files': paths,
            'alt': title + ' — ' + caption, 'sha256': hashlib.sha256((CHARTS / f'{identifier}.png').read_bytes()).hexdigest()}


def _national_plot(identifier, domain, *, groups=('all',), measure_ids=None, colors=None):
    data = national()
    data = data[data.domain.isin([domain] if isinstance(domain, str) else domain)]
    base = data[data.group_id == groups[0]].copy()
    if measure_ids:
        base = base.set_index('measure_id').loc[measure_ids].reset_index()
    labels = base.label.tolist()
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(12, max(4.7, len(labels)*.6+1.5)))
    palette = colors or [COLORS[-1], COLORS[1], '#a5aebe']
    for i, group in enumerate(groups):
        rows = data[data.group_id == group].set_index('measure_id').loc[base.measure_id]
        pos = y+(i-(len(groups)-1)/2)*.22
        vals, low, high = (rows[col].to_numpy() for col in ['pct', 'ci_low', 'ci_high'])
        if len(groups) == 1:
            ax.barh(pos, vals, height=.48, color=palette[0], alpha=.88)
        else:
            ax.scatter(vals, pos, s=45, color=palette[i], label=rows.group_label.iloc[0], zorder=4)
        ax.errorbar(vals, pos, xerr=[vals-low, high-vals], fmt='none', ecolor=palette[i], capsize=2, lw=1.3)
        if len(groups) == 1:
            for j, row in enumerate(rows.itertuples()):
                ax.text(min(float(row.ci_high)+1.5, 103), pos[j], f'{row.pct:.1f}%  ({row.n:,}/{row.N:,})', fontsize=10, va='center', color=INK)
    ax.set_yticks(y, labels); ax.invert_yaxis(); clean(ax)
    if len(groups) == 1: ax.set_xlim(0, 119)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel('ร้อยละของผู้ตอบที่เข้าเกณฑ์')
    if len(groups) > 1:
        ax.legend(loc='lower left', bbox_to_anchor=(0, 1.02), ncol=3, frameon=False, fontsize=10)
    fig.subplots_adjust(left=.35, right=.96, top=.88, bottom=.17)
    finish(fig, identifier)


def _profile():
    data = national().query("group_id == 'all'")
    domains = [('profile_age', 'อายุ'), ('profile_education', 'การศึกษา'),
               ('profile_income', 'รายได้ครัวเรือน'), ('profile_scheme', 'สิทธิสุขภาพหลัก')]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for ax, (domain, heading) in zip(axes.flat, domains):
        rows = data[(data.domain == domain) & (data.measure_id != 'private_insurance')]
        pos = np.arange(len(rows))
        ax.barh(pos, rows.pct, height=.57, color=COLORS[-1])
        for y, row in zip(pos, rows.itertuples()):
            ax.text(row.pct+1.3, y, f'{row.pct:.1f}', fontsize=10, va='center', color=INK)
        ax.set_yticks(pos, rows.label, fontsize=10); ax.invert_yaxis(); clean(ax, 82)
        ax.set_xticks([0,20,40,60,80]); ax.set_xlabel('ร้อยละ', fontsize=10)
        ax.text(0, 1.05, heading, transform=ax.transAxes, weight='bold', color=INK)
    fig.subplots_adjust(left=.2, right=.97, bottom=.12, top=.92, wspace=1.1, hspace=.5)
    finish(fig, 'national-profile')


def _usual_source():
    rows = national().query("domain == 'usual_source' and group_id == 'all'")
    fig, ax = plt.subplots(figsize=(12, 5.5))
    palette = COLORS + ['#a0a8b6', '#d1d6df']
    pos = np.arange(len(rows)); ax.barh(pos, rows.pct, color=palette, height=.6)
    for y, row in zip(pos, rows.itertuples()):
        ax.text(row.pct+1, y, f'{row.pct:.1f}%  ·  {row.n:,} คน', va='center', fontsize=12)
    ax.set_yticks(pos, rows.label); ax.invert_yaxis(); clean(ax, 43)
    ax.set_xlabel('ร้อยละของผู้ตอบทั้งหมด 2,017 คน')
    fig.subplots_adjust(left=.29, right=.96, top=.94, bottom=.19)
    finish(fig, 'usual-source')


def _international_panels(identifier, metric_ids, headings):
    frame = international_values()
    first = frame[frame.metric_id == metric_ids[0]]
    order = first.country_iso.tolist()
    names = first.country_th.tolist()
    countries = len(order)
    if len(metric_ids) == 4:
        matrix = frame.pivot(index='country_iso', columns='metric_id', values='value_percent').reindex(order)[metric_ids]
        from matplotlib.colors import LinearSegmentedColormap
        palette = LinearSegmentedColormap.from_list('primary_quality', ['#fff1ec','#efa6a0','#b52e46','#641d36'])
        fig, ax = plt.subplots(figsize=(11, 9))
        ax.imshow(matrix, cmap=palette, vmin=0, vmax=100, aspect='auto')
        for y in range(len(matrix)):
            for x in range(len(metric_ids)):
                value = matrix.iloc[y,x]
                ax.text(x,y,f'{value:.1f}',ha='center',va='center',fontsize=12,
                        color='white' if value >= 55 else '#252832',weight='bold' if order[y]=='THA' else 'normal')
        ax.set_yticks(range(countries), names, fontsize=12)
        ax.set_xticks(range(4), headings, fontsize=12); ax.xaxis.tick_top()
        ax.tick_params(length=0,pad=10)
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.axhline(countries-1.5,color=INK,lw=1.3)
        ax.axhline(countries-2.5,color=GRID,lw=1)
        ax.set_xlabel('ร้อยละที่ประเมินว่าดีมากหรือดีเยี่ยม · สีเข้มหมายถึงร้อยละสูง',labelpad=13)
        fig.subplots_adjust(left=.29,right=.98,top=.91,bottom=.12)
        finish(fig,identifier)
        return
    fig, axes = plt.subplots(1, len(metric_ids), figsize=(12, 10), sharey=True, squeeze=False)
    for ax, metric, heading in zip(axes.flat, metric_ids, headings):
        rows = frame[frame.metric_id == metric].set_index('country_iso').reindex(order)
        colors = [COLORS[-1] if iso == 'THA' else '#8792a6' if iso == 'TOTAL' else '#d77577' for iso in order]
        bars = ax.barh(np.arange(countries), rows.value_percent, height=.63, color=colors)
        bars[-1].set_hatch('///'); bars[-1].set_edgecolor('#612235')
        for i, row in enumerate(rows.itertuples()):
            if np.isfinite(row.value_percent):
                ax.text(row.value_percent+1.1, i, f'{row.value_percent:.1f}', va='center', fontsize=10,
                        weight='bold' if row.Index == 'THA' else 'normal', color=INK)
        ax.axhline(countries-1.5, color=GRID, lw=1)
        ax.axhline(countries-2.5, color=GRID, lw=1)
        ax.set_yticks(range(countries), names, fontsize=11)
        clean(ax, 109 if metric != 'unmet_need' else 31)
        ax.set_xticks([0,25,50,75,100] if metric != 'unmet_need' else [0,5,10,15,20,25,30])
        ax.set_xlabel('ร้อยละ', fontsize=10)
        ax.text(.5, 1.025, heading, transform=ax.transAxes, ha='center', fontsize=12, weight='bold', color=INK)
    axes.flat[0].invert_yaxis()
    fig.subplots_adjust(left=.22 if len(metric_ids)<3 else .2, right=.98, bottom=.1, top=.91, wspace=.17)
    finish(fig, identifier)


def build_overview():
    charts=[]
    definitions = [
      ('national-health', 'health', 'สุขภาพและความพร้อมดูแลตนเองของผู้ตอบ', 'สุขภาพ',
       'ผู้ตอบส่วนใหญ่ประเมินสุขภาพว่าดีขึ้นไป ขณะเดียวกันประมาณหนึ่งในสามมีภาวะเจ็บป่วยเรื้อรัง',
       'ใช้ผู้ตอบทั้งหมด 2,017 คน ความมั่นใจดูแลสุขภาพเชิงรุกสองข้อและเกณฑ์มั่นใจมากทั้งสองข้อเป็นคนละนิยาม'),
      ('national-use', 'use', 'การใช้บริการและความจำเป็นที่ยังไม่ได้รับบริการ', 'การใช้บริการ',
       'ผู้ตอบ 354 คนรายงานว่ามีความจำเป็นด้านสุขภาพแต่ไม่ได้รับบริการ และ 341 คนเคยนอนโรงพยาบาลในรอบปี',
       'นอนโรงพยาบาล เยี่ยมบ้าน และบริการทางไกลอ้างอิง 12 เดือน; ความจำเป็นที่ไม่ได้รับบริการ Q29 อ้างอิง 12 เดือนเช่นกัน; การกู้ยืมหรือขายทรัพย์สิน Q31 อ้างอิง 12 เดือนเช่นกัน'),
      ('national-confidence', 'confidence', 'ความมั่นใจว่าจะรักษาได้และจ่ายไหว', 'ความมั่นใจ',
       'มั่นใจคุณภาพ 78.9% มั่นใจว่าสามารถจ่ายได้ 66.5% และมั่นใจทั้งสองด้าน 64.4%',
       'เป็นการรับรู้เมื่อสมมติว่าเจ็บป่วยรุนแรง ไม่ใช่การวัดคุณภาพทางคลินิกหรือรายจ่ายที่เกิดขึ้นจริง'),
      ('national-system-ratings', 'system_ratings', 'เสียงสะท้อนต่อคุณภาพและการทำงานของระบบสุขภาพ', 'คุณภาพระบบ',
       'คะแนนคุณภาพที่ประชาชนรับรู้แตกต่างกันระหว่างภาครัฐ เอกชน และบริการเฉพาะด้าน',
       'คุณภาพบริการมารดา เด็ก โรคเรื้อรัง และสุขภาพจิต ใช้เฉพาะผู้ประเมินได้ ตัวหารตามลำดับ 1,650; 1,702; 1,787; 1,648 คน รายการอื่นใช้ 2,017 คน'),
    ]
    for identifier, domain, title, short, caption, note in definitions:
        _national_plot(identifier, domain)
        charts.append(artifact(identifier,title,caption,sources=[NATIONAL.relative_to(ROOT)],category='ภาพรวมประเทศไทย',note=note,short=short))
    _profile(); _usual_source()
    charts.insert(0,artifact('national-profile','ลักษณะผู้ตอบแบบสำรวจ 2,017 คน','การกระจายอายุ การศึกษา รายได้ครัวเรือน และสิทธิสุขภาพหลัก',sources=[NATIONAL.relative_to(ROOT)],category='ภาพรวมประเทศไทย',note='ลักษณะของกลุ่มตัวอย่างที่เก็บได้ ไม่ใช่การกระจายประชากรไทยที่ผ่านการถ่วงน้ำหนัก',short='ผู้ตอบแบบสำรวจ'))
    charts.append(artifact('usual-source','ใครมีหน่วยบริการประจำ และเลือกใช้ที่ใด','ผู้ตอบ 1,529 คนมีหน่วยบริการประจำ ขณะที่ 488 คนไม่มีหน่วยบริการประจำ',sources=[NATIONAL.relative_to(ROOT)],category='ภาพรวมประเทศไทย',note='หกกลุ่มไม่ซ้ำกันและรวมครบ 2,017 คน การมีหน่วยบริการประจำไม่เท่ากับการขึ้นทะเบียนตามสิทธิสุขภาพ',short='หน่วยบริการประจำ'))
    _national_plot('national-prevention','prevention',groups=('all','municipal','non_municipal'))
    charts.append(artifact('national-prevention','บริการป้องกันและคัดกรองในผู้ตอบทั้งหมด','แสดงภาพรวมและความแตกต่างระหว่างผู้ตอบในเขตเทศบาลกับนอกเขตเทศบาล',sources=[NATIONAL.relative_to(ROOT)],category='ภาพรวมประเทศไทย',note='Q27 ถามการได้รับบริการในช่วง 12 เดือนที่ผ่านมา การตรวจเต้านมและปากมดลูกใช้ผู้ตอบหญิงเท่านั้น ข้อมูลไม่ระบุอายุเข้าเกณฑ์ ระยะห่างการตรวจ หรือสถานพยาบาลที่ให้บริการ',short='บริการป้องกัน'))
    for identifier,domain,title,short in [('usual-prevention','prevention','ผู้มีหน่วยบริการประจำได้รับบริการป้องกันต่างจากผู้ไม่มีอย่างไร','บริการป้องกัน'),('usual-confidence','confidence','ความมั่นใจของผู้มีและไม่มีหน่วยบริการประจำ','ความมั่นใจ')]:
        _national_plot(identifier,domain,groups=('has_usual','no_usual'))
        charts.append(artifact(identifier,title,'เปรียบเทียบผู้มีหน่วยบริการประจำ 1,529 คนกับผู้ไม่มี 488 คน ด้วยร้อยละและช่วงความเชื่อมั่น 95%',sources=[NATIONAL.relative_to(ROOT)],category='ความต่อเนื่องของบริการ',note='เป็นความสัมพันธ์พรรณนาที่ยังไม่ปรับปัจจัยร่วม ไม่ใช่ผลเชิงสาเหตุของการมีหน่วยบริการประจำ ฐานผู้ตอบของการคัดกรองเฉพาะหญิงต่างจากรายการทั่วไป',short=short))
    comparative = [
        ('international-unmet',['unmet_need'],['ความจำเป็นด้านสุขภาพที่ไม่ได้รับบริการ'], 'ความจำเป็นที่ไม่ได้รับบริการใน 14 ประเทศและกลุ่มตัวอย่างไทย','ความต้องการบริการ', 'ค่าไทย 17.6% แสดงร่วมกับผล PVS ต่างประเทศ 14 ประเทศ ซึ่งรายงานค่ารวม 14.2%', 'ทั้งไทยและต่างประเทศอ้างอิง 12 เดือนที่ผ่านมา แต่ต่างกันด้านแผนสุ่มตัวอย่าง การถ่วงน้ำหนัก และช่วงเก็บข้อมูล จึงใช้เปรียบเทียบเชิงพรรณนา'),
        ('international-confidence',['quality_confidence','affordability_confidence','health_security'],['มั่นใจคุณภาพ','มั่นใจว่าจ่ายไหว','มั่นใจทั้งสองด้าน'], 'ความเชื่อมั่นต่อระบบสุขภาพใน 15 ประเทศและกลุ่มตัวอย่างไทย','ความเชื่อมั่น', 'ความมั่นใจด้านคุณภาพและความสามารถจ่ายเป็นคนละมิติในทุกบริบท', ''),
        ('international-system',['system_improved','system_works'],['ระบบดีขึ้นในสองปี','ระบบทำงานดี / ปรับเล็กน้อย'], 'ทิศทางและการยอมรับระบบสุขภาพในหลายประเทศ','ทิศทางของระบบ','ผู้ตอบไทย 30.1% เห็นว่าระบบดีขึ้นในสองปี และ 43.8% เห็นว่าระบบทำงานดีหรือต้องปรับเพียงเล็กน้อย',''),
        ('international-quality',['public_quality','private_quality'],['คุณภาพระบบภาครัฐ','คุณภาพระบบเอกชน'],'คุณภาพภาครัฐและเอกชนในมุมมองประชาชน','คุณภาพรัฐ–เอกชน','ร้อยละที่ประเมินว่าดีมากหรือดีเยี่ยม; ไทย 18.0% สำหรับภาครัฐ และ 45.4% สำหรับเอกชน','เป็นการประเมินระบบโดยรวม ไม่ใช่คะแนนคุณภาพทางคลินิกหรือคะแนนของสถานพยาบาลครั้งล่าสุด'),
        ('international-primary',['maternal_quality','child_quality','chronic_quality','mental_quality'],['บริการมารดา','บริการเด็ก','บริการโรคเรื้อรัง','บริการสุขภาพจิต'],'การรับรู้คุณภาพบริการปฐมภูมิเฉพาะด้านในหลายประเทศ','บริการเฉพาะด้าน','ร้อยละที่ประเมินว่าดีมากหรือดีเยี่ยม แยกบริการสี่ด้าน','ค่าของไทยตัดผู้ที่ประเมินไม่ได้ออกจากตัวหารรายข้อ; ต้องพิจารณานิยามบริการและวิธีจัดการคำตอบไม่ทราบของแต่ละการสำรวจ'),
        ('international-governance',['government_listens','covid_management'],['รัฐบาลรับฟังประชาชน','จัดการโควิดดีมาก / ดีเยี่ยม'],'เสียงประชาชนต่อการตอบสนองของรัฐบาล','การตอบสนองของรัฐ','ไทย 54.2% มั่นใจว่ารัฐรับฟังประชาชน และ 15.3% ประเมินการจัดการโควิดว่าดีมากหรือดีเยี่ยม','การประเมินโควิดเกิดในบริบทการระบาดและช่วงเวลาเก็บข้อมูลต่างกัน'),
    ]
    for identifier,metrics,headings,title,short,caption,note in comparative:
        _international_panels(identifier,metrics,headings)
        record=artifact(identifier,title,caption,sources=[INTERNATIONAL.relative_to(ROOT),NATIONAL.relative_to(ROOT)],category='เปรียบเทียบระหว่างประเทศ',note=' '.join([note,INTERNATIONAL_NOTE]).strip(),short=short)
        record['metric_ids']=metrics
        charts.append(record)
    frame=international_values()
    frame.to_csv(DATA/'international_comparison.csv',index=False)
    from .story_maps import draw_world
    scopes_path=ROOT/'content/international/spatial-scope.json'
    scopes=json.loads(scopes_path.read_text()) if scopes_path.exists() else {}
    point=scopes.get('ARG',{}).get('point',{}).get('coordinates')
    if not point:
        raise ValueError('Verified Mendoza locator is required for international maps')
    for identifier,metric,title,short,vmax in [
        ('map-unmet','unmet_need','ความจำเป็นที่ไม่ได้รับบริการในแต่ละพื้นที่ศึกษา','แผนที่ความต้องการบริการ',30),
        ('map-confidence','health_security','ความมั่นใจทั้งคุณภาพและความสามารถจ่ายในแต่ละพื้นที่ศึกษา','แผนที่ความเชื่อมั่น',100),
        ('map-system-quality','public_quality','การรับรู้คุณภาพระบบภาครัฐในแต่ละพื้นที่ศึกษา','แผนที่คุณภาพภาครัฐ',100),
    ]:
        rows=frame[(frame.metric_id==metric)&(frame.country_iso!='TOTAL')]
        values=dict(zip(rows.country_iso,rows.value_percent))
        fig,ax=plt.subplots(figsize=(12,6.4))
        draw_world(ax,values,vmax=vmax,mendoza=point)
        fig.subplots_adjust(left=.02,right=.99,top=.97,bottom=.17)
        finish(fig,identifier)
        note=INTERNATIONAL_NOTE+' สีเทาหมายถึงไม่มีค่าประมาณในชุดเปรียบเทียบ ไม่ใช่ร้อยละศูนย์'
        if metric=='unmet_need': note+=' ทั้งไทยและต่างประเทศอ้างอิง 12 เดือนที่ผ่านมา'
        record=artifact(identifier,title,'สีแสดงร้อยละตามคำตอบของผู้เข้าร่วมการสำรวจในพื้นที่นั้น',sources=[INTERNATIONAL.relative_to(ROOT),NATIONAL.relative_to(ROOT)],category='เปรียบเทียบระหว่างประเทศ',note=note,short=short)
        record['metric_ids']=[metric]
        charts.append(record)
    for record in charts:
        if record.get('metric_ids'):
            preview=frame[frame.metric_id.isin(record['metric_ids'])].copy()
            if record['id'].startswith('map-'):
                preview=preview[preview.country_iso!='TOTAL']
            names={m['id']:m['title_th'] for m in json.loads((ROOT/'content/international/metrics.json').read_text())}
            preview['metric_id']=preview.metric_id.map(names)
            preview['country_th']=preview.country_th.replace({'ไทย*':'ไทย (กลุ่มตัวอย่าง 13 จังหวัด)'})
            preview=preview[['metric_id','country_th','value_percent','source_id']].rename(columns={
                'metric_id':'ตัวชี้วัด','country_th':'ประเทศหรือพื้นที่','value_percent':'ร้อยละ','source_id':'แหล่งข้อมูล'})
        else:
            filters={
                'national-profile': (['profile_age','profile_education','profile_income','profile_scheme'],['all']),
                'national-health': (['health'],['all']), 'national-use': (['use'],['all']),
                'national-confidence': (['confidence'],['all']),
                'national-system-ratings': (['system_ratings'],['all']),
                'usual-source': (['usual_source'],['all']),
                'national-prevention': (['prevention'],['all','municipal','non_municipal']),
                'usual-prevention': (['prevention'],['has_usual','no_usual']),
                'usual-confidence': (['confidence'],['has_usual','no_usual']),
            }
            domains,groups=filters[record['id']]
            preview=national()
            preview=preview[preview.domain.isin(domains)&preview.group_id.isin(groups)]
            if record['id']=='national-profile': preview=preview[preview.measure_id!='private_insurance']
            preview=preview[['label','group_label','n','N','pct','ci_low','ci_high']].rename(columns={
                'label':'รายการ','group_label':'กลุ่ม','n':'จำนวน','N':'ตัวหาร','pct':'ร้อยละ',
                'ci_low':'95% CI ล่าง','ci_high':'95% CI บน'})
            preview=preview.round(2)
        target=DATA/f"{record['id']}.csv"
        preview.to_csv(target,index=False)
        record['csv']=str(target.relative_to(ROOT/'site'))
    for folder in ['national','international']:
        shutil.copytree(ROOT/'content'/folder,ASSETS/'sources'/folder,dirs_exist_ok=True)
    return charts
