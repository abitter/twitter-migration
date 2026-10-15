import sys
import pandas as pd
from tqdm import tqdm

from utils.utils import (
    find_config,
    load_config,
    get_path,
    check_json_dtypes,
    check_df_dtypes,
    unnest_column,
)


def concat_json_rds_tweets(cfg):

    #######################
    # Profiles researchers
    #######################

    # Profiles are used to remove timelines for whom we do not have profile information

    # get path
    path_profiles = get_path(
        cfg, "processed", "twitter", "setup", "profiles_researchers_combined.json"
    )

    # sanity check: all ids in json file should be strings
    check_json_dtypes(
        path_profiles,
        fields_to_check=[
            "id",
            # "pinned_tweet_id", # this field does not seem to exist in every json file
        ],
    )

    # read json file into pandas dataframe, define correct dtypes
    # note: without specifying dtype, the id column is falsely represented as int64
    profiles_df = pd.read_json(
        path_profiles,
        orient="records",
        lines=True,
        dtype={"id": str},
    )

    # sanity check: all ids in pandas dataframe should be strings
    check_df_dtypes(profiles_df, columns_to_check=["id"])

    #######################
    # RDS timelines
    #######################

    # get path
    path_timelines_rds = get_path(
        cfg, "processed", "twitter", "setup", "timelines_rds_combined.json"
    )

    # sanity check: all ids in json file should be strings
    check_json_dtypes(
        path_timelines_rds,
        fields_to_check=[
            "id",
            "author_id",
            "conversation_id",
            # "pinned_tweet_id", # this field does not seem to exist in every json file
            # "in_reply_to_user_id", # not a string, but we dont need it anyway
        ],
    )

    # load data chunk by chunk
    # NOTE: this updated code specifically sets dtype string for IDs and moves normalization out of
    # loop, as this caused issues in the past
    timelines_rds_df = pd.DataFrame()
    for chunk in tqdm(
        pd.read_json(
            path_timelines_rds,
            orient="records",
            lines=True,
            chunksize=100000,
            dtype={
                "author_id": str,
                "id": str,
                "conversation_id": str,
            },
        )
    ):
        # retain only columns that are needed for now
        # (need to bring the df in same format as the json df)
        chunk = chunk[
            [
                # "possibly_sensitive",
                "public_metrics",
                "lang",
                "text",
                "entities",
                "created_at",
                "referenced_tweets",
                "author_id",
                "id",
                "edit_history_tweet_ids",
                "conversation_id",
                # "context_annotations",
                # "attachments",
                # "geo",
                # "withheld",
                "in_reply_to_user_id",
            ]
        ]
        # concat chunk to timelines_rds_df, reset index
        timelines_rds_df = pd.concat([timelines_rds_df, chunk], ignore_index=True)

    # unnest columns
    nested_columns = ["public_metrics", "entities"]  # 'referenced_tweets'
    unnested_columns = pd.concat(
        [unnest_column(timelines_rds_df, col) for col in nested_columns], axis=1
    )
    if not timelines_rds_df.index.is_unique:
        raise ValueError("Index in timelines_rds_df is not unique.")
    if not unnested_columns.index.equals(timelines_rds_df.index):
        raise ValueError("Index in unnested_columns is not identical to df.")
    timelines_rds_df = timelines_rds_df.join(unnested_columns)
    timelines_rds_df = timelines_rds_df.drop(nested_columns, axis=1)

    # sanity check: all ids in pandas dataframe should be strings
    check_df_dtypes(
        timelines_rds_df, columns_to_check=["id", "author_id", "conversation_id"]
    )

    # add column type to indicate source of data
    timelines_rds_df["type"] = "rds"

    # retaining only tweets by people in profiles_researchers_df
    timelines_rds_df = timelines_rds_df[
        timelines_rds_df["author_id"].isin(profiles_df["id"])
    ].reset_index(drop=True)

    # remove duplicates in place, if any
    timelines_rds_df.drop_duplicates(
        subset=["conversation_id", "id", "author_id", "created_at", "text"],
        inplace=True,
        ignore_index=True,
    )

    # how many profiles are found in timelines?
    print(
        "Profile IDs (int) found in timelines_rds_df:",
        profiles_df["id"].isin(timelines_rds_df["author_id"]).value_counts(),
    )

    #######################
    # JSON timelines
    #######################

    # get path
    path_timelines_json = get_path(
        cfg, "processed", "twitter", "setup", "timelines_json_combined.json"
    )

    # load data chunk by chunk
    timelines_json_df = pd.DataFrame()
    for chunk in tqdm(
        pd.read_json(
            path_timelines_json,
            orient="records",
            lines=True,
            chunksize=100000,
            dtype={
                "author_id": str,
                "id": str,
                "conversation_id": str,
            },
        )
    ):
        # retain only the columns that are needed for now
        # (need to bring the df in same format as the rds df)
        chunk = chunk[
            [
                "conversation_id",
                "referenced_tweets",
                "created_at",
                "lang",
                "author_id",
                "text",
                "edit_history_tweet_ids",
                "id",
                "public_metrics.retweet_count",
                "public_metrics.reply_count",
                "public_metrics.like_count",
                "public_metrics.quote_count",
                "public_metrics.impression_count",
                "entities.mentions",
                "entities.annotations",
                "entities.hashtags",
                "in_reply_to_user_id",
                "entities.urls",
                "source",
                # "geo.coordinates.type",
                # "geo.coordinates.coordinates",
                # "withheld.scope",
            ]
        ]
        timelines_json_df = pd.concat([timelines_json_df, chunk], ignore_index=True)

    # sanity check: all ids in json file should be strings
    check_json_dtypes(
        path_timelines_json,
        fields_to_check=[
            "id",
            "author_id",
            "conversation_id",
        ],
        error=False,
    )

    # remove one row that contains "None" as author_id
    timelines_json_df = timelines_json_df[
        timelines_json_df.author_id.apply(lambda x: x != "None")
    ].reset_index(drop=True)

    # sanity check: all ids in pandas dataframe should be strings
    check_df_dtypes(
        timelines_json_df,
        columns_to_check=["id", "author_id", "conversation_id"],
        error=False,
    )

    # add column type to indicate source of data
    timelines_json_df["type"] = "json"

    # retaining only data_ files with IDs found in profiles_researchers_df (users_
    # files are removed for now - this could already be done in bind_json_tweets.py)
    timelines_json_df = timelines_json_df[
        (timelines_json_df["source"] == "data")
        & (timelines_json_df["author_id"].isin(profiles_df["id"]))
    ].reset_index(drop=True)

    # remove duplicates in place (note, duplicates should be removed after dropping
    # users_; dont want to remove duplicates between data_ and users_ from the good
    # data_ files)
    timelines_json_df.drop_duplicates(
        subset=["conversation_id", "id", "author_id", "created_at", "text"],
        inplace=True,
        ignore_index=True,
    )

    # how many profiles are found in timelines?
    print(
        "Profile IDs (int) found in timelines_json_df:",
        profiles_df["id"].isin(timelines_json_df["author_id"]).value_counts(),
    )

    #######################
    # Concat
    #######################

    # Concat the two dataframes
    timelines_concat = pd.concat(
        [timelines_rds_df, timelines_json_df], ignore_index=True
    )

    timelines_concat.drop_duplicates(
        subset=["conversation_id", "id", "author_id", "created_at", "text"],
        inplace=True,
        ignore_index=True,
    )

    timelines_concat.to_json(
        get_path(cfg, "processed", "twitter", "setup", "timelines_combined_final.json"),
        orient="records",
        lines=True,
    )
