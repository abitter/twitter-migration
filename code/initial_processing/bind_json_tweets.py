import os
import json
import pandas as pd
from tqdm import tqdm

from utils.utils import (
    get_path,
)


def bind_json_tweets(cfg, return_data=False):
    """
    Bind JSON files containing tweets and save the result to disk

    Based on Mastodon_temp/bind_json_tweets_v3.ipynb
    We may want to remove the users_ files entirely Possibly remove error handling
    and printing functionality that was used for exploration

    NOTE: pd.json_normalize resets the index (bug), which can lead to issues when
    concatenating horizontally based on the index, but here we concat vertically.
    """

    # path to the directory containing JSON files
    data_path = get_path(cfg, "raw", "twitter", "timelines mongeon json/data", "")

    # output format for the combined data ("feather", "json", or "parquet").
    out_format = "json"

    # output path for the combined data file
    out_path = get_path(
        cfg, "processed", "twitter", "setup", "timelines_json_combined.json"
    )

    # list of filename patterns to include in the concatenation process.
    concat = ["data_*json", "users_*json"]

    def bind_subset(data_path, file_prefix, batch_size=20000):
        """
        Process and bind subset of JSON files based on the specified file prefix.

        :param data_path: The path to the directory containing JSON files.
        :param file_prefix: The prefix of the files to process and concatenate ("data_" or "users_").
        :return: A DataFrame containing the concatenated data.
        """

        file_list = [
            os.path.join(data_path, file)
            for file in os.listdir(data_path)
            if file.startswith(file_prefix)
        ]
        # print how many files we have
        print(
            f"Found {len(file_list)} files with prefix {file_prefix} in {data_path}"
        )  # TEMP
        concatenated_dfs = pd.DataFrame()
        concatenated_list = []
        error_files = pd.DataFrame(
            columns=["file", "error"]
        )  # Initialize an empty DataFrame to store all error files

        for i, file in tqdm(enumerate(file_list)):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                if file_prefix == "data_":
                    # unpack nested columns
                    df_normalized = pd.json_normalize(data)
                    df_normalized["source"] = (
                        "data"  # TEMP: Add a column to indicate the source of the data
                    )
                elif file_prefix == "users_":
                    # unpack nested columns, here from "tweets" column
                    df_normalized = pd.json_normalize(data["tweets"])
                    df_normalized["source"] = (
                        "users"  # TEMP: Add a column to indicate the source of the data
                    )
                # append current df to list of dfs for fast processing
                concatenated_list.append(df_normalized)
                # to not overload memory: every batch_size iterations, concat
                # all dfs in list, then concat with pandas df, and erase list
                if i % batch_size == 0 or i == len(file_list) - 1:
                    concatenated_list_df = pd.concat(
                        concatenated_list, ignore_index=True, copy=False
                    )
                    concatenated_dfs = pd.concat(
                        [concatenated_dfs, concatenated_list_df],
                        ignore_index=True,
                        copy=False,
                    )
                    concatenated_list = []
                    concatenated_list_df = None
            except Exception as e:
                error_df = pd.DataFrame({"file": [file], "error": [str(e)]})
                error_files = pd.concat([error_files, error_df], ignore_index=True)

        # drop duplicates
        concatenated_dfs.drop_duplicates(
            subset=["conversation_id", "id", "author_id", "created_at", "text"],
            inplace=True,
        )
        # drop columns that we don't need
        concatenated_dfs = concatenated_dfs.drop(
            columns=[
                "withheld.copyright",
                "withheld.country_codes",
                "geo.place_id",
                "attachments.poll_ids",
                "entities.cashtags",
                "attachments.media_keys",
                "possibly_sensitive",
                "context_annotations",
            ]
        )
        return concatenated_dfs, error_files

    def save_dataframe(df, out_format, out_path):
        """
        Save the given DataFrame to a file in the specified format.

        :param df: The DataFrame to save.
        :param out_format: The output format for the DataFrame ("feather", "json", or "parquet").
        :param out_path: The output path for the combined data file.
        """

        format_to_function = {
            "feather": lambda: df.to_feather(out_path),
            "json": lambda: df.to_json(out_path, orient="records", lines=True),
            "parquet": lambda: df.to_parquet(
                out_path, engine="pyarrow", compression="snappy"
            ),
        }
        format_to_function[out_format]()

    concatenated_dfs = None
    error_files = pd.DataFrame(
        columns=["file", "error"]
    )  # Initialize an empty DataFrame to store all error files

    if "data_*json" in concat:
        concatenated_dfs, error_files_data = bind_subset(data_path, "data_")
        error_files = pd.concat(
            [error_files, error_files_data]
        )  # Add the error files from the "data_" subset
        # print length of data df
        print(f"Data df has {len(concatenated_dfs)} rows")
        # print number of unique users
        print(f"Data df has {len(concatenated_dfs['author_id'].unique())} unique users")
        # print the number of error files
        print(f"Found {len(error_files_data)} error files (not included in Data df)")

    if "users_*json" in concat:
        users_dfs, error_files_users = bind_subset(data_path, "users_")
        # print length of users df
        print(f"Users df has {len(users_dfs)} rows")
        # print number of unique users
        print(f"Users df has {len(users_dfs['author_id'].unique())} unique users")
        # print the number of error files
        print(f"Found {len(error_files_users)} error files (not included in Users df)")
        # concat data and users dfs at the end; this could be optimized and done earlier
        if concatenated_dfs is not None:
            concatenated_dfs = pd.concat(
                [concatenated_dfs, users_dfs], ignore_index=True, copy=False
            )
            error_files = pd.concat(
                [error_files, error_files_users]
            )  # Add the error files from the "users_" subset
        else:
            concatenated_dfs = users_dfs

    # print length of final df
    print(f"Final df has {len(concatenated_dfs)} rows")
    # print number of unique users
    print(f"Final df has {len(concatenated_dfs['author_id'].unique())} unique users")
    # Save final df to file
    save_dataframe(concatenated_dfs, out_format, out_path)
    # Save the error files to a CSV file
    error_files.to_csv(
        os.path.join(
            os.path.dirname(out_path), "timelines_json_combined_errorfiles.csv"
        ),
        index=False,
    )

    # post-hoc sanity check: index is unique and monotonically increasing
    if not concatenated_dfs.index.is_unique:
        raise ValueError("Index is not unique")
    if not concatenated_dfs.index.is_monotonic_increasing:
        raise ValueError("Index is not monotonically increasing")

    # return concatenated data and error files if requested
    if return_data:
        return concatenated_dfs, error_files
