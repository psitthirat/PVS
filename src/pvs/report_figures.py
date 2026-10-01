"""Recreate the author's three international figures, preserving original palettes.

All geometry is plotted from verified aggregate data. No raster image editing.
Download images have Thai axes/legends and the agreed credit, without captions.
"""
from __future__ import annotations
import hashlib, json, shutil, zipfile
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from .paths import ROOT
from .storytelling import CHARTS, DATA, CREDIT, add_credit
from .story_overview import international_values, artifact

REGIONS=[('แอฟริกา',['ETH','KEN','ZAF']),('ลาตินอเมริกา',['PER','COL','MEX','URY','ARG']),('เอเชีย',['LAO','IND','KOR']),('อเมริกาเหนือ\nและยุโรป',['GRC','ITA','GBR','USA'])]
PALETTES={
 'report-figure-04':['#e34948'],
 'report-figure-05':['#C99A2E','#4E8FCB','#5F9E5A','#8D7BB0','#6E85A6'],
 'report-figure-06':['#2E7D46','#8CC152','#2a78d6','#eb6834','#1baf7a','#eda100','#4a3aa7','#e34948'],
}
COUNTRY_LABELS={'ETH':'เอธิโอเปีย','KEN':'เคนยา','ZAF':'แอฟริกาใต้','PER':'เปรู','COL':'โคลอมเบีย','MEX':'เม็กซิโก','URY':'อุรุกวัย','ARG':'อาร์เจนตินา†','LAO':'ลาว','IND':'อินเดีย','KOR':'เกาหลีใต้','GRC':'กรีซ','ITA':'อิตาลี','GBR':'สหราชอาณาจักร','USA':'สหรัฐอเมริกา','TOTAL':'รวม','THA':'ไทย*'}


def save(fig, identifier):
    # The other report charts use 12-inch canvases. These 15/16-inch figures
    # need proportionately larger credit type to match them when placed at
    # the same width in Word or on the website.
    scale = fig.get_figwidth() / 12
    add_credit(fig, size_scale=scale)
    for ext in ['png','svg']:
        fig.savefig(CHARTS/f'{identifier}.{ext}',dpi=300,bbox_inches='tight',pad_inches=.15*scale,facecolor='white',
                    metadata={'Date':None} if ext=='svg' else None)
    # Change only the screen theme after the print assets have been saved.
    # Series fills, values, positions and report-ready light PNGs stay identical.
    _screen_dark(fig)
    fig.savefig(CHARTS/f'{identifier}-dark.svg',bbox_inches='tight',
                pad_inches=.15*scale,facecolor='#101116',metadata={'Date':None})
    plt.close(fig)


def _screen_dark(fig):
    """Apply the website's dark canvas without recolouring any data series."""
    from matplotlib.colors import to_rgb
    from matplotlib.text import Text

    background, foreground, muted = '#101116', '#e9edf4', '#a7b0c0'
    fig.set_facecolor(background)
    for text in fig.findobj(match=Text):
        text.set_color(muted if text.get_text() == CREDIT else foreground)
    for ax in fig.axes:
        ax.set_facecolor(background)
        ax.tick_params(axis='both',colors=muted)
        for spine in ax.spines.values():
            spine.set_edgecolor('#566070')
        for line in ax.lines:
            # The only free lines in these figures are region brackets.
            line.set_color('#7c8798')
        for line in ax.get_xgridlines()+ax.get_ygridlines():
            line.set_color('#303846')
        for patch in ax.patches:
            # Keep every original series fill. Pale outlines/hatching make
            # darker bars legible; brighter bars retain the dark outlines.
            rgb = to_rgb(patch.get_facecolor())
            linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            luminance = sum(v*w for v,w in zip(linear,[.2126,.7152,.0722]))
            patch.set_edgecolor('#aab3c4' if luminance < .15 else '#080a0e')


