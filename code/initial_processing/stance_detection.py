import pandas as pd
from pathlib import Path
from utils.utils import load_config, get_path

from utils.data_loaders import (
    load_top100_eval_merged_evaluated_v2,
    load_influencer_profiles_v2_initial,
)


# TODO: refactoring
def manual_stance_detection(cfg):
    """
    This function weights the influence scores of influencers posting about
    twitter migration using manual evaluations of their posts, in order to
    account for anti-migration influencers (weight -1 vs. 1). Saves the updated
    influencer profiles with weighted influence scores as a JSON file.

    Args: cfg (dict): Configuration dictionary containing paths and parameters
    for loading and saving data.

    Returns: None.
    """

    ## get stance of top 100 influencers based on manual eval

    # load the manual evaluation of the top 100 influencers
    top100_eval_merged_evaluated_df = load_top100_eval_merged_evaluated_v2(cfg)

    # transform the manual eval stating the proportion of against migration posts
    # out of the top X tweets per influencer to binary: if person has at least one
    # post against migration, then the person is against migration.
    top100_eval_merged_evaluated_df["is_against_migration_manual"] = (
        top100_eval_merged_evaluated_df[
            "notes_influencer_prop_against_migration"
        ].apply(lambda x: 0 if (x[0]) == "0" else 1)
    )

    # how many people are against migration based on the manual eval?
    top100_eval_merged_evaluated_df["is_against_migration_manual"].value_counts()
    # -> 10

    # new column for weighting influence score with stance: -1 for against
    # migration, 1 for not against migration
    top100_eval_merged_evaluated_df["influence_weight_manual"] = (
        top100_eval_merged_evaluated_df["is_against_migration_manual"].replace(
            {1: -1, 0: 1}
        )
    )

    ## for each influencer: calculate binary-weighted influence score

    # now, we can read the influencer profiles and weight the influence scores using
    # the stance is against migration (*-1 or 1). the influencers 101-end all get
    # the default weight of 1, "not against migration"

    # load influencer profiles
    influencer_profiles_df = load_influencer_profiles_v2_initial(cfg)

    # sanity check that usernames in top 100 manual eval are in influencer profiles
    # (12 non-researchers/influencers already removed, so 88 matches)
    top100_eval_merged_evaluated_df.username.isin(
        influencer_profiles_df.username
    ).value_counts()

    # merging the 'influence_weight_manual' column from
    # top100_eval_merged_evaluated_df into influencer_profiles_df based on common
    # username column
    influencer_profiles_df = influencer_profiles_df.merge(
        top100_eval_merged_evaluated_df[["username", "influence_weight_manual"]],
        on="username",
        how="left",
    )
    influencer_profiles_df["influence_weight_manual"] = influencer_profiles_df[
        "influence_weight_manual"
    ].fillna(1)

    # use overall stance per influencer to weight the influence score with -1 or 1
    influencer_profiles_df["influence_score_20-80_weighted"] = (
        influencer_profiles_df["influence_score_20-80"]
        * influencer_profiles_df["influence_weight_manual"]
    )

    # there are now 10 influence scores below 0, as expected.
    (influencer_profiles_df["influence_score_20-80_weighted"] < 0).value_counts()

    # save influencer profiles with weighted influence score
    path_influencer_profiles_weighted = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "influencer_profiles_v2_weighted.json",
    )
    influencer_profiles_df.to_json(
        path_influencer_profiles_weighted, orient="records", lines=True
    )
