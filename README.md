# Academic Social Media Migration Through a Psychology of Science Lens

This repository contains the code and processed data for the study "Academic Social Media Migration Through a Psychology of Science Lens" by Bittermann, Lauer, and Peters, on the role of academic influencers and the open science movement in the migration of researchers from Twitter to Mastodon in late 2022.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Requirements and Setup](#requirements-and-setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Results](#results)
- [License](#license)

## Overview

The study investigates how academic influencers and the open science movement shaped researchers' migration from Twitter to Mastodon following Elon Musk's acquisition of Twitter. Using a theory-driven, large-scale data analysis, it shows that both the social impact of fellow researchers discussing the migration and the endorsement of open science are associated with a higher likelihood of academics moving to Mastodon.

The key steps of the project include:
- Collecting Academic Twitter and Mastodon accounts and establishing a link between them
- Collecting all tweets related to the topic of TwitterMigration
- Identifying influencers regarding the topic of TwitterMigration
- Collecting all followers of influencers in order to link them to the Academic twitter accounts
- Calculating social impact on each academic based on the influencers they follow
- Analyzing and predicting migration behavior based on social impact and open science endorsement on the user. 

The main script main.py goes through and explains all steps of data collection, preprocessing, and analysis (see below). 

## Project Structure

The directory structure of this project is as follows:

```
├── code/
│   ├── main.py
│   ├── data_collection/
│   ├── initial_processing/
│   ├── main_processing/
│   ├── statistical_analysis/
│   ├── utils/
│   └── revision/
├── data/
│   └── final_analyzed.csv
├── results/
│   └── figures/
├── config.yml
├── environment.yml
├── README.md
```

- `code/`: Contains all the scripts for data collection, processing, and analysis. The main script main.py goes through all steps, importing functions from the following subdirectories.
  - `data_collection/`: Scripts for collecting data from Twitter, Mastodon, and OpenCheck 
  - `initial_processing/`: Scripts for cleaning and preprocessing raw data.
  - `main_processing/`: The main processing needed for social impact, open science endorsement, and migration behavior
  - `statistical_analysis/`: Code for statistical/ML analysis on the preprocessed data (`analysis.R`).
  - `utils/`: Utility functions used across the project.
  - `revision/`: Additional analyses added in the revision (September 2026), see below.
  
- `data/`: Directory for storing data. `final_analyzed.csv` contains the final analyzed data used in the modelling. Raw data and metadata are not available for privacy/legal reasons. 

- `results/`: Contains the final results and figures generated from the analysis.

- `config.yml`: Configuration file to customize paths and parameters (e.g., API keys, data paths).

- `environment.yml`: The Conda environment file to reproduce the project's environment.

## Requirements and Setup

This project requires both Python and R for full functionality. The necessary Python dependencies are managed through [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/), while the statistical/ML analysis steps require R. You can install R from [here](https://cran.r-project.org/), or through [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/).

Note that full reproduction of the results requires access to the raw data (see config), which cannot be shared publicly due to privacy and legal reasons. 

To set up and run this project, if raw data is available, follow these steps:

1. **Clone the repository:**

   ```
   git clone https://github.com/abitter/twitter-migration.git
   cd twitter-migration
   ```

2. **Create and activate the Conda environment**:

    The provided environment.yml file contains the necessary dependencies for the project.

    ```
    conda env create -f environment.yml
    conda activate twittermigration
    ```

3. **Install additional R packages (if needed):**

    If certain R packages are not included in the Conda environment or need updating, you can install them directly in R:

    ```
    install.packages(c("mgcv", "jsonlite", "dplyr", "itsadug", "visibly", "iml", 
                        "shapr", "caret", "DHARMa", "kernelshap", "shapviz", 
                        "ggplot2", "gridExtra", "corrplot", "ggforce", 
                        "reshape2", "tidyr", "yaml", "patchwork", "cowplot"))
    ```

4. **Configure the project**:

    Modify the config.yml file to suit your environment. You can change paths, API keys, and other parameters as needed.

## Usage

The main script main.py goes through and explains all steps of the pipeline. Note that some steps are performed in R as described in the script.

If the raw data is not available, you can explore the final preprocessed and analyzed dataset used for modeling (`data/final_analyzed.csv`). However, note that metadata has been removed for privacy/legal reasons. That is, while the dependent variable (DV) and key features of interest are included, the covariates are not.

## Revision analyses

The following scripts were added in the revision (September 2026). They live in `code/revision/`, separate from the originally submitted pipeline; `analysis.R` itself is unchanged apart from one axis label. Each script is standalone, repeats the preprocessing it needs from `analysis.R`, and writes only new files or aggregate tables. Paths are absolute and need adjusting on another machine.

| Script | Supports |
|---|---|
| `code/revision/r2r_figure2_revision.R` | Figure 2 (axis spacing, odds ratio labels) |
| `code/revision/r2r_figure3_revision.R` | Figure 3 (predicted probabilities) and Supplementary Appendix 4 |
| `code/revision/r2r_influencer_concentration.R` | Supplementary Appendix 5 (concentration of the follow network) |
| `code/revision/r2r_number_vs_proportion.R` | Section 4.4, number vs. proportion of sources |
| `code/revision/r2r_check_nationalities/` | Supplementary Appendix 6 (migration rates by country and region) |
| `code/revision/r2r_open_science_examples/` | Supplementary Appendix 7 (context of open science terms) |
| `code/revision/r2r_excluded_researchers/` | Section 2.3 (excluded vs. included researchers) |

## Configuration
The config.yml file allows one to see at a glance important parameters and  modify the project configuration. Key parameters include:

- Paths for data and API keys/tokens for data collection
- URLs for data collection
- Datetime constants for defining migration period
- Patterns used for filtering and analysis (e.g. keywords for tweets related to TwitterMigration)
- Parameters for topic model used for social impact (-> similarity) analysis

## Results
The analysis results, including generated figures, are saved in the results/ directory. 

## Resources 

**Mastodon/Twitter**
- [`rtoot`](https://github.com/schochastics/rtoot) repo
- [`Mastodon.py`](https://github.com/halcy/Mastodon.py/tree/master) repo
- [`academics-on-mastodon`](https://github.com/nathanlesage/academics-on-mastodon) repo
- [OpenCheck list of academics on Twitter/Mastodon](https://opencheck.is/people)
- [An open data set of scholars on Twitter](https://doi.org/10.1162/qss_a_00250) by Mongeon et al. (2023) and the [dataset on Zenodo](https://doi.org/10.5281/zenodo.10905839)
- [Twitter API status 1](https://twitter.com/TwitterDev/status/1621026986784337922)  
- [Twitter API status 2](https://twitter.com/TwitterDev/status/1625234161010343941) (Update Feb 13)  
- [Twitter API status 3](https://twitter.com/TwitterDev/status/1626732269174943745) (Update Feb 18)

**Methods**
- [`transformers`](https://github.com/huggingface/transformers) repo
- [`sentence-transformers`](https://github.com/UKPLab/sentence-transformers) repo 
- [`BERTopic`](https://github.com/MaartenGr/BERTopic) repo
- [`pandarallel`](https://github.com/nalepae/pandarallel) repo
- [`beautifulsoup`](https://pypi.org/project/beautifulsoup4/)
- [`DHARMa`](https://github.com/florianhartig/DHARMa) repo
- [`kernelshap`](https://github.com/ModelOriented/kernelshap) repo

## License
This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