def build():
    frame=international_values(); values=frame.set_index(['metric_id','country_iso']).value_percent
    def value(metric,country): return float(values.loc[metric,country])
    def countries(metric):
        available=set(frame.loc[frame.metric_id.eq(metric),'country_iso'])
        return [c for _,countries in REGIONS for c in countries if c in available]+['TOTAL','THA']
    def export(identifier,metrics,title,caption,note):
        sub=frame[frame.metric_id.isin(metrics)].copy()
        sub=sub.rename(columns={'metric_id':'ตัวชี้วัด','country_th':'ประเทศ','country_iso':'รหัสพื้นที่','value_percent':'ร้อยละ','source_id':'แหล่งข้อมูล','unit_level':'ขอบเขตพื้นที่'})
        sub.to_csv(DATA/f'{identifier}.csv',index=False,encoding='utf-8-sig')
        labels = {'report-figure-04':'ความต้องการที่ไม่ได้รับบริการ',
                  'report-figure-05':'ความเชื่อมั่นต่อระบบ',
                  'report-figure-06':'คุณภาพระบบสุขภาพ'}
        item=artifact(identifier,title,caption,sources=['content/international/values.csv','content/national/national_summary.csv'],category='บริบทระหว่างประเทศ',note=note,short=labels[identifier])
        item.update(csv=f'assets/data/{identifier}.csv',section='international',
                    original_palette=PALETTES[identifier],report_figure=int(identifier[-2:]))
        return item
    notes='* ไทยเป็นกลุ่มตัวอย่าง 13 จังหวัด ไม่ถ่วงน้ำหนัก; † อาร์เจนตินาศึกษาเฉพาะจังหวัดเมนโดซา การศึกษาแต่ละพื้นที่ต่างกันด้านเวลาและวิธีสำรวจ ค่ารวมใช้ค่าที่ตีพิมพ์ ไม่ใช่ค่าเฉลี่ยที่คำนวณใหม่'
    order=countries('unmet_need');xx=np.arange(len(order),dtype=float);xx[-1]+=.9
    fig,ax=plt.subplots(figsize=(15,7.4));height=[value('unmet_need',c) for c in order]
    bars=ax.bar(xx,height,width=.61,color=PALETTES['report-figure-04'][0],edgecolor='black',linewidth=1.1,zorder=3)
    bars[-1].set_hatch('///')
    for x,y in zip(xx,height):ax.text(x,y+.6,f'{y:.1f}%',ha='center',va='bottom',fontsize=11)
    ax.set_ylim(0,32);ax.set_yticks(range(0,31,5));ax.set_ylabel('ร้อยละของผู้ตอบที่มีความจำเป็นด้านสุขภาพ\nแต่ไม่ได้รับบริการ (%)',fontsize=12)
    ax.set_xticks(xx,[COUNTRY_LABELS[c] for c in order],rotation=45,ha='right',fontsize=11)
    for c,t in zip(order,ax.get_xticklabels()):
        if c in ['TOTAL','THA']:t.set_fontweight('bold')
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',color='#e5e5e5',lw=.7);ax.set_axisbelow(True)
    for region,codes in REGIONS:
        positions=[xx[order.index(c)] for c in codes if c in order]
        a,b=min(positions)-.45,max(positions)+.45
        ax.plot([a,a,b,b],[-.36,-.30,-.30,-.36],transform=ax.get_xaxis_transform(),color='#777777',lw=1,clip_on=False)
        ax.text((a+b)/2,-.325,region,transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=11,fontweight='bold')
    fig.subplots_adjust(left=.08,right=.99,top=.97,bottom=.33);save(fig,'report-figure-04')
    charts=[export('report-figure-04',['unmet_need'],'ความจำเป็นด้านสุขภาพที่ไม่ได้รับบริการในไทยและต่างประเทศ','ไทย 17.6% เทียบกับค่ารวม 14 ประเทศ 14.2%; แท่งลายเฉียงคือกลุ่มตัวอย่างไทย',notes+' ทั้งไทยและต่างประเทศถามช่วง 12 เดือนที่ผ่านมา แต่แผนสุ่มตัวอย่าง การถ่วงน้ำหนัก และช่วงเก็บข้อมูลต่างกัน จึงไม่ใช้จัดอันดับประเทศ')]
    def multi(identifier,panels):
        order=countries(panels[0][0][0]);yy=-np.arange(len(order),dtype=float);yy[-1]-=.9
        fig,axes=plt.subplots(1,len(panels),figsize=(16,14.6),sharey=True)
        for ax,(metrics,colors,legend,title,xlabel) in zip(axes,panels):
            k=len(metrics);h=.7/k; offsets=(np.arange(k)[::-1]-(k-1)/2)*h
            for metric,color,label,offset in zip(metrics,colors,legend,offsets):
                for y,country in zip(yy,order):
                    v=value(metric,country)
                    ax.barh(y+offset,v,height=h,color=color,edgecolor='black',lw=1,hatch='///' if country=='THA' else None,zorder=3)
                    ax.text(v+1.6,y+offset,f'{v:.1f}%',va='center',fontsize=7.3 if k>1 else 8.2,color='#333333')
            ax.set_title(title,loc='left',fontsize=12,fontweight='bold',pad=11)
            if k>1:ax.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(colors,legend)],loc='upper left',bbox_to_anchor=(0,1),ncol=2 if k in [2,4] else 1,fontsize=10,frameon=False,handlelength=1.5,columnspacing=.8)
            ax.set_xlim(0,100);ax.set_ylim(yy[-1]-1,2.6);ax.set_xlabel(xlabel,fontsize=10,labelpad=8)
            ax.set_xticks(range(0,101,20));ax.tick_params(axis='y',length=0);ax.spines[['top','right']].set_visible(False)
            ax.grid(axis='x',color='#e5e5e5',lw=.6);ax.set_axisbelow(True)
        axes[0].set_yticks(yy,[COUNTRY_LABELS[c] for c in order],fontsize=10.5)
        for c,t in zip(order,axes[0].get_yticklabels()):
            if c in ['TOTAL','THA']:t.set_fontweight('bold')
        for region,codes in REGIONS:
            pos=[yy[order.index(c)] for c in codes];top,bottom=max(pos)+.48,min(pos)-.48
            ax=axes[0];x=-.42 if len(panels)==4 else -.34
            ax.plot([x-.06,x,x,x-.06],[top,top,bottom,bottom],transform=ax.get_yaxis_transform(),color='#777777',clip_on=False,lw=1)
            ax.text(x-.14,(top+bottom)/2,region,rotation=90,transform=ax.get_yaxis_transform(),ha='center',va='center',fontsize=10,fontweight='bold')
        # Leave a separate footer below the two-line Thai axis labels.
        fig.subplots_adjust(left=.155,right=.99,bottom=.095,top=.96,wspace=.16 if len(panels)==3 else .19)
        save(fig,identifier)
    pal=PALETTES['report-figure-05']
    panels=[
      (['quality_confidence','affordability_confidence','health_security'],pal[:3],['มั่นใจว่าจะได้รับบริการคุณภาพ','มั่นใจว่าจะจ่ายค่ารักษาไหว','มั่นใจทั้งคุณภาพและการจ่าย'],'ก  ความมั่นคงทางสุขภาพ','ร้อยละที่ค่อนข้างมั่นใจหรือมั่นใจมาก (%)'),
      (['system_improved'],pal[3:4],[''],'ข  ทิศทางของระบบสุขภาพ','ร้อยละที่เห็นว่าระบบสุขภาพ\nดีขึ้นในสองปีที่ผ่านมา (%)'),
      (['system_works'],pal[4:],[''],'ค  การยอมรับระบบปัจจุบัน','ร้อยละที่เห็นว่าระบบทำงานดีอยู่แล้ว\nหรือต้องปรับเพียงเล็กน้อย (%)')]
    multi('report-figure-05',panels)
    charts.append(export('report-figure-05',[m for p in panels for m in p[0]],'ความเชื่อมั่นในระบบสุขภาพในไทยและต่างประเทศ','ความมั่นใจทั้งคุณภาพและการจ่ายของไทย 64.4%; การเห็นว่าระบบดีขึ้น 30.1%; ระบบทำงานดีหรือปรับเล็กน้อย 43.8%',notes))
    pal=PALETTES['report-figure-06'];quality='ร้อยละที่ประเมินว่า\nดีมากหรือดีเยี่ยม (%)'
    panels=[
      (['public_quality','private_quality'],pal[:2],['ภาครัฐ','ภาคเอกชน'],'ก  คุณภาพระบบสุขภาพ\nภาครัฐและเอกชน',quality),
      (['maternal_quality','child_quality','chronic_quality','mental_quality'],pal[2:6],['มารดา','เด็ก','โรคเรื้อรัง','สุขภาพจิต'],'ข  คุณภาพบริการปฐมภูมิ\nเฉพาะด้านของรัฐ',quality),
      (['government_listens'],pal[6:7],[''],'ค  รัฐบาลรับฟัง\nความคิดเห็นประชาชน','ร้อยละที่ค่อนข้างมั่นใจ\nหรือมั่นใจมาก (%)'),
      (['covid_management'],pal[7:],[''],'ง  การจัดการโควิด-19\nของรัฐบาล',quality)]
    multi('report-figure-06',panels)
    charts.append(export('report-figure-06',[m for p in panels for m in p[0]],'การประเมินคุณภาพระบบสุขภาพในไทยและต่างประเทศ','การประเมินคุณภาพภาครัฐและเอกชน บริการเฉพาะด้าน การรับฟังประชาชน และการจัดการโควิด-19',notes+' Q40 ของไทยใช้ผู้ประเมินได้: มารดา 1,650; เด็ก 1,702; โรคเรื้อรัง 1,787; สุขภาพจิต 1,648 คน คะแนนสะท้อนการรับรู้ ไม่ใช่คุณภาพทางคลินิก'))
    dest=ROOT/'output/figures/final_20261001';dest.mkdir(parents=True,exist_ok=True)
    for chart in charts:
        for ext in ['png','svg']:shutil.copy2(ROOT/'site'/chart[ext],dest/f'{chart["id"]}.{ext}')
    (dest/'คำอธิบายภาพ.json').write_text(json.dumps(charts,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(dest/'รูปภาษาไทย_4-6.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in dest.iterdir():
            if p.suffix in ['.png','.svg','.json']:z.write(p,p.name)
    return charts


def private_routes():
    """Two denominators: composition of 127 users versus uptake within each route."""
    import pandas as pd
    from .storytelling import finish, clean
    frame=pd.read_csv(ROOT/'content/national/private_routes.csv')
    labels=['สิทธิประกันสังคม','สิทธิอื่น + ประกันเอกชน','สิทธิอื่น ไม่มีประกันเอกชน']
    fig,axes=plt.subplots(1,2,figsize=(13,5.1),gridspec_kw={'width_ratios':[1,1]})
    for ax,col,xmax in zip(axes,['Share of all users %','Rate % (within route)'],[100,30]):
        vals=frame[col].to_numpy();bars=ax.barh(range(3),vals,height=.53,color=['#bd3346','#dc9993','#73839c'])
        for i,(v,bar) in enumerate(zip(vals,bars)):
            ax.text(v+1,i,f'{v:.1f}%',va='center',fontsize=12,fontweight='bold')
        ax.set_yticks(range(3),labels if ax is axes[0] else [f'n={int(k)} / N={int(n):,}' for k,n in zip(frame['Private-hospital users (n)'],frame['People (N)'])],fontsize=11)
        ax.invert_yaxis();clean(ax,xmax)
    axes[0].set_xlabel('ร้อยละของผู้ใช้โรงพยาบาลเอกชนประจำ 127 คน')
    axes[1].set_xlabel('ร้อยละผู้ใช้โรงพยาบาลเอกชนประจำในแต่ละกลุ่มสิทธิ')
    fig.subplots_adjust(left=.2,right=.965,bottom=.19,top=.95,wspace=.5)
    finish(fig,'private-routes')
    item=artifact('private-routes','สองมุมมองของผู้ใช้โรงพยาบาลเอกชนประจำ','ซ้าย: ผู้ใช้ประจำ 127 คนมาจากกลุ่มใด; ขวา: ภายในแต่ละกลุ่มสิทธิ มีผู้ใช้ประจำเท่าไร',sources=['content/national/private_routes.csv'],category='ผู้ใช้บริการ',note='แบ่งกลุ่มไม่ซ้ำกัน: ประกันสังคมรวมทั้งผู้มีและไม่มีประกันเอกชน ส่วนกลุ่มสิทธิอื่นจึงค่อยแยกตามประกันเอกชน การมีสิทธิไม่ยืนยันช่องทางจ่ายเงินจริง',short='สิทธิและผู้ใช้บริการ')
    item['section']='subgroup'
    frame['Route']=labels
    frame.rename(columns={'Route':'กลุ่มสิทธิ','People (N)':'ผู้ตอบในกลุ่ม (N)','Private-hospital users (n)':'ผู้ใช้โรงพยาบาลเอกชนประจำ (n)','Share of all users %':'องค์ประกอบของผู้ใช้ 127 คน (%)','Rate % (within route)':'สัดส่วนการใช้ภายในกลุ่ม (%)'}).to_csv(DATA/'private-routes.csv',index=False,encoding='utf-8-sig')
    # Keep the exact aggregate source copy separate from the Thai preview.
    shutil.copy2(ROOT/'content/national/private_routes.csv',DATA/'private_routes.csv')
    item['csv']='assets/data/private-routes.csv'
    return item
