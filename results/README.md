# Selected September research outputs

This release contains the September revision figures, tables, and final English report selected by the repository owner for public sharing.

**Questionnaire clarification, 1 October 2026:** The researcher checked the original
questionnaire and confirmed that preventive services (Q27), unmet need (Q29), and
borrowing/sale of assets for care (Q31) refer to the **past 12 months**. Earlier
wording in this historical English report, Figure 4 and inventory/model notes
that describes those items as unbounded or lifetime recall is superseded by
[the confirmation record](../content/questionnaire/recall-confirmation.json).
The numerical estimates and file checksums remain unchanged. Current website
notes and working report generators use the corrected recall periods.

| Location | Contents |
| --- | --- |
| [2026-09/figures/](2026-09/figures/) | Nine PNG figures, including appendix figures A1 and A2 |
| [2026-09/tables/](2026-09/tables/) | 61 CSV tables, including inventories and model notes |
| [2026-09/report.docx](2026-09/report.docx) | Customers of private hospitals in the Thai health system |
| [2026-09/manifest.csv](2026-09/manifest.csv) | Source paths, release paths, sizes, and SHA-256 checksums |

These files were copied from `output/revision_2026-09/` during repository preparation. The manifest identifies each source file; the report was renamed only in the release copy.

**Refreshed on 1 October 2026.** Eight artifacts were regenerated and replaced after the
continuity measure was corrected: Q20 ("were all your visits to the same facility?") was fielded to
everyone with at least one visit, so respondents who attended exactly once answered "one facility"
as a matter of arithmetic and inflated every group. The measure now restricts to respondents with
more than one visit in twelve months (n = 1,238). The affected files are
`T21_utilisation_by_group.csv`, `T26_utilisation_binary.csv`, `T59_core_outcomes_adjusted.csv`,
`T90_all_adjusted_combined.csv`, `questionnaire_inventory.csv`,
`Figure 3 - Access and utilisation.png`, `Figure 6 - Adjusted differences private hospital users.png`
and `report.docx`. Their manifest rows carry updated sizes, checksums and source paths pointing at
`output/`; the other 63 artifacts are unchanged from the September release.

After repository reorganization, those original working files are preserved locally under `archive/legacy/output/revision_2026-09/`. Manifest source paths describe their locations at the time the release was prepared. New runs write to `output/`; they do not update this release snapshot.

Raw responses, the prepared respondent frame, cached model objects, the notebook's saved outputs, earlier reports, and internal revision notes are excluded from this release. The additional chart-data workbook and segmentation workbook are also outside this selected set.

See the [reproduction guide](../docs/reproduction.md) for how the code generates working outputs and for the limits of the validation performed.

These research outputs are outside the repository's MIT software license. Their existing rights are retained; publishing this selected set does not assign an additional reuse license to the research materials.
