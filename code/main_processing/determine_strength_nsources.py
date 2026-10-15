from utils.data_loaders import load_influencer_tprofiles_main
import numpy as np
import pandas as pd


def calculate_strength_nsources(cfg, profiles_researchers_df):
    """
    Calculate strength and number of sources for each researcher, looping
    through profiles_researchers_df.

    Parameters:
        profiles_researchers_df (pd.DataFrame): DataFrame containing researcher
        profiles.

    Returns:
        profiles_researchers_df (pd.DataFrame): DataFrame containing researcher
        profiles with added columns for strength and number of sources.
    """

    def calculate_strength_nsources_row(row, influencer_profiles_weighted_df):
        """
        Calculate strength and number of sources for a given user ID.
        """

        followed_influencers_IDs = row["followed_influencer_ids_remaining"]

        # if no followed influencers, return nan
        if not followed_influencers_IDs:
            return pd.Series(
                {
                    "SI_S": np.nan,
                    "SI_N": np.nan,
                }
            )

        # get influence scores of followed influencers
        filtered_df = influencer_profiles_weighted_df[
            influencer_profiles_weighted_df["id"].isin(followed_influencers_IDs)
        ]
        followed_influencers_scores = filtered_df["influence_score_20-80_weighted"]

        # calculate strength
        strength = followed_influencers_scores.mean()

        # calculate number of sources (aquivalent to len of followed influencer_ids)
        number_of_sources = len(followed_influencers_scores)

        return pd.Series(
            {
                "SI_S": strength,
                "SI_N": number_of_sources,
            }
        )

    influencer_profiles_weighted_df = load_influencer_tprofiles_main(cfg)

    # apply function, calculating strength and number of sources for each researcher
    profiles_researchers_df[
        [
            "SI_S",
            "SI_N",
        ]
    ] = profiles_researchers_df.parallel_apply(
        calculate_strength_nsources_row, args=(influencer_profiles_weighted_df,), axis=1
    )

    return profiles_researchers_df


def extract_influence_scores(cfg, profiles_researchers_df):
    """
    Extract influence scores of followed influencers for each researcher.

    Parameters:
        profiles_researchers_df (pd.DataFrame): DataFrame containing researcher profiles.

    Returns:
        profiles_researchers_df (pd.DataFrame): DataFrame containing researcher profiles
        with added column 'SI_S_raw'.
    """

    influencer_profiles_weighted_df = load_influencer_tprofiles_main(cfg)

    def extract_influence_scores_row(row, influencer_profiles_weighted_df):
        followed_influencers_IDs = row["followed_influencer_ids_remaining"]

        # If no followed influencers, return empty list
        if not followed_influencers_IDs:
            return []

        # Get influence scores of followed influencers
        filtered_df = influencer_profiles_weighted_df[
            influencer_profiles_weighted_df["id"].isin(followed_influencers_IDs)
        ]
        followed_influencers_scores = filtered_df[
            "influence_score_20-80_weighted"
        ].tolist()

        return followed_influencers_scores

    # Apply function to extract influence scores and store in 'SI_S_raw' column
    profiles_researchers_df["SI_S_raw"] = profiles_researchers_df.parallel_apply(
        extract_influence_scores_row, args=(influencer_profiles_weighted_df,), axis=1
    )

    return profiles_researchers_df
