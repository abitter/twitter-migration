import pandas as pd

from utils.utils import (
    get_path,
)

from utils.nlp_utils import (
    categorize_mhandles_valid_invalid,
    lower_minstance_substring,
    categorize_mhandles_known_unknown,
    is_valid_mastodon_url,
    reformat_url,
    deduplicate_mhandles,
)

from utils.data_loaders import (
    load_tprofiles_initial,
    load_opencheck_initial,
    load_academics_on_mastodon_initial,
    load_minstances_ranking,
)


# TODO: refactoring
def extract_mhandles_from_tprofiles(cfg):
    """
    Extracts and processes Mastodon handles from Twitter profiles and open lists
    retrieved from external sources (OpenCheck, Academics on Mastodon). Saves a
    JSON file containing profiles with validated and categorized Mastodon
    handles.

    1. Loads and cleans researcher profile data from Twitter.
    2. Extracts potential Mastodon handles from Twitter usernames, descriptions,
       and external datasets.
    3. Merges Mastodon handles from OpenCheck and Academics on Mastodon
       datasets, aligning Twitter and Mastodon handles.
    4. Validates and categorizes Mastodon handles as valid/invalid and
       known/unknown instances.
    5. Deduplicates and refines the handles for consistency.
    6. Saves the combined and cleaned profiles data, including Mastodon
       handles and associated disciplines.

    Args:
        cfg: Configuration object containing file paths and other parameters
        required for loading and processing data.

    Returns:
        None
    """

    # read profiles researchers data
    profiles_researchers_df = load_tprofiles_initial(cfg)

    # remove duplicates
    profiles_researchers_df.drop_duplicates(
        subset=["description", "id", "username", "description"], inplace=True
    )

    def new_col_with_potential_handles(profiles_researchers_df):
        """
        get potential handles from twitter username, name, and description, creating new col
        """

        def get_potential_handles(text):
            return [
                segment for segment in str(text).split() if 1 <= segment.count("@") <= 2
            ]

        profiles_researchers_df["potential_handles"] = profiles_researchers_df.apply(
            lambda row: get_potential_handles(
                " ".join(
                    [str(row["username"]), str(row["name"]), str(row["description"])]
                )
            ),
            axis=1,
        )
        return profiles_researchers_df

    profiles_researchers_df = new_col_with_potential_handles(profiles_researchers_df)

    def process_opencheck(profiles_researchers_df, cfg):
        """
        Add OpenCheck handles to the potential_handles column in the
        profiles_researchers_df, and create two new columns for discipline
        information and isFromOpenCheck identifier.
        """

        def load_and_clean_opencheck(cfg):

            # read data
            OpenCheck_df = load_opencheck_initial(cfg)

            # drop rows with missing values (some people did not provide a mastodon account)
            OpenCheck_df = OpenCheck_df.dropna()

            # retain only rows with two @ signs (all except one person)
            OpenCheck_df = OpenCheck_df[OpenCheck_df["mastodon"].str.count("@") == 2]

            # remove people who reported the twitter handle "@none"
            print(
                f'removing {len(OpenCheck_df[OpenCheck_df["twitter"] == "@None"])} rows with twitter handle "@None".'
            )
            OpenCheck_df = OpenCheck_df[OpenCheck_df["twitter"] != "@None"]

            return OpenCheck_df

        def group_opencheck_data(OpenCheck_df):
            """
            Group OpenCheck data by Twitter handle to then add handles to
            profiles researchers df
            """

            # group by 'twitter' while agg 'discipline', 'mastodon', and 'person' as lists
            OpenCheck_df_groupby = (
                OpenCheck_df.groupby("twitter")
                .agg({"discipline": list, "mastodon": list, "person": list})
                .reset_index()
            )

            # removing @ symbol from Twitter handles so that they are consistent with
            # handles in profiles
            OpenCheck_df_groupby["twitter"] = OpenCheck_df_groupby["twitter"].apply(
                lambda x: x.split("@")[-1]
            )

            # convert mastodon and person list to a set, de-dublicating the entries
            # (note, there may still be multiple entries for the same person)
            OpenCheck_df_groupby["mastodon"] = OpenCheck_df_groupby["mastodon"].apply(
                lambda x: list(set(x))
            )
            OpenCheck_df_groupby["person"] = OpenCheck_df_groupby["person"].apply(
                lambda x: list(set(x))
            )

            return OpenCheck_df_groupby

        def add_handles_to_profiles(profiles_researchers_df, OpenCheck_df_groupby):
            """
            Append the Mastodon handles to the potential_handles column in the
            profiles_researchers_df using a mask
            """

            # create boolean mask to select rows where the Twitter handle is in the
            # OpenCheck_df_groupby df
            mask = profiles_researchers_df["username"].isin(
                OpenCheck_df_groupby["twitter"]
            )

            # create dictionary where the keys are the Twitter usernames and the
            # values are their corresponding Mastodon handles
            username_to_mastodon = OpenCheck_df_groupby.set_index("twitter")[
                "mastodon"
            ].to_dict()

            # Use mapping to append Mastodon handles: For each row selected by the
            # mask, map the username to its corresponding Mastodon handle using the
            # username_to_mastodon dictionary and append it to the potential_handles
            # list.
            profiles_researchers_df.loc[mask, "potential_handles"] = (
                profiles_researchers_df.loc[mask, "potential_handles"]
                + profiles_researchers_df.loc[mask, "username"].map(
                    username_to_mastodon
                )
            )

            return profiles_researchers_df, mask

        def add_opencheck_info(profiles_researchers_df, OpenCheck_df_groupby, mask):
            """Add discipline information and OpenCheck identifier as new columns to
            profiles_researchers_df"""

            # create mapping dictionary
            username_to_discipline = OpenCheck_df_groupby.set_index("twitter")[
                "discipline"
            ].to_dict()

            # add discipline column
            profiles_researchers_df["discipline_OpenCheck"] = profiles_researchers_df[
                "username"
            ].map(username_to_discipline)

            # replace NaN (no discipline) with empty list
            profiles_researchers_df.loc[
                profiles_researchers_df["discipline_OpenCheck"].isna(),
                "discipline_OpenCheck",
            ] = profiles_researchers_df.loc[
                profiles_researchers_df["discipline_OpenCheck"].isna(),
                "discipline_OpenCheck",
            ].apply(
                lambda x: []
            )

            # let's also add the source of the handles (OpenCheck or Twitter profiles)
            profiles_researchers_df["isFromOpenCheck"] = 0
            profiles_researchers_df.loc[mask, "isFromOpenCheck"] = 1

            return profiles_researchers_df

        OpenCheck_df = load_and_clean_opencheck(cfg)
        OpenCheck_df_groupby = group_opencheck_data(OpenCheck_df)
        profiles_researchers_df, mask = add_handles_to_profiles(
            profiles_researchers_df, OpenCheck_df_groupby
        )
        profiles_researchers_df = add_opencheck_info(
            profiles_researchers_df, OpenCheck_df_groupby, mask
        )

        return profiles_researchers_df

    profiles_researchers_df = process_opencheck(profiles_researchers_df, cfg)

    def process_academics_on_mastdon(profiles_researchers_df, cfg):
        """
        Add Academics on Mastodon handles to the potential_handles column in the
        profiles_researchers_df, and create two new columns for discipline
        information and isFromAcademics identifier.
        """

        # read data
        Academics_df = load_academics_on_mastodon_initial(cfg)

        # exclude lists that have protected TOS (we have not collected the users from
        # these lists, they are just placeholders in the df)
        Academics_df = Academics_df[Academics_df["protected_tos"] == 0]

        # remove the people who did not provide a twitter handle
        Academics_df = Academics_df.dropna().reset_index(drop=True)

        ## preprocess mastodon handles

        # preserve only rows that have 1-2 @ symbols in the mastodon handle
        Academics_df = Academics_df[
            Academics_df["mastodon_handle"].str.count("@").between(1, 2)
        ]

        ## preprocess twitter handles

        Academics_df = Academics_df[
            Academics_df["twitter_handle"].str.count("@").between(0, 1)
        ]

        # rescue twitter handles that are in url-format
        mask = (Academics_df.twitter_handle.str.count("@") == 0) & (
            Academics_df.twitter_handle.str.startswith("https://")
        )
        Academics_df.loc[mask, "twitter_handle"] = Academics_df.loc[
            mask, "twitter_handle"
        ].apply(lambda x: x.split("/")[-1])

        # remove the @ symbol from the twitter handles that are reported with a
        # beginning @ so that it is consistent with the profiles.
        mask = Academics_df.twitter_handle.fillna("").str.startswith("@")
        Academics_df.loc[mask, "twitter_handle"] = Academics_df.loc[
            mask, "twitter_handle"
        ].apply(lambda x: x[1:])

        # group by 'twitter' while agg 'discipline' and 'mastodon_handle' as lists
        Academics_df_groupby = (
            Academics_df.groupby("twitter_handle")
            .agg({"discipline": list, "mastodon_handle": list})
            .reset_index()
        )

        # convert mastodon list to a set, de-dublicating the entries
        # (note, there may still be multiple entries for the same person)
        Academics_df_groupby["mastodon_handle"] = Academics_df_groupby[
            "mastodon_handle"
        ].apply(lambda x: list(set(x)))

        # create boolean mask to select rows where the Twitter handle is in the Academics_df_complete df
        mask = profiles_researchers_df["username"].isin(
            Academics_df_groupby["twitter_handle"]
        )

        # Create dictionary where the keys are the Twitter usernames and the values are their corresponding Mastodon handles
        username_to_mastodon = Academics_df_groupby.set_index("twitter_handle")[
            "mastodon_handle"
        ].to_dict()

        # Use mapping to append Mastodon handles: For each row selected by the mask,
        # map the username to its corresponding Mastodon handle using the
        # username_to_mastodon dictionary and append it to the potential_handles list.
        profiles_researchers_df.loc[mask, "potential_handles"] = (
            profiles_researchers_df.loc[mask, "potential_handles"]
            + profiles_researchers_df.loc[mask, "username"].map(username_to_mastodon)
        )

        ## add discipline information

        username_to_discipline = Academics_df_groupby.set_index("twitter_handle")[
            "discipline"
        ].to_dict()

        # add discipline column
        profiles_researchers_df["discipline_Academics"] = profiles_researchers_df[
            "username"
        ].map(username_to_discipline)

        # replace NaN (no discipline) with empty list
        profiles_researchers_df.loc[
            profiles_researchers_df["discipline_Academics"].isna(),
            "discipline_Academics",
        ] = profiles_researchers_df.loc[
            profiles_researchers_df["discipline_Academics"].isna(),
            "discipline_Academics",
        ].apply(
            lambda x: []
        )

        # let's also add the source of the handles (OpenCheck or Twitter profiles)
        profiles_researchers_df["isFromAcademics"] = 0
        profiles_researchers_df.loc[mask, "isFromAcademics"] = 1

        return profiles_researchers_df

    profiles_researchers_df = process_academics_on_mastdon(profiles_researchers_df, cfg)

    def process_potential_handles(profiles_researchers_df):
        """
        split all collected potential handles into valid/invalid, and then the
        valid ones into handles from known/unknown mastodon instances, creating
        new columns for each category.
        """

        ## split potential handles: valid/invalid

        # splitting potential handles column into valid and invalid handles
        (
            profiles_researchers_df["handles_valid"],
            profiles_researchers_df["handles_invalid"],
        ) = zip(
            *profiles_researchers_df["potential_handles"].apply(
                categorize_mhandles_valid_invalid
            )
        )

        ## split valid handles: known/unknown instances

        # read known instances
        path_known_instances = get_path(
            cfg, "raw", "mastodon", "known_instances", "known_instances.csv"
        )
        known_instances_df = pd.read_csv(path_known_instances)

        # Convert the known instances to a set for fast lookup
        known_instances_set = {
            instance for instance in known_instances_df["instance_name"]
        }

        # splitting valid handles into handles containing known/unknown instances
        (
            profiles_researchers_df["handles_valid_known"],
            profiles_researchers_df["handles_valid_unknown"],
        ) = zip(
            *profiles_researchers_df["handles_valid"].apply(
                lambda handle: categorize_mhandles_known_unknown(
                    handle, known_instances_set
                )
            )
        )

        # convert instance substring to lowercase (known instances are lowercase, and we
        # dont want to have different versions of the same instance when counting them
        # in the end)
        profiles_researchers_df["handles_valid_known"] = profiles_researchers_df[
            "handles_valid_known"
        ].apply(lambda x: [lower_minstance_substring(x) for x in x])

        profiles_researchers_df["handles_valid_unknown"] = profiles_researchers_df[
            "handles_valid_unknown"
        ].apply(lambda x: [lower_minstance_substring(x) for x in x])

        # add missing @ symbol at the beginning of valid known handle
        profiles_researchers_df["handles_valid_known"] = profiles_researchers_df[
            "handles_valid_known"
        ].apply(lambda x: ["@" + handle for handle in x])

        ## rescue people who used URLs instead of handles

        # new column with valid mastodon urls containing knwon instance
        profiles_researchers_df["urls_valid_known"] = profiles_researchers_df[
            "handles_invalid"
        ].apply(
            lambda x: [x for x in x if is_valid_mastodon_url(x, known_instances_set)]
        )

        # reformat urls to match handle format
        profiles_researchers_df["urls_valid_known_handle"] = profiles_researchers_df[
            "urls_valid_known"
        ].apply(lambda x: [reformat_url(url) for url in x])

        ## postprocessing profiles

        # combine handles and handles extracted from urls
        profiles_researchers_df["handles_valid_known_combined"] = (
            profiles_researchers_df["handles_valid_known"]
            + profiles_researchers_df["urls_valid_known_handle"]
        )

        # apply new function to remove duplicates in mastodon handles
        profiles_researchers_df["handles_valid_known_combined"] = (
            profiles_researchers_df["handles_valid_known_combined"].apply(
                deduplicate_mhandles
            )
        )

        return profiles_researchers_df

    profiles_researchers_df = process_potential_handles(profiles_researchers_df)

    def create_top_minstances_df(profiles_researchers_df):
        """
        Create df with mastodon instances covering the top 95% of users. Other
        instances are dropped as we can not collect data from all of them.
        """

        # flatten the lists of lists in handles_valid_known_combined for plotting
        instances = [
            handle.split("@")[-1]
            for sublist in profiles_researchers_df["handles_valid_known_combined"]
            for handle in sublist
        ]

        # get the counts of each instance
        instance_counts = pd.Series(instances).value_counts()

        # convert the series into a dataframe
        instance_df = instance_counts.reset_index()

        # rename the columns
        instance_df.columns = ["instance", "number_of_users"]

        # new column showing the cumulative percentage of users
        instance_df["cumulative_percentage"] = (
            instance_df["number_of_users"].cumsum()
            / instance_df["number_of_users"].sum()
        )

        # drop rows where the cumulative percentage is above 0.95
        instance_df = instance_df[instance_df["cumulative_percentage"] <= 0.95]

        return instance_df

    instance_df = create_top_minstances_df(profiles_researchers_df)

    def check_minstances_manual_eval(instance_df):
        """
        Check how many instances were already collected.

        This part is based on a notebook where we already ranked instances,
        manually checked TOS and started collecting account credentials for the
        top 95% of instances. After making some cleaning/refactoring changes, we
        now double-check that the new ranking is in line with the old one, i.e.,
        that all instances in our new ranking are contained in the file with
        manual evaluations.
        """

        # load the old instances ranking file with checked TOS and account credentials
        evaluated_df = load_minstances_ranking(cfg)

        # drop all rows in old ranking that are not within the 95% of instances
        # (+ within 10 additional instances that were not covered in the very
        # first round)
        evaluated_df.dropna(subset=["email", "comments"], how="all", inplace=True)

        # sanity check that all instances in the new ranking are covered in the
        # old ranking
        new_not_in_old = instance_df[
            ~instance_df.instance.isin(evaluated_df["instance"])
        ]
        if not new_not_in_old.empty:
            raise ValueError(
                f"Sanity check failed: The following instances in the new ranking are not in the evaluated set:\n{new_not_in_old}"
            )

    check_minstances_manual_eval(instance_df)
    # --> all 122 instances in the new 95% ranking have now been evaluated and
    # are contained in the evaluation file - ready to be used for scraping; only
    # two extra instances in the old evaluation file are not in the new ranking
    # anymore (i.e. not in the new 95%), so we have two additional instances.

    # ==================================
    # save profiles with handles
    # ==================================

    # save as json
    path_profiles_researchers = get_path(
        cfg,
        "processed",
        "twitter",
        "extract_handles",
        # "profiles_researchers_combined_handles.json",
        "profiles_researchers_combined_handles_updated.json",  # new deduplication
    )
    profiles_researchers_df.to_json(
        path_profiles_researchers, orient="records", lines=True
    )
