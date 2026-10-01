"""Export national and area-stratified PVS aggregates from a prepared frame.

This module never loads raw survey inputs, cleans data or modifies dictionaries.
The optional command reads only a trusted local analysis_frame.pkl produced by
the study pipeline. Public story/report builds use the resulting CSV snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .analysis import prop_ci
from .paths import ROOT


GROUP_LABELS = {
    "all": "ผู้ตอบทั้งหมด", "municipal": "ในเขตเทศบาล", "non_municipal": "นอกเขตเทศบาล",
    "has_usual": "มีหน่วยบริการประจำ", "no_usual": "ไม่มีหน่วยบริการประจำ",
    "public": "หน่วยบริการประจำภาครัฐ", "private": "หน่วยบริการประจำภาคเอกชน",
}
RATING_LABELS = {"แย่": 0, "พอใช้": 1, "ดี": 2, "ดีมาก": 3, "ดีเยี่ยม": 4}


def q40_top2(values: pd.Series) -> pd.Series:
    """Map cleaned Thai Q40 labels; inapplicable/missing answers remain missing.

    Fail on unknown labels rather than silently classifying an unrecognised
    response as a low rating or excluding every valid observation.
    """
    observed = set(values.dropna().unique())
    unknown = observed - set(RATING_LABELS) - {"ไม่สามารถประเมินได้"}
    if unknown:
        raise ValueError("Unrecognised Q40 response labels")
    ordinal = values.map(RATING_LABELS)
    return ordinal.ge(3).astype("boolean").where(ordinal.notna(), pd.NA)


def aggregate(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return aggregate counts only, plus explicit definitions and exclusions."""
    df = frame.copy()
    groups = {
        "all": pd.Series(True, index=df.index),
        "municipal": df.municipality.eq("municipal"),
        "non_municipal": df.municipality.eq("non-municipal"),
        "has_usual": df.has_usual.eq("yes"), "no_usual": df.has_usual.eq("no"),
        "public": df.usual_sector.eq("public"), "private": df.usual_sector.eq("private"),
    }
    records, definitions = [], {}

    def add(domain, mid, label, values, positive, *, allowed=None, restriction=None, note=""):
        valid = values.notna()
        if restriction is not None:
            valid &= restriction
        definitions[mid] = {"domain": domain, "label": label, "positive": str(positive), "note": note}
        for gid in (allowed or groups):
            mask = groups[gid]
            den = int((mask & valid).sum())
            num = int((mask & valid & values.eq(positive)).sum())
            pct, lo, hi = prop_ci(num, den)
            records.append({"domain": domain, "measure_id": mid, "label": label,
                            "group_id": gid, "group_label": GROUP_LABELS[gid], "n": num, "N": den,
                            "excluded": int(mask.sum()) - den, "pct": round(pct, 4),
                            "ci_low": round(lo, 4), "ci_high": round(hi, 4)})

    area = ["all", "municipal", "non_municipal"]
    profile_sex = df.sex.astype(object).fillna("refused")
    for value, label in [("male", "ชาย"), ("female", "หญิง"), ("other", "เพศอื่น"), ("refused", "ไม่ประสงค์ระบุเพศ")]:
        add("profile_sex", "sex_"+value, label, profile_sex, value, allowed=area,
            note="ใช้ผู้ตอบทั้งหมดในพื้นที่เป็นตัวหารและแสดงผู้ไม่ระบุเพศแยก")
    for value, label in [("18-29", "18–29 ปี"), ("30-39", "30–39 ปี"), ("40-49", "40–49 ปี"),
                         ("50-59", "50–59 ปี"), ("60-69", "60–69 ปี"), ("70-79", "70–79 ปี"), ("80+", "80 ปีขึ้นไป")]:
        add("profile_age", "age_"+value, label, df.age_band, value, allowed=area,
            note="ใช้กลุ่มอายุ Q4 ที่มีข้อมูลครบ ไม่ใช้ exact age ที่ขาดข้อมูล")
    for i, (value, label) in enumerate([
        ("below primary", "ต่ำกว่าประถมศึกษา"), ("primary", "ประถมศึกษา"),
        ("lower secondary", "มัธยมศึกษาตอนต้น"), ("upper secondary/voc", "มัธยมศึกษาตอนปลาย/ปวช."),
        ("diploma/high voc", "อนุปริญญา/ปวส."), ("bachelor or above", "ปริญญาตรีขึ้นไป")]):
        add("profile_education", f"education_{i}", label, df.edu, value, allowed=area)
    income = df.income.astype(object).map({"<10k":"under30", "10-30k":"under30", "30-60k":"30to60", "60-100k":"60plus", "100k+":"60plus"})
    for val, label in [("under30", "ต่ำกว่า 30,000 บาท/เดือน"), ("30to60", "30,000–59,999 บาท/เดือน"), ("60plus", "60,000 บาท/เดือนขึ้นไป")]:
        add("profile_income", "income_"+val, label, income, val, allowed=area)
    scheme = df.scheme.astype(object).fillna("unknown")
    for value, label in [("UCS", "หลักประกันสุขภาพแห่งชาติ"), ("SSS", "ประกันสังคม"),
                         ("CSMBS", "สวัสดิการข้าราชการ"), ("other public", "สิทธิรัฐอื่น"), ("unknown", "ไม่ทราบสิทธิหลัก")]:
        add("profile_scheme", "scheme_"+value.replace(" ", "_"), label, scheme, value, allowed=area,
            note="ตัวหารรวมผู้ไม่ทราบสิทธิและแสดงเป็นแถวแยก; การถือครองสิทธิไม่ระบุผู้จ่ายจริง")
    add("profile_scheme", "private_insurance", "มีประกันสุขภาพเอกชน", df.priv_ins_owned, "yes", allowed=area,
        note="สิทธิเสริมอาจซ้อนกับสิทธิหลัก จึงไม่รวมกับสัดส่วนสิทธิหลักเป็น100%")

    items = [
        ("health", "health_good", "สุขภาพร่างกายดีขึ้นไป", "health_good3", "good or better"),
        ("health", "health_top2", "สุขภาพร่างกายดีมาก/ดีเยี่ยม", "health_top2", "very good/excellent"),
        ("health", "mental_good", "สุขภาพจิตดีขึ้นไป", "mental_good3", "good or better"),
        ("health", "chronic", "ภาวะเจ็บป่วยเรื้อรังตั้งแต่หกเดือน", "chronic", "yes"),
        ("health", "activation", "มั่นใจดูแลสุขภาพเชิงรุกทั้งสองข้อ", "activation", "high"),
        ("health", "activation_strict", "มั่นใจมากทั้งสองข้อ", "activation_strict", "high"),
        ("use", "admission", "นอนโรงพยาบาลใน 12 เดือน", "admit", "yes"),
        ("use", "unmet", "มีความจำเป็นแต่ไม่ได้รับบริการ", "unmet", "yes"),
        ("use", "homevisit", "ได้รับการเยี่ยมบ้านใน 12 เดือน", "homevisit_any", "yes"),
        ("use", "telemedicine", "ใช้บริการทางไกลใน 12 เดือน", "telemed_any", "yes"),
        ("use", "borrowed", "เคยกู้ยืม/ขายทรัพย์สินเพื่อรักษา", "borrowed_ever", "yes"),
        ("confidence", "good_care", "มั่นใจว่าจะได้รับบริการคุณภาพ", "conf_get", "confident"),
        ("confidence", "afford", "มั่นใจว่าจะจ่ายไหว", "conf_afford", "confident"),
        ("confidence", "security", "มั่นใจทั้งคุณภาพและจ่ายไหว", "health_security", "confident"),
        ("system_ratings", "improved", "ระบบดีขึ้นในสองปี", "sys_improved_bin", "improved"),
        ("system_ratings", "works_well", "ระบบทำงานดี/ปรับเพียงเล็กน้อย", "sys_endorse_bin", "works well"),
        ("system_ratings", "public_quality", "คุณภาพระบบรัฐดีมาก/ดีเยี่ยม", "q_public_top2", "very good/excellent"),
        ("system_ratings", "private_quality", "คุณภาพระบบเอกชนดีมาก/ดีเยี่ยม", "q_private_top2", "very good/excellent"),
        ("system_ratings", "listens", "มั่นใจว่ารัฐบาลรับฟังประชาชน", "conf_voice", "confident"),
        ("system_ratings", "covid", "การจัดการโควิด-19 ดีมาก/ดีเยี่ยม", "q_covid_top2", "very good/excellent"),
        ("own_provider", "own_quality", "หน่วยบริการประจำดีมาก/ดีเยี่ยม", "usual_qual_top2", "very good/excellent"),
    ]
    for domain, mid, label, var, positive in items:
        note = "ในช่วง 12 เดือนที่ผ่านมา" if mid in {"unmet", "borrowed"} else ""
        if domain == "confidence":
            note = "ความมั่นใจหากเจ็บป่วยรุนแรง ไม่ใช่ผลลัพธ์บริการหรือการจ่ายจริง"
        add(domain, mid, label, df[var], positive, note=note)
        definitions[mid]["variable"] = var
    for mid, label, var in [
        ("bp", "วัดความดันโลหิต", "bp_r"), ("sugar", "ตรวจน้ำตาลในเลือด", "sugar_r"),
        ("lipid", "ตรวจไขมันในเลือด", "lipid_r"), ("dental", "ตรวจสุขภาพช่องปาก", "dental_r"),
        ("vision", "ตรวจการมองเห็น", "vision_r"), ("mental_service", "รับบริการสุขภาพจิต", "mental_r"),
        ("breast", "ตรวจเต้านม/แมมโมแกรม (เพศหญิง)", "mammogram_r"),
        ("cervical", "ตรวจมะเร็งปากมดลูก (เพศหญิง)", "ca_cervix_r")]:
        restriction = df.sex.eq("female") if mid in {"breast", "cervical"} else None
        add("prevention", mid, label, df[var], "yes", restriction=restriction,
            note="รายงานว่าได้รับในช่วง 12 เดือนที่ผ่านมา ไม่ระบุสถานพยาบาล; breast/cervicalจำกัดเพศหญิง ไม่ใช่coverageตามเกณฑ์คัดกรอง")
        definitions[mid]["variable"] = var
    for mid, label, var in [("maternal", "บริการมารดา/หญิงตั้งครรภ์", "eval_maternal"),
                            ("child", "บริการเด็ก", "eval_ped"),
                            ("chronic_care", "บริการโรคเรื้อรัง", "eval_chronic"),
                            ("mental_care", "บริการสุขภาพจิต", "eval_mental")]:
        rating = q40_top2(df[var])
        add("system_ratings", mid, label + "ดีมาก/ดีเยี่ยม", rating, True,
            note="Q40: map exact Thai labels0–4; ดีมาก/ดีเยี่ยม>=3; excludeไม่สามารถประเมินได้ from denominator. Corrects numeric-prefix mapping mismatch in frozen September exports.")
        definitions[mid]["variable"] = var
        definitions[mid]["rating_map"] = RATING_LABELS

    # A complete, mutually exclusive full-sample usual-source distribution.
    source = df.provider_group.astype(object)
    source = source.mask(df.has_usual.eq("no"), "none").fillna("other")
    for mid, value, label in [
        ("usual_public_primary", "public primary care", "ปฐมภูมิภาครัฐ"),
        ("usual_public_hospital", "public hospital OPD/ER", "โรงพยาบาลรัฐ"),
        ("usual_private_clinic", "private clinic/pharmacy", "คลินิกหรือร้านยาเอกชน"),
        ("usual_private_hospital", "private hospital OPD/ER", "โรงพยาบาลเอกชน"),
        ("usual_none", "none", "ไม่มีหน่วยบริการประจำ"), ("usual_other", "other", "ประเภทอื่น/จำแนกสี่กลุ่มไม่ได้")]:
        add("usual_source", mid, label, source, value, allowed=area,
            note="ตัวหารผู้ตอบทั้งหมด; หกกลุ่มไม่ซ้ำกันและรวมครบ2,017คน")
    add("usual_coverage", "has_usual", "มีหน่วยบริการประจำ", df.has_usual, "yes", allowed=area)
    for value, label in [("public", "ภาครัฐ"), ("private", "ภาคเอกชน")]:
        membership = df.usual_sector.eq(value).astype(bool)
        add("usual_sector", "sector_"+value, label, membership, True, allowed=area,
            note="ตัวหารผู้ตอบทั้งหมด; publicรวมผู้ระบุสถานที่อื่น3คน จึงต่างจากผลรวมสองกลุ่มรัฐที่จำแนกสถานที่ได้")
    for value, label in [(False, "หน่วยบริการนอกโรงพยาบาล"), (True, "ผู้ป่วยนอก/ฉุกเฉินโรงพยาบาล")]:
        membership = df.usual_hospital.eq(value).astype(bool)
        add("usual_setting", "setting_hospital" if value else "setting_nonhospital", label, membership, True, allowed=area,
            note="ตัวหารผู้ตอบทั้งหมด; แบบสอบถามไม่ยืนยันระดับทุติยภูมิ/ตติยภูมิ จึงใช้ประเภทสถานที่")
    metadata = {
        "title": "ผลการศึกษาระดับกลุ่มตัวอย่างทั้งหมดและจำแนกพื้นที่",
        "source": "Canonical prepared PVS analysis frame; individual data are not published",
        "definition_code": "src/pvs/national.py:aggregate", "source_rows": len(df),
        "unweighted": True, "interval": "Wilson95%; not design-based national inference",
        "groups": GROUP_LABELS, "definitions": definitions,
        "recall_confirmation": "content/questionnaire/recall-confirmation.json; Q27/Q29/Q31: past 12 months, researcher confirmed original questionnaire on 2026-10-01",
        "q40_correction": "Frozen September Q40 columns expected numeric prefixes although cleaned response labels are Thai text. New summaries map five exact labels and exclude cannot-evaluate. Frozen source tables remain unchanged.",
        "no_new_models": "Restored national association questions use current descriptive comparisons. Superseded adjusted estimates are not recycled; existing September four-group models remain separate.",
    }
    return pd.DataFrame(records), metadata


def build(frame_path: Path, output_dir: Path | None = None) -> Path:
    """Export only aggregate rows from a trusted, locally produced pickle."""
    out = Path(output_dir or ROOT / "content/national")
    result, metadata = aggregate(pd.read_pickle(frame_path))
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "national_summary.csv", index=False)
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", type=Path, required=True, help="Trusted locally generated canonical frame")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    print(build(args.frame, args.out))


if __name__ == "__main__":
    main()
