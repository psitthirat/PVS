# PVS Thailand

Analysis of the People's Voice Survey in Thailand, focusing on usual sources of care, service use, patient experience, and confidence in the health system. The survey contains 2,017 respondents; individual responses are not included in this repository.

**Website:** <https://psitthirat.github.io/PVS/>. It is a Thai storytelling site following the author's October report in two parts: **overall health-system findings** (including international comparisons) and **usual private-hospital users**. It has red-accented light/dark themes, reading, presentation and exploration modes, and 32 downloadable charts.

**Full report:** the reviewed Thai report is supplied by email request to [peerasit.sit@mahidol.ac.th](mailto:peerasit.sit@mahidol.ac.th). It has passed the numerical recheck with no remaining findings; its checksum, review scope and contact are recorded in [the report release record](content/report-release.json).

## Where things are

| Folder | What it holds | Edit it? |
| --- | --- | --- |
| [`src/pvs/`](src/pvs/) | All code: cleaning, models, tables, figures, reports and the website build | Yes |
| [`content/`](content/) | Public inputs for the website: national and international aggregates, maps, fonts, report release record | Yes |
| [`site/`](site/) | The published website. `index.html`, `app.js`, `styles.css` are hand-written; `site/assets/` is generated | Only the three page files |
| [`results/2026-09/`](results/2026-09/) | Frozen, approved September release: [9 figures](results/2026-09/figures/), [61 tables](results/2026-09/tables/), [English report](results/2026-09/report.docx) | No ([release notes](results/README.md)) |
| [`notebooks/analysis.ipynb`](notebooks/analysis.ipynb) | Guided notebook; shows released results by default | Yes |
| [`docs/`](docs/) | Guides and records (below) | Yes |
| [`tests/`](tests/), [`tools/`](tools/) | Public checks, private report audit, local preview server | Yes |
| `data/` | Private survey inputs; only [its README](data/README.md) is in Git | Local only |
| `output/`, `archive/` | Working outputs and historical files; ignored by Git | Local only |

| Guide | Read it to |
| --- | --- |
| [docs/website.md](docs/website.md) | Change, rebuild, check and publish the website (includes a “where to edit” table) |
| [docs/reproduction.md](docs/reproduction.md) | Install the environment and rerun the analysis |
| [docs/validation.md](docs/validation.md) | See what was verified, when, and its limits |
| [docs/report-editorial-notes.md](docs/report-editorial-notes.md) | Understand report coverage, definitions and data provenance |

## Quick start

Use Python 3.13 from the project root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
```

| Task | Command | Needs private data? |
| --- | --- | --- |
| Rebuild the website and chart downloads | `python -m pvs story` | No |
| Preview the website | `python3 tools/serve_site.py` | No |
| Run the public checks | see [website guide](docs/website.md#build-preview-and-check) | No |
| Rerun the full analysis into `output/` | `python -m pvs` (stages: `python -m pvs --help`) | Yes, see [input requirements](data/README.md) |

Running the analysis writes working files to `output/`; it never replaces the selected release in `results/`. The public files support inspection of code and results; they do not contain the respondent-level inputs needed to reproduce the analysis itself. For the notebook, install `python -m pip install -e '.[notebook]'` and see the [reproduction guide](docs/reproduction.md).

## Interpretation

The analysis compares public primary care, public hospital OPD/ER, private clinic/pharmacy, and private hospital OPD/ER. Adjusted models use public hospital OPD/ER as the reference group. Standard errors clustered by subdistrict approximate the sampling structure; they are not full design-based survey inference. Associations should not be interpreted as causal effects. Details and limitations are in the report and model-note tables.

Q27, Q29 and Q31 refer to the **past 12 months**, as the researcher confirmed against the original questionnaire on 1 October 2026. Historical September artifacts keep their recorded bytes; their older recall notes are superseded by the [release clarification](results/README.md).

## Citation and contact

Software citation metadata are provided in [`CITATION.cff`](CITATION.cff):

> Sitthirat, Peerasit. PVS Thailand: People's Voice Survey analysis. Version 2026.09.

This identifies the software; the study's complete research authorship and any future article citation are separate. No DOI has been assigned.

**Peerasit Sitthirat (พีรสิชฌ์ สิทธิรัตน์)**  
ผู้วิเคราะห์ข้อมูล / Data analyst  
Faculty of Medicine Ramathibodi Hospital, Mahidol University  
คณะแพทยศาสตร์โรงพยาบาลรามาธิบดี มหาวิทยาลัยมหิดล  
Contact: [peerasit.sit@mahidol.ac.th](mailto:peerasit.sit@mahidol.ac.th)

For code questions, use GitHub Issues. For data-access inquiries, email the contact above with your research purpose and requested inputs. Access is subject to the study team's decision; public code availability does not provide access to the underlying responses.

## Research project and funding

ภายใต้โครงการวิจัย **“การสังเคราะห์การแนวทางกำกับดูแลโรงพยาบาลเอกชนเพื่อสร้างระบบสุขภาพของประเทศไทยที่เป็นธรรม”** โดย **บริษัท วันโอวัน พับลิโก้ จำกัด** และ **คณะแพทยศาสตร์โรงพยาบาลรามาธิบดี มหาวิทยาลัยมหิดล** สนับสนุนโดยสถาบันวิจัยระบบสาธารณสุข ปีงบประมาณ **2569** ตามข้อตกลงเลขที่ **สวรส. 69-003**

## License

The code and software documentation use the [MIT License](LICENSE), following the [Open Source Initiative's MIT template](https://opensource.org/license/mit). Research outputs under `results/`, the Thai research narrative and aggregate data under `content/`, research content and exports under `site/`, survey inputs, and third-party materials are outside this software license; their existing rights are retained. The shared graphics credit บริษัท วันโอวัน พับลิโก้ จำกัด and คณะแพทยศาสตร์โรงพยาบาลรามาธิบดี มหาวิทยาลัยมหิดล. Fonts and map sources carry their own licenses, documented in the [website guide](docs/website.md#data-notes).
