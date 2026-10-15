# Excluded vs. included researchers (Section 2.3)

`r2r_excluded_researchers.py` compares the 151,773 researchers excluded during sample construction
with the 258,409 included ones on the Twitter profile metadata available for everyone (account age,
follower, following, tweet and listed counts, protected and verified status), and checks whether a
valid Mastodon handle was found for them and whether that account posted during the migration
period (November to December 2022). Only aggregate counts and medians are written
(`table_excluded_vs_included.csv`); no profile-level data is exported. Inputs are the full profile
export, the final sample and the combined Mastodon timelines from the data deposit; paths are absolute.
The results are summarized in Section 2.3 of the manuscript.

    conda activate Twitter-Migration
    python r2r_excluded_researchers.py
