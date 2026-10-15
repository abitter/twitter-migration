import jsons
from datetime import datetime
import pandas as pd
import numpy as np


def preprocess_ttimelines_main(
    profiles_researchers_df, twitter_timelines_df, common_timezone
):
    """
    This function preprocesses the twitter timelines DataFrame, applying
    multiindex and sorting for fast filtering (as otherwise filtering is very
    slow due to the large size of the dataframe).

    Parameters:
    - profiles_researchers_df (pd.DataFrame): The profiles_researchers DataFrame.
    - twitter_timelines_df (pd.DataFrame): The twitter timelines DataFrame.
    - common_timezone (str): The common timezone for all dates.

    Returns:
    - twitter_timelines_df (pd.DataFrame): The preprocessed twitter timelines
    DataFrame.
    """

    # add timezone info: localize to UTC and convert to common_timezone
    twitter_timelines_df["created_at"] = (
        twitter_timelines_df["created_at"]
        .dt.tz_localize("UTC")
        .dt.tz_convert(common_timezone)
    )

    # sanity check that start_date_activity_comparison is a datetime object
    if (
        not profiles_researchers_df["start_date_activity_comparison"]
        .apply(lambda x: isinstance(x, (datetime, pd.Timestamp)))
        .all()
    ):
        raise ValueError("start_date_activity_comparison is not a datetime object.")

    # new column coding original/non-original tweets
    twitter_timelines_df["is_original_tweet"] = (
        twitter_timelines_df["referenced_tweets"] == {}
    ).astype(int)

    # multi-indexing and sorting df: by setting a multi-index on author_id and
    # created_at and then sorting it, the DataFrame is organized hierarchically.
    # specifically, entries are first organized by author_id, with all records for a
    # specific author adjacent to each other. Within each author's block of records,
    # entries are further ordered chronologically by created_at. This hierarchical
    # organization of the DataFrame facilitates more efficient data retrieval and
    # slicing operations, as entries related to a specific author can be quickly
    # accessed and are guaranteed to be in chronological order.
    twitter_timelines_df.set_index(["author_id", "created_at"], inplace=True)
    twitter_timelines_df.sort_index(inplace=True)
    if not twitter_timelines_df.index.is_monotonic_increasing:
        raise ValueError("The index is not increasing.")

    return twitter_timelines_df
