#!/usr/bin/env python3
"""Audit public national/international aggregates and the generated site CSV.

Run from any directory with ``python3 tools/verify_comparisons.py``. This check
uses only public CSV/JSON files and the Python standard library. It never reads
the respondent export, legacy notebook, or private mapping files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
import sys


ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = {
    "ETH", "KEN", "ZAF", "PER", "COL", "MEX", "URY", "ARG",
    "LAO", "IND", "KOR", "GRC", "ITA", "GBR", "USA",
}
GROUP_N = {
    "all": 2017, "municipal": 697, "non_municipal": 1320,
    # The broad public-sector group also includes three setting="other"
    # respondents excluded from the narrower four-provider analysis cohort.
    "has_usual": 1529, "no_usual": 488, "public": 1252, "private": 269,
}
Q40_COUNTS = {
    "maternal": (458, 1650), "child": (426, 1702),
    "chronic_care": (516, 1787), "mental_care": (350, 1648),
}
USUAL_COUNTS = {
    "usual_public_primary": 634, "usual_public_hospital": 615,
    "usual_private_clinic": 142, "usual_private_hospital": 127,
    "usual_none": 488, "usual_other": 11,
}


class ValidationError(ValueError):
    """A public aggregate or generated file disagrees with its documented source."""


def check(condition, message):
    if not condition:
        raise ValidationError(message)


def read_csv(relative):
    with (ROOT / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def unique_index(rows, columns, label):
    indexed = {}
    for row in rows:
        key = tuple(row[column] for column in columns)
        check(key not in indexed, f"{label}: duplicate key {key}")
        indexed[key] = row
    return indexed


def integer(value, label):
    number = float(value)
    check(math.isfinite(number) and number.is_integer(), f"{label}: not an integer: {value}")
    return int(number)


def near(actual, expected, label, tolerance=0.00011):
    check(math.isfinite(float(actual)) and abs(float(actual) - expected) <= tolerance,
          f"{label}: got {actual}, expected {expected}")


def wilson(n, denominator):
    proportion = n / denominator
    z = NormalDist().inv_cdf(0.975)
    divisor = 1 + z * z / denominator
    centre = (proportion + z * z / (2 * denominator)) / divisor
    half = z * math.sqrt(proportion * (1 - proportion) / denominator
                         + z * z / (4 * denominator * denominator)) / divisor
    return max(0, 100 * (centre - half)), min(100, 100 * (centre + half))


def verify():
    foreign_path = "content/international/values.csv"
    foreign = read_csv(foreign_path)
    foreign_index = unique_index(foreign, ("metric_id", "country_iso"), "international source")
    check(len(foreign) == 223, f"Expected 223 published values, got {len(foreign)}")
    metrics = read_json("content/international/metrics.json")
    metric_ids = {row["id"] for row in metrics}
    check(len(metrics) == len(metric_ids) == 14, "Expected fourteen unique international metrics")
    check({row["metric_id"] for row in foreign} == metric_ids, "Source metric coverage mismatch")
    sources = read_json("content/international/sources.json")
    actual_hash = hashlib.sha256((ROOT / foreign_path).read_bytes()).hexdigest()
    check(actual_hash == sources["values_sha256"], "International source SHA256 mismatch")

    geography = read_json("content/geography/world-countries.geojson")
    country_geometry = {row["properties"]["iso"] for row in geography["features"]}
    for metric in metrics:
        selected = [row for row in foreign if row["metric_id"] == metric["id"]]
        expected = COUNTRIES - ({"GRC"} if metric["id"] == "unmet_need" else set())
        expected |= {"TOTAL"}
        check({row["country_iso"] for row in selected} == expected,
              f"{metric['id']}: wrong countries or missing published Total")
        check(len(selected) == metric["country_count_foreign"] + 1,
              f"{metric['id']}: documented country count mismatch")
        for row in selected:
            value = float(row["value_percent"])
            check(math.isfinite(value) and 0 <= value <= 100, f"Invalid percentage: {row}")
            check(row["source_id"] == metric["source_id"], f"Wrong source for {metric['id']}")
            check(row["source_locator"] == metric["source_locator"],
                  f"Wrong source locator for {metric['id']}")
            check(row["country_iso"] == "TOTAL" or row["country_iso"] in country_geometry,
                  f"No map geometry join for {row['country_iso']}")
            if row["country_iso"] == "ARG":
                check(row["unit_level"] == "province_Mendoza_only", "Argentina scope lost")

    unmet = read_json("content/international/unmet-need-table1.json")
    check(len(unmet) == 15, "Unmet-need Table 1 must have fourteen countries plus Total")
    for row in unmet:
        key = (row["metric_id"], row["country_iso"])
        near(foreign_index[key]["value_percent"], float(row["value_percent"]), f"Unmet source {key}")
        # Table 1 prints both the counts and the percentages. Their agreement
        # guards against accidentally substituting another paper's weighted series.
        near(row["value_percent"], round(100 * row["numerator_as_reported"]
                                        / row["sample_n_as_reported"], 1), f"Unmet n/N {key}")
    total = next(row for row in unmet if row["country_iso"] == "TOTAL")
    check((total["numerator_as_reported"], total["sample_n_as_reported"])
          == (3296, 23230), "Unmet Total must be 3296/23230 across fourteen countries")

    national = read_csv("content/national/national_summary.csv")
    national_index = unique_index(national, ("group_id", "measure_id"), "national source")
    check({row["group_id"] for row in national} == set(GROUP_N), "Unexpected national group coverage")
    for row in national:
        key = (row["group_id"], row["measure_id"])
        n = integer(row["n"], f"{key} numerator")
        denominator = integer(row["N"], f"{key} denominator")
        excluded = integer(row["excluded"], f"{key} excluded")
        check(0 <= n <= denominator and excluded >= 0,
              f"Invalid national count/denominator {key}: {n}/{denominator}, excluded={excluded}")
        check(denominator + excluded == GROUP_N[row["group_id"]],
              f"Eligible + excluded does not reconcile to group size: {key}")
        if denominator == 0:
            check(key == ("no_usual", "own_quality"),
                  f"Unexpected empty eligible group: {key}")
            check(all(row[column] == "" for column in ("pct", "ci_low", "ci_high")),
                  f"An inapplicable outcome must not acquire a zero percentage: {key}")
            continue
        near(row["pct"], 100 * n / denominator, f"National percentage {key}")
        low, high = wilson(n, denominator)
        near(row["ci_low"], low, f"Wilson lower {key}")
        near(row["ci_high"], high, f"Wilson upper {key}")
    for measure, expected in Q40_COUNTS.items():
        row = national_index[("all", measure)]
        check((int(row["n"]), int(row["N"])) == expected,
              f"Q40 {measure}: changed corrected numerator/valid-answer denominator")
    usual = [row for row in national if row["group_id"] == "all" and row["domain"] == "usual_source"]
    check({row["measure_id"]: int(row["n"]) for row in usual} == USUAL_COUNTS,
          "Six-way usual-source partition disagrees with approved cohort counts")
    check(sum(int(row["n"]) for row in usual) == 2017, "Usual-source partition must total 2017")

    join = read_json("content/international/thai-indicator-join.json")["join"]
    check(set(join) == metric_ids and len(set(join.values())) == 14,
          "Thai crosswalk must map all fourteen international metrics uniquely")
    combined = read_csv("site/assets/data/international_comparison.csv")
    combined_index = unique_index(combined, ("metric_id", "country_iso"), "site comparison")
    expected_keys = set(foreign_index) | {(metric, "THA") for metric in metric_ids}
    check(set(combined_index) == expected_keys and len(combined) == 237,
          "Site comparison must contain 223 source rows and fourteen separate Thai rows")
    for key, source_row in foreign_index.items():
        row = combined_index[key]
        near(row["value_percent"], float(source_row["value_percent"]), f"Site foreign value {key}")
        for column in ("source_id", "source_locator", "unit_level", "verification"):
            check(row[column] == source_row[column], f"Site source metadata changed: {key}, {column}")
    for metric, measure in join.items():
        row = combined_index[(metric, "THA")]
        thai = national_index[("all", measure)]
        near(row["value_percent"], round(float(thai["pct"]), 1), f"Site Thai value {metric}")
        check(row["source_id"] == "pvs_thailand" and row["source_locator"] == measure,
              f"Site Thai source join is wrong for {metric}")
        check(row["unit_level"] == "unweighted_13_province_sample", f"Thai sample scope lost: {metric}")

    scopes = read_json("content/international/spatial-scope.json")
    check(scopes["ARG"]["shade_country"] is False and scopes["TOTAL"]["render"] == "do_not_map",
          "Mendoza-only scope or non-geographic Total rule lost")
    check(scopes["ARG"]["point"]["coordinates"] == [-68.818557, -32.881384],
          "Mendoza locator differs from the documented Natural Earth point")
    return (len(foreign), len(national), len(combined))


def main():
    try:
        foreign, national, combined = verify()
    except (OSError, KeyError, ValueError, ZeroDivisionError) as error:
        print(f"Comparison validation FAILED: {error}", file=sys.stderr)
        return 1
    print(f"Comparison validation passed: {foreign} published values; {national} national rows; "
          f"{combined} site comparison rows. Fourteen Thai joins, corrected Q40 denominators, "
          "Wilson intervals, geography scope and the 2,017-person partition agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
