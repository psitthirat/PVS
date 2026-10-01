"""Build shared Thai chart assets and public storytelling data from approved tables.

No respondent-level data are read. Report and website consume the same exported
PNGs; SVG downloads contain outlined text for portability into presentation tools.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import NullLocator
import numpy as np
import pandas as pd

from .paths import ROOT
from .figures import _parse

TABLES = ROOT / "results/2026-09/tables"
SITE = ROOT / "site"
ASSETS = SITE / "assets"
CHARTS = ASSETS / "figures"
DATA = ASSETS / "data"
CREDIT = "© 2569 บริษัท วันโอวัน พับลิโก้ จำกัด และคณะแพทยศาสตร์โรงพยาบาลรามาธิบดี มหาวิทยาลัยมหิดล"
GROUPS = ["public primary care", "public hospital OPD/ER", "private clinic/pharmacy", "private hospital OPD/ER"]
LABELS = ["ปฐมภูมิภาครัฐ", "โรงพยาบาลรัฐ", "คลินิก/ร้านยาเอกชน", "โรงพยาบาลเอกชน"]
COLORS = ["#73839c", "#34435b", "#dc9993", "#bd3346"]
INK, MUTED, GRID = "#252b38", "#68717f", "#e2e4e9"
TRANSLATIONS = {
    "Aged under 50": "อายุต่ำกว่า 50 ปี",
    "Lives in a municipality": "อาศัยในเขตเทศบาล",
    "Upper-secondary education or above": "การศึกษามัธยมปลายขึ้นไป",
    "Household income ฿30,000+ / month": "รายได้ครัวเรือน ≥30,000 บาท/เดือน",
    "Social Security (SSS)": "สิทธิประกันสังคม",
    "Universal Coverage (UCS)": "สิทธิหลักประกันสุขภาพแห่งชาติ",
    "Owns private health insurance": "มีประกันสุขภาพเอกชน",
    "Self-rated health good or better": "ประเมินสุขภาพว่าดีขึ้นไป",
    "Chronic condition ≥ 6 months": "มีโรค/ภาวะเรื้อรัง ≥6 เดือน",
    "High patient activation": "ความพร้อมจัดการสุขภาพระดับสูง",
    "Covered by my insurance scheme": "ใช้สิทธิประกันสุขภาพได้",
    "Short waiting time": "รอรับบริการไม่นาน",
    "Close to home": "ใกล้บ้าน",
    "Has medicines and equipment": "มียาและอุปกรณ์พร้อม",
    "Low cost": "ค่าใช้จ่ายต่ำ",
    "Provider skill": "ทักษะของผู้ให้บริการ",
    "Blood pressure measured (Q27A)": "ตรวจวัดความดันโลหิต",
    "Blood sugar tested (Q27F)": "ตรวจน้ำตาลในเลือด",
    "Blood lipids tested (Q27G)": "ตรวจไขมันในเลือด",
    "Dental examination (Q27E)": "ตรวจสุขภาพช่องปาก",
    "Vision check (Q27D)": "ตรวจสายตา",
    "Mental-health service received (Q27H)": "รับบริการสุขภาพจิต",
    "Breast examination/mammogram (Q27B) — women only": "ตรวจเต้านม/แมมโมแกรม (เฉพาะหญิง)",
    "Cervical screening (Q27C) — women only": "ตรวจคัดกรองมะเร็งปากมดลูก (เฉพาะหญิง)",
    "Walked in without an appointment": "มารับบริการโดยไม่ได้นัดหมาย",
    "Waited 1 hour or more at the facility": "รอรับบริการอย่างน้อย 1 ชั่วโมง",
    # The frozen release still carries the first label; new runs use the second.
    "Used only one facility in 12 months": "ใช้สถานพยาบาลแห่งเดียวใน 12 เดือน",
    "Used only one facility (of those with >1 visit)":
        "ใช้สถานพยาบาลแห่งเดียว (เฉพาะผู้ใช้บริการ >1 ครั้ง)",
    "Admitted overnight in 12 months": "นอนโรงพยาบาลใน 12 เดือน",
    "Received a home visit": "เคยได้รับการเยี่ยมบ้าน",
    "Reported an unmet health-care need": "มีความต้องการบริการที่ไม่ได้รับการตอบสนอง",
    "Overall experience": "ประสบการณ์โดยรวม",
    "Provider knowledge and skill": "ความรู้และทักษะของผู้ให้บริการ",
    "Equipment and supplies ready": "ความพร้อมของอุปกรณ์และเวชภัณฑ์",
    "Treated with respect": "ได้รับการปฏิบัติด้วยความเคารพ",
    "Provider knew my history": "ผู้ให้บริการทราบประวัติการรักษา",
    "Explained things clearly": "อธิบายข้อมูลอย่างเข้าใจง่าย",
    "Involved me in decisions": "มีส่วนร่วมในการตัดสินใจ",
    "Enough time in the consultation": "มีเวลาปรึกษาเพียงพอ",
    "Satisfaction with waiting time": "ความพึงพอใจต่อเวลารอ",
    "Courtesy of staff": "ความสุภาพของเจ้าหน้าที่",
    "Ease of getting an appointment": "ความสะดวกในการนัดหมาย",
    "Rates usual facility very good/excellent": "ประเมินหน่วยบริการประจำว่าดีมาก/ดีเยี่ยม",
    "Would recommend provider (0-10 score 9-10)": "แนะนำหน่วยบริการ (คะแนน 9–10)",
    "Admitted overnight, past 12 months": "นอนโรงพยาบาลใน 12 เดือน",
    "Unmet health-care need": "มีความต้องการบริการที่ไม่ได้รับการตอบสนอง",
    "Perceived a medical error (ever)": "เคยรับรู้ความผิดพลาดทางการแพทย์",
    "Felt discriminated against (ever)": "เคยรู้สึกถูกเลือกปฏิบัติ",
    "All visits at one facility": "ใช้บริการที่สถานพยาบาลแห่งเดียว",
    "Health security": "มั่นใจทั้งคุณภาพและความสามารถจ่าย",
    "Confident of good care if seriously ill": "มั่นใจว่าจะได้รับบริการคุณภาพเมื่อป่วยหนัก",
    "Confident of affording care": "มั่นใจว่าสามารถจ่ายค่ารักษาได้",
    "System improved over 2 years": "เห็นว่าระบบดีขึ้นในสองปี",
    "System works well / minor change": "เห็นว่าระบบดี/ต้องปรับเล็กน้อย",
    "Public system quality high": "ประเมินระบบภาครัฐว่าคุณภาพสูง",
    "Private system quality high": "ประเมินระบบเอกชนว่าคุณภาพสูง",
    "Government listens to the public": "มั่นใจว่ารัฐรับฟังประชาชน",
}


def read(name):
    return pd.read_csv(TABLES / f"{name}.csv")


def label(text):
    return TRANSLATIONS.get(text, TRANSLATIONS.get(text.split(" — ")[-1], text))


def setup():
    for directory in [CHARTS, DATA, ASSETS / "fonts"]:
        directory.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / "content/fonts").iterdir():
        if source.suffix == ".ttf":
            font_manager.fontManager.addfont(str(source))
        shutil.copy2(source, ASSETS / "fonts" / source.name)
    shutil.copytree(ROOT / "content/geography", ASSETS / "geography", dirs_exist_ok=True)
    shutil.copytree(ROOT / "content/questionnaire", ASSETS / "sources/questionnaire", dirs_exist_ok=True)
    plt.rcParams.update({
        "font.family": "Sarabun", "font.size": 12, "text.color": INK,
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK,
        "axes.edgecolor": GRID, "axes.unicode_minus": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "svg.fonttype": "path", "savefig.facecolor": "white",
        # Stable SVG ids, so an unchanged chart rebuilds to identical bytes.
        "svg.hashsalt": "pvs",
    })


def clean(ax, xmax=100):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    if xmax:
        ax.set_xlim(0, xmax)


def add_credit(fig, *, size_scale=1.0):
    """Shared lower-left credit; scale type for figures displayed at equal width."""
    return fig.text(0.012, 0.013, CREDIT, fontsize=7.6 * size_scale,
                    color=MUTED, ha="left", va="bottom")


def finish(fig, identifier):
    # Titles, narrative captions, and interpretation remain outside the artifact.
    add_credit(fig)
    for suffix in ["png", "svg"]:
        fig.savefig(CHARTS / f"{identifier}.{suffix}", dpi=300,
                    bbox_inches="tight", pad_inches=0.15,
                    metadata={"Date": None} if suffix == "svg" else None)
    # The screen version retains the same data and geometry. Print downloads
    # and DOCX always use the white-background exports above.
    from matplotlib.text import Text
    from matplotlib.colors import to_hex, to_rgba
    from matplotlib.patches import Patch
    from matplotlib.collections import Collection
    from matplotlib.lines import Line2D
    background, foreground = "#101116", "#e9edf4"
    dark_inks = {INK, "#203b46", "#183b56", "#183d45", "#000000", "#60747c", MUTED}
    pale = {"#ffffff", "#f5f7f6", "#f7f8fa", "#faf7f7"}
    dark_palette = {"#34435b": "#8ba7ce", "#73839c": "#a9b5cb",
                    "#e3e8e8": "#273443", "#e1e8e9": "#273443",
                    "#cdd9da": "#48576c", GRID: "#303846"}
    fig.set_facecolor(background)
    for ax in fig.axes:
        ax.set_facecolor(background)
        for spine in ax.spines.values(): spine.set_edgecolor("#384050")
        for line in ax.get_xgridlines() + ax.get_ygridlines(): line.set_color("#303846")
    for item in fig.findobj(match=Text):
        box = item.get_bbox_patch()
        if box is not None:
            try:
                if to_hex(box.get_facecolor()).lower() in pale:
                    box.set_facecolor(background)
            except (TypeError, ValueError):
                pass
        try:
            if to_hex(item.get_color()).lower() in dark_inks:
                item.set_color(foreground)
        except (TypeError, ValueError):
            pass
    for item in fig.findobj(match=Patch):
        try:
            color = to_hex(item.get_facecolor()).lower()
            if color in pale and item.get_facecolor()[-1] > 0:
                item.set_facecolor(background if color == "#ffffff" else "#141b26")
            elif color in dark_palette:
                item.set_facecolor(dark_palette[color])
            if to_hex(item.get_edgecolor()).lower() == "#ffffff":
                item.set_edgecolor("#1d2633")
        except (TypeError, ValueError):
            pass
    for item in fig.findobj(match=Collection):
        for get, set_ in [(item.get_facecolors, item.set_facecolors), (item.get_edgecolors, item.set_edgecolors)]:
            colors = get().copy()
            for i, value in enumerate(colors):
                key = to_hex(value).lower()
                if key in dark_palette:
                    colors[i] = to_rgba(dark_palette[key], value[-1])
                elif key == "#ffffff":
                    colors[i] = to_rgba("#1d2633", value[-1])
            set_(colors)
    for item in fig.findobj(match=Line2D):
        try:
            color = to_hex(item.get_color()).lower()
            if color in dark_palette: item.set_color(dark_palette[color])
            elif color == INK: item.set_color(foreground)
        except (TypeError, ValueError):
            pass
    fig.savefig(CHARTS / f"{identifier}-dark.svg", bbox_inches="tight",
                pad_inches=0.15, facecolor=background, metadata={"Date": None})
    plt.close(fig)


def grouped(identifier, table, measures=None, experience=False):
    frame = read(table)
    if measures is not None:
        frame = frame.set_index("Measure").loc[measures].reset_index()
    fig, ax = plt.subplots(figsize=(12, max(5.0, len(frame) * 0.59 + 1.7)))
    ys = np.arange(len(frame))
    for i, group in enumerate(GROUPS):
        parsed = [_parse(x) for x in frame[group]]
        values = np.array([x[2] for x in parsed])
        low, high = np.array([x[3] for x in parsed]), np.array([x[4] for x in parsed])
        offset = (i - 1.5) * 0.16
        valid_ci = np.isfinite(low) & np.isfinite(high)
        ax.hlines(ys[valid_ci] + offset, low[valid_ci], high[valid_ci], color=COLORS[i], lw=1.6, alpha=0.65)
        ax.scatter(values, ys + offset, color=COLORS[i], s=43, label=LABELS[i], zorder=3,
                   edgecolors="white", linewidths=0.6)
    for y in ys[::2]:
        ax.axhspan(y - 0.47, y + 0.47, color="#f5f7f6", zorder=0)
    ax.set_yticks(ys, [label(x) for x in frame["Measure"]])
    ax.invert_yaxis()
    clean(ax)
    ax.set_xlabel("ร้อยละที่ประเมินว่าดีมากหรือดีเยี่ยม" if experience else "ร้อยละของผู้ตอบที่เข้าเกณฑ์ในแต่ละกลุ่ม")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2, frameon=False, fontsize=11)
    fig.subplots_adjust(left=0.33, right=0.98, top=0.87, bottom=0.15)
    finish(fig, identifier)


def sampling():
    frame = read("T10_planned_vs_achieved_region")
    fig, ax = plt.subplots(figsize=(12, 8))
    ys = np.arange(len(frame))
    ax.barh(ys-0.18, frame["Planned total"], height=0.32, color="#cdd9da", label="ตามแผน")
    ax.barh(ys+0.18, frame["Achieved total"], height=0.32, color=COLORS[1], label="เก็บได้จริง")
    for i, row in frame.iterrows():
        ax.text(row["Achieved total"]+3, i+0.18, str(row["Achieved total"]), va="center", fontsize=10)
    ax.set_yticks(ys, [f"เขต {int(r['Health region'])} · {r['Province sampled']}" for _, r in frame.iterrows()])
    ax.invert_yaxis(); clean(ax, 230)
    ax.set_xlabel("จำนวนผู้ตอบแบบสำรวจ (คน)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1), ncol=2, frameon=False)
    fig.subplots_adjust(left=0.25, right=0.96, top=0.92, bottom=0.13)
    finish(fig, "figure-a1")


def access():
    frame = read("T22_access_by_group")
    usage = read("T26_utilisation_binary")
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [1, 1.5]})
    waiting = ["<15 min", "15-29 min", "30-59 min", "1-2 h", "2-3 h", "3-4 h", "4 h+"]
    waiting_th = ["<15 นาที", "15–29 นาที", "30–59 นาที", "1–2 ชม.", "2–3 ชม.", "3–4 ชม.", "≥4 ชม."]
    shades = ["#fae5e3", "#efc4bf", "#df9992", "#cc6a67", "#b34550", "#8f2d42", "#622336"]
    left = np.zeros(4)
    for key, text, color in zip(waiting, waiting_th, shades):
        row = frame[frame["Measure"].str.strip() == key].iloc[0]
        values = np.array([_parse(row[g])[2] for g in GROUPS])
        axes[0].barh(np.arange(4), values, left=left, color=color, label=text, edgecolor="white", height=0.62)
        for i, value in enumerate(values):
            if value >= 8:
                axes[0].text(left[i]+value/2, i, f"{value:.0f}", ha="center", va="center",
                             color="white" if color in shades[3:] else "#252832", fontsize=10)
        left += values
    axes[0].set_yticks(range(4), LABELS); axes[0].invert_yaxis(); clean(axes[0])
    axes[0].set_xlabel("สัดส่วนตามเวลารอ ณ สถานพยาบาล (ร้อยละ)")
    axes[0].legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=4, fontsize=10, frameon=False)
    for i, group in enumerate(GROUPS):
        axes[1].scatter([_parse(v)[2] for v in usage[group]], np.arange(len(usage))+(i-1.5)*0.16,
                        color=COLORS[i], s=40, label=LABELS[i], zorder=3)
    axes[1].set_yticks(range(len(usage)), [label(v) for v in usage["Measure"]])
    axes[1].invert_yaxis(); clean(axes[1]); axes[1].set_xlabel("ร้อยละของผู้ตอบที่เข้าเกณฑ์ในแต่ละกลุ่ม")
    axes[1].legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, fontsize=10, frameon=False)
    fig.subplots_adjust(left=0.34, right=0.98, top=0.9, bottom=0.11, hspace=0.68)
    finish(fig, "figure-3")


def forest(identifier, table):
    frame = read(table)
    frame = frame[frame["Group"] == GROUPS[-1]].copy()
    fig, ax = plt.subplots(figsize=(13, max(5, len(frame)*0.43+1.6)))
    for i, (_, row) in enumerate(frame.iterrows()):
        color = COLORS[-1] if row["p (BH within family)"] < 0.05 else "#89979e"
        ax.plot([row["lo"], row["hi"]], [i, i], color=color, lw=2)
        ax.scatter(row["aOR"], i, color=color, s=45, zorder=3, edgecolor="white", linewidth=0.6)
        ax.text(1.04, i, f"{row['aOR']:.2f} ({row['lo']:.2f}–{row['hi']:.2f})", transform=ax.get_yaxis_transform(), va="center", fontsize=10)
    ax.axvline(1, color=INK, lw=0.8, linestyle="--")
    ax.set_xscale("log")
    lo = min(0.2, float(frame["lo"].min())*0.75)
    hi = max(4, float(frame["hi"].max())*1.15)
    ax.set_xlim(lo, hi)
    ticks = [x for x in [0.05, 0.1, 0.2, 0.5, 1, 2, 4, 8] if lo <= x <= hi]
    ax.set_xticks(ticks, [f"{value:g}" for value in ticks])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_yticks(range(len(frame)), [label(v) for v in frame["Outcome"]]); ax.invert_yaxis()
    clean(ax, None)
    ax.set_xlabel("อัตราส่วนโอกาสที่ปรับแล้ว (aOR) · เทียบกับกลุ่มโรงพยาบาลรัฐ")
    ax.text(1.04, 1.025, "aOR (95% CI)", transform=ax.transAxes, fontsize=11, fontweight="bold")
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker="o", color=COLORS[-1], lw=0, label="BH-adjusted p <0.05"),
               Line2D([0], [0], marker="o", color="#89979e", lw=0, label="BH-adjusted p ≥0.05")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.01), frameon=False, fontsize=10, ncol=2)
    fig.subplots_adjust(left=0.38, right=0.8, top=0.91, bottom=0.11)
    finish(fig, identifier)


def security():
    frame = read("T55_security_decomposition").iloc[1:]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    names = ["มั่นใจทั้งคุณภาพและการจ่าย", "มั่นใจคุณภาพ แต่ไม่มั่นใจการจ่าย", "ไม่มั่นใจคุณภาพ แต่มั่นใจการจ่าย", "ไม่มั่นใจทั้งสองด้าน"]
    left = np.zeros(4)
    for (_, row), text, color in zip(frame.iterrows(), names, ["#34435b", "#bd3346", "#dc9993", "#d2d7df"]):
        vals = np.array([_parse(row[g])[2] for g in GROUPS])
        ax.barh(range(4), vals, left=left, height=0.62, color=color, label=text, edgecolor="white")
        for i, value in enumerate(vals):
            if value >= 5:
                ax.text(left[i]+value/2, i, f"{value:.1f}", va="center", ha="center", fontsize=11, color="white" if color in ["#34435b", "#bd3346"] else "#252832")
        left += vals
    ax.set_yticks(range(4), LABELS); ax.invert_yaxis(); clean(ax)
    ax.set_xlabel("ร้อยละของผู้ตอบในแต่ละกลุ่ม")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, fontsize=10, frameon=False)
    fig.subplots_adjust(left=0.23, right=0.98, top=0.76, bottom=0.2)
    finish(fig, "security-states")


def chart(identifier, title, caption, tables, category, note=""):
    for table in tables:
        shutil.copy2(TABLES / f"{table}.csv", DATA / f"{table}.csv")
    png = CHARTS / f"{identifier}.png"
    if identifier == "figure-3":
        preview = pd.concat([read("T22_access_by_group"), read("T26_utilisation_binary")], ignore_index=True)
    else:
        preview = read(tables[0])
    if identifier in {"figure-6", "figure-a2"}:
        preview = preview[preview["Group"] == GROUPS[-1]].copy()
    if identifier == "security-states":
        preview = preview.iloc[1:].copy()
    if "Measure" in preview:
        preview["Measure"] = preview["Measure"].map(label)
    if "Outcome" in preview:
        preview["Outcome"] = preview["Outcome"].map(label)
    preview = preview.rename(columns={"Measure": "รายการ", "Outcome": "ผลลัพธ์", **dict(zip(GROUPS,LABELS))})
    preview.to_csv(DATA / f"{identifier}.csv", index=False)
    return {"id": identifier, "title": title, "caption": caption, "note": note,
            "category": category, "source": "PVS Thailand · " + ", ".join(tables),
            "png": f"assets/figures/{identifier}.png", "svg": f"assets/figures/{identifier}.svg",
            "svg_dark": f"assets/figures/{identifier}-dark.svg",
            "csv": f"assets/data/{identifier}.csv", "alt": title + " — " + caption,
            "source_tables": tables, "sha256": hashlib.sha256(png.read_bytes()).hexdigest()}


def build(report_metadata=None):
    setup()
    sampling()
    grouped("figure-1", "T24_profile_binary")
    grouped("figure-2", "T25_reasons_binary")
    access()
    grouped("figure-4", "T30_preventive_descriptive")
    grouped("figure-5", "T50_experience_by_usual_group", experience=True)
    forest("figure-6", "T90_all_adjusted_combined")
    forest("figure-a2", "T31_preventive_adjusted")
    security()
    from .story_maps import draw_thailand
    fig, ax = plt.subplots(figsize=(11, 9))
    draw_thailand(ax); fig.subplots_adjust(bottom=0.08)
    finish(fig, "map-thailand")
    charts = [
        chart("map-thailand", "เสียงจาก 13 จังหวัดที่เก็บตัวอย่าง", "เลือกหนึ่งจังหวัดต่อเขตสุขภาพ รวม 2,017 คน สีแสดงจำนวนตัวอย่าง ไม่ใช่อัตราสุขภาพระดับจังหวัด", ["T10_planned_vs_achieved_region"], "พื้นที่และวิธีศึกษา", "จังหวัดสีเทาไม่ได้อยู่ในพื้นที่เก็บตัวอย่าง การเลือกจังหวัดไม่ทำให้ผลเป็นตัวแทนทุกจังหวัดในเขตสุขภาพ"),
        chart("figure-a1", "จำนวนตัวอย่างตามแผนและที่เก็บได้จริง", "แผน 2,000 คน เทียบกับข้อมูลที่เก็บได้จริง 2,017 คน แยกตามจังหวัดใน 13 เขตสุขภาพ", ["T10_planned_vs_achieved_region"], "พื้นที่และวิธีศึกษา"),
        chart("figure-1", "ลักษณะของผู้ใช้แหล่งบริการประจำสี่กลุ่ม", "จุดคือร้อยละในแต่ละกลุ่ม เส้นคือช่วงความเชื่อมั่น 95% แบบ Wilson ใช้ข้อมูลที่ตอบได้ตามเกณฑ์ของแต่ละข้อ", ["T24_profile_binary"], "ผู้ใช้บริการ", "การมีประกันสุขภาพไม่ได้ยืนยันว่าใช้สิทธินั้นจ่ายค่ารักษาในครั้งที่รายงาน"),
        chart("figure-2", "เหตุผลในการเลือกแหล่งบริการประจำ", "เหตุผลหลักที่ผู้ตอบเลือกเพียงหนึ่งข้อ แสดงหกเหตุผลสำคัญโดยใช้ฐานผู้มีแหล่งบริการประจำ", ["T25_reasons_binary"], "ผู้ใช้บริการ", "เหตุผลที่ระบุไม่ใช่ข้อมูลการลงทะเบียนหรือผู้จ่ายค่าบริการ"),
        chart("figure-3", "การเข้าถึงและรูปแบบการใช้บริการ", "ส่วนบนแสดงการกระจายเวลารอ ณ สถานพยาบาล ส่วนล่างแสดงรูปแบบการใช้บริการตามช่วงเวลาที่ระบุในข้อคำถาม", ["T26_utilisation_binary", "T22_access_by_group"], "การเข้าถึงบริการ", "ข้อคำถามแต่ละข้อมีช่วงเวลาอ้างอิงต่างกัน จึงไม่ควรตีความทุกแถวเป็นการใช้บริการในรอบปีเดียวกัน รายการใช้สถานพยาบาลแห่งเดียวคัดเฉพาะผู้ที่ใช้บริการมากกว่า 1 ครั้งใน 12 เดือน (1,238 คน) เนื่องจากผู้ไปครั้งเดียวย่อมตอบว่าใช้แห่งเดียวโดยปริยาย ตัวหารจึงต่างจากแถวอื่น"),
        chart("figure-4", "การได้รับบริการป้องกันและคัดกรอง", "ร้อยละการได้รับบริการตามคำตอบข้อ Q27 พร้อมช่วงความเชื่อมั่น 95%", ["T30_preventive_descriptive"], "การเข้าถึงบริการ", "การได้รับบริการในช่วง 12 เดือนที่ผ่านมา ไม่ได้บอกว่าได้รับบริการจากสถานพยาบาลประจำ และไม่ใช่ความครอบคลุมตามเกณฑ์อายุหรือความเสี่ยง"),
        chart("figure-5", "ประสบการณ์ในการรับบริการครั้งล่าสุด", "ร้อยละที่ประเมินแต่ละด้านว่าดีมากหรือดีเยี่ยม แยกตามแหล่งบริการประจำ", ["T50_experience_by_usual_group"], "ประสบการณ์", "สถานพยาบาลครั้งล่าสุดอาจไม่ใช่แหล่งบริการประจำ ตัวหารตัดคำตอบที่ไม่เข้าข่ายออกตามข้อคำถาม"),
        chart("figure-6", "ความแตกต่างหลังปรับปัจจัยร่วม", "อัตราส่วนโอกาสที่ปรับแล้วของกลุ่มโรงพยาบาลเอกชน เทียบกับกลุ่มโรงพยาบาลรัฐ เส้นแสดงช่วงความเชื่อมั่น 95%", ["T90_all_adjusted_combined"], "การวิเคราะห์ปรับปัจจัย", "ปรับอายุ เพศ การศึกษา รายได้ เขตที่อยู่อาศัย สิทธิสุขภาพ สุขภาพตนเอง และโรคเรื้อรัง คำนึงถึงการเกาะกลุ่มระดับตำบล สีแดงแสดงนัยสำคัญหลังปรับ BH ภายในกลุ่มผลลัพธ์ เป็นความสัมพันธ์ ไม่ใช่ผลเชิงสาเหตุ"),
        chart("figure-a2", "บริการป้องกันหลังปรับปัจจัยร่วม", "เปรียบเทียบกลุ่มโรงพยาบาลเอกชนกับโรงพยาบาลรัฐ โดยมีช่วงความเชื่อมั่น 95% และการปรับการทดสอบหลายครั้ง", ["T31_preventive_adjusted"], "การวิเคราะห์ปรับปัจจัย", "การตรวจความดันใช้แบบจำลองลดรูป ปรับอายุ เพศ และเขตที่อยู่อาศัย บริการอื่นใช้ปัจจัยร่วมเต็มชุด การคัดกรองเฉพาะหญิงใช้ฐานผู้ตอบหญิงและไม่ปรับเพศ ข้อคำถามบางส่วนยังมีข้อจำกัดด้านการตรวจสอบถ้อยคำ"),
        chart("security-states", "ความมั่นใจด้านคุณภาพและด้านการจ่ายไม่ใช่สิ่งเดียวกัน", "แจกแจงความมั่นใจเป็นสี่สถานะ เพื่อแยกช่องว่างด้านคุณภาพออกจากด้านความสามารถในการจ่าย", ["T55_security_decomposition"], "ความเชื่อมั่น", "เป็นการรับรู้เมื่อสมมติว่าป่วยหนัก ไม่ใช่ข้อมูลรายจ่ายจริงหรือการประเมินภาวะล้มละลายจากค่ารักษา"),
    ]
    from .story_overview import build_overview
    from .report_figures import build as report_figures, private_routes
    charts = build_overview() + report_figures() + [private_routes()] + charts
    report_numbers = {"figure-a1": 2, "map-thailand": 3, "figure-1": 7,
                      "figure-2": 8, "figure-3": 9, "figure-4": 10,
                      "figure-a2": 11, "figure-5": 12, "security-states": 13}
    chart_topics = {"map-thailand": "พื้นที่ศึกษา", "figure-a1": "จำนวนผู้ตอบ",
                    "figure-1": "ลักษณะผู้ใช้บริการ", "figure-2": "เหตุผลที่เลือก",
                    "figure-3": "เวลารอและการใช้บริการ", "figure-4": "บริการป้องกัน",
                    "figure-a2": "บริการป้องกันเมื่อปรับปัจจัย", "figure-5": "ประสบการณ์รับบริการ",
                    "figure-6": "ผลปรับปัจจัยร่วม", "security-states": "มั่นใจคุณภาพและจ่ายไหว"}
    for item in charts:
        # Topic labels explain the choice without requiring the Word report.
        # Preserve figure numbering separately for report cross-references.
        if item["id"] in report_numbers:
            item["report_figure"] = report_numbers[item['id']]
        item["label"] = chart_topics.get(item["id"], item.get("label", item["title"]))
    story = make_story(charts)
    if report_metadata is not None:
        story['report'] = report_metadata
    (ASSETS / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    (ASSETS / "story-data.js").write_text("window.PVS_STORY = " + json.dumps(story, ensure_ascii=False) + ";\n", encoding="utf-8")
    with zipfile.ZipFile(ASSETS / "pvs-thai-charts.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        def add(name, content):
            # Fixed timestamps: an unchanged chart set rebuilds to an identical ZIP.
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
        for item in charts:
            for key in ["png", "svg"]:
                path = SITE / item[key]
                add(path.name, path.read_bytes())
        add("README.txt", "กราฟจากเว็บไซต์สำหรับใช้ในรายงานและสไลด์\n" + CREDIT + "\nคำอธิบาย ตัวหาร และข้อจำกัด: ดู story.json\n")
        add("story.json", (ASSETS / "story.json").read_bytes())
        for file in sorted((ROOT / "content/geography").iterdir()):
            if file.is_file(): add("geography/" + file.name, file.read_bytes())
        for file in sorted((ASSETS / "sources").rglob("*")):
            if file.is_file(): add(str(file.relative_to(ASSETS)), file.read_bytes())
        for path in sorted({item["csv"] for item in charts}):
            add("data/" + Path(path).name, (SITE / path).read_bytes())
    from .web_assets import stamp_assets
    stamp_assets(SITE)
    print(f"Built {len(charts)} shared Thai charts as PNG/SVG and public storytelling data.")
    return story


def make_story(charts):
    from .story_content import make_story as compose
    return compose(charts, CREDIT)


if __name__ == "__main__":
    build()
