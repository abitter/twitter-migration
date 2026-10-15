# Country / region analysis (Supplementary Appendix 6)

Migration rates by country and region of researchers' 2022 affiliation, added in the revision
(September 2026).

**Pipeline**
1. `r2r_check_nationalities_v2.ipynb`, section 1: matches the final sample to OpenAlex author ids
   via the crosswalk of Mongeon et al. (2023; version 2, Mongeon et al., 2024), writes
   `author_ids_to_fetch_v2.csv`.
2. `fetch_openalex_v2.py --wait`: downloads the author records (`openalex_results_v2.json.gz`);
   resumable, runs over several days on the free OpenAlex tier. Set `OPENALEX_MAILTO` to your
   e-mail for the polite pool.
3. Notebook, sections 3–6: assigns the 2022 affiliation country and writes
   `table_s3_countries_v2.csv`, `table_s3_regions_v2.csv`, `table_s3_sensitivity_v2.csv`.
4. `migration_map.R`: world map of country-level rates (`results/figures/supplementary_migration_map_countries.png`).

**Data files not in the repository**: the crosswalk `authors_tweeters_2024_02.csv`
(https://doi.org/10.5281/zenodo.10905839), the OpenAlex records `openalex_results_v2.json.gz`, and
the per-researcher intermediates `profiles_*_v2.csv.gz`, which link Twitter ids to migration status
and country. They live in the shared data folder set in `config.yml`
(`paths.data.processed.countries`); only the aggregate tables and the unresolved-id list are here.

Paths in the notebook and scripts are absolute and need adjusting on another machine.
