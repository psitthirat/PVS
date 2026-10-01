# Public map boundaries

These files support the Thai report and storytelling website. They contain
administrative boundaries, public names and province-level sample counts from
the approved September tables. They contain no respondent locations.

| File | Source | License |
| --- | --- | --- |
| `thailand-provinces.geojson` | [geoBoundaries THA ADM1](https://www.geoboundaries.org/api/current/gbOpen/THA/ADM1/), OpenStreetMap / Wambacher | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| `world-countries.geojson` | [Natural Earth 1:110m countries](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson) | [Public domain](https://www.naturalearthdata.com/about/terms-of-use/) |
| `sampled-provinces.json` | Approved `results/2026-09/tables/T10_planned_vs_achieved_region.csv`; names joined to province ISO codes | Project research-output terms apply to sample counts; geographic label coordinates derive from the ODbL geometry |

The Thailand geometry is redistributed as an adapted database under ODbL 1.0,
separately from the repository's MIT-licensed code. Its upstream boundary ID is
`THA-ADM1-36821470`; represented year is 2017; upstream commit is `9469f09`.
Map graphics credit **© OpenStreetMap contributors · geoBoundaries / Wambacher ·
ODbL 1.0**. The adapted database is supplied here for download and reuse under
the source license. Copyright notices for the report or charts do not replace
this attribution or restrict the public-domain Natural Earth source data.
The complete canonical ODbL text is bundled as `LICENSE-ODbL.txt`, downloaded
from <https://opendatacommons.org/licenses/odbl/odbl-10.txt> on 2026-09-30.
`LICENSE-Natural-Earth.txt` records the world-map source's public-domain terms.

Coordinates are WGS84 longitude/latitude. Thailand polygons were simplified
with Shapely's topology-preserving Douglas–Peucker algorithm at 0.006 degrees
and rounded to four decimal places. Adjacent provinces were simplified
independently, so the geometry is intended for illustration, not geospatial
measurement. World polygons retain Natural Earth's geometry, with coordinates
rounded to four decimal places and unrelated properties removed. Thai label
points are representative interior points derived from the geometry; world
label points come from Natural Earth's `LABEL_X` and `LABEL_Y` fields.
After rounding, a Sudan self-intersection and a degenerate North Korea ring
were repaired with Shapely `make_valid`, retaining polygon components only.

`metadata.json` records original URLs, hashes, processing, licenses, join keys,
the 13-province crosswalk, and the primary paper supporting the contextual
international comparison. `geoboundaries-source.json` preserves the downloaded
upstream metadata. These files can be used offline by the story builder.

## Interpretation

The Thai map displays **sample coverage and achieved respondent counts** in
13 selected provinces, one in each health region (2,017 people). The remaining
64 provinces are grey and mean **no sample**, not zero prevalence. Province
shading must never be presented as an estimate of health outcomes across
Thailand. Province identifiers and health-region numbers serve different
purposes and are kept separate.

The world maps now support the multi-country confidence, health-system opinion,
quality and unmet-need series recovered from the original Thai report and
verified against primary PVS publications. Their data and provenance are in
`content/international/`. Colours show published percentages for a selected
metric; they do not establish a harmonised country ranking. Countries without
data stay grey, and a published `Total` is never mapped.

Argentina estimates apply only to Mendoza Province. Keep its national polygon
grey and use the sourced Mendoza provincial-capital locator from
`content/international/spatial-scope.json`. The locator identifies the province
for readers; it is not a respondent location or a city-level estimate. Show
Thailand distinctly as an unweighted sample from 13 selected provinces.

The sources differ in sampling, weighting, period, mode and context. Foreign
and Thai unmet need both refer to the previous 12 months, following the
researcher's check of the original Thai questionnaire on 1 October 2026. The Croke et al. unmet-need total covers 14 countries;
Kruk et al. confidence and quality figures cover 15. Both studies include adults
aged 18+, and the Kruk methods specify sampling/post-stratification weighting;
these details were marked unverified in the historical T81 table, which remains
preserved unchanged. Item-specific valid-answer denominators, particularly the
restored Thai Q40 quality items, must remain clear when comparing series.
