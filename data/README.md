# Private analysis inputs

The survey and related working inputs stay local. This directory is ignored by Git except for this file. For data-access inquiries, email **Peerasit Sitthirat**, Faculty of Medicine Ramathibodi Hospital, Mahidol University, at [peerasit.sit@mahidol.ac.th](mailto:peerasit.sit@mahidol.ac.th), describing your research purpose and requested inputs. Access must be arranged with the study team; this is an inquiry route, not a guarantee of access. Do not attach participant data or confidential documents to public GitHub issues.

| Local path | Required content |
| --- | --- |
| `data/survey.xlsx` | Survey export, sheet `ส่งงาน` |
| `data/data_dict-survey.xlsx` | Existing validation dictionary, sheet `validate` |
| `data/reference/thai_report.docx` | Thai report whose first table supplies planned regional allocation |
| `data/mappings/*.csv` | Existing recoding maps used by the cleaning pipeline and coding audit |

The dictionary can contain examples drawn from individual responses. Recoding maps can contain observed response text. Both remain private with the survey until separately reviewed.

The Thai report can remain elsewhere on your computer. Set `PVS_THAI_REPORT` to its path before running the analysis:

```bash
export PVS_THAI_REPORT="/path/to/thai_report.docx"
```

The questionnaire inventory is transcribed into `src/pvs/inventory.py`; that module does not parse a questionnaire document. The international comparison values are encoded in the analysis, rather than extracted from a PDF during execution. Consult the original questionnaire and cited reference when reviewing those choices.

Use working copies of inputs: the existing cleaning pipeline refreshes a generated sheet in the dictionary, can write error extracts, and may update recoding maps or prompt for missing mappings.
