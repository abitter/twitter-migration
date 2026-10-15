from utils.nlp_utils import (
    remove_handles_and_urls,
    remove_newline_chars_spaces,
    clean_text,
    wrapper_remove_handles_and_urls,
    wrapper_remove_newline_chars_spaces,
)


def prep_profiles_timelines(
    twitter_timelines_df,
    mastodon_timelines_df,
    profiles_researchers_df,
    start_date_nov,
    end_date_dec,
):
    """
    Prepare twitter and mastodon profile descriptions and timelines for pre-post
    split for immediacy calculation. The goal of pre-post split is to first get
    all relevant posts of a person (twitter and/or mastodon, based on migration)
    and collect them in a list along with the profile description (twitter or
    mastodon, based on migration), so that we can compare immediacy of people
    based on their profile and posts. We want the profile descriptions and posts
    to be clean and not contain e.g. handles, urls etc, which is achieved by
    this function.
    NOTE: Some posts without text content are removed; this is only done for
    immediacy calculation, not for comparing twitter/mastodon activity or
    anything else. The rationale is that it doesn't make sense to embed empty
    strings.

    Parameters:
        twitter_timelines_df (pd.DataFrame): DataFrame containing twitter timelines.
        mastodon_timelines_df (pd.DataFrame): DataFrame containing mastodon timelines.
        profiles_researchers_df (pd.DataFrame): DataFrame containing researcher profiles.
        start_date_nov (datetime): The start date for the period of interest (Nov 1st).
        end_date_dec (datetime): The end date for the period of interest (Dec 31st).

    Returns:
        A tuple containing:
        twitter_timelines_nov_dec_df (pd.DataFrame): Cleaned twitter timelines.
        mastodon_timelines_nov_dec_df (pd.DataFrame): Cleaned mastodon timelines.
        profiles_researchers_df (pd.DataFrame): Cleaned researcher profiles.
    """

    def preprocess_twitter_timelines(twitter_timelines_df):
        """
        Clean twitter timelines: Remove handles, urls, newline chars, and spaces
        from twitter posts, and remove posts without text content. Retain only
        posts in period of interest.
        """

        # NOTE: we use all activity from the twitter timelines, not only
        # original tweets. first, we clean the text in twitter_timelines_df.

        twitter_timelines_nov_dec_df = twitter_timelines_df.copy()
        twitter_timelines_nov_dec_df["text_final"] = twitter_timelines_nov_dec_df[
            "text"
        ].parallel_apply(remove_handles_and_urls)
        twitter_timelines_nov_dec_df["text_final"] = twitter_timelines_nov_dec_df[
            "text_final"
        ].parallel_apply(remove_newline_chars_spaces)

        # remove tweets that do not have any text content
        twitter_timelines_nov_dec_df = twitter_timelines_nov_dec_df[
            twitter_timelines_nov_dec_df["text_final"].parallel_apply(len) > 0
        ]
        print(
            f"removing {len(twitter_timelines_df) - len(twitter_timelines_nov_dec_df)} tweets out of {len(twitter_timelines_df)} due to missing text content."
        )

        # remove tweets that were not created in period of interest
        cur_len_timelines = len(twitter_timelines_nov_dec_df)
        twitter_timelines_nov_dec_df = twitter_timelines_nov_dec_df.loc[
            (
                twitter_timelines_nov_dec_df.index.get_level_values("created_at")
                >= start_date_nov
            )
            & (
                twitter_timelines_nov_dec_df.index.get_level_values("created_at")
                <= end_date_dec
            )
        ]
        print(
            f"removing {cur_len_timelines - len(twitter_timelines_nov_dec_df)} tweets out of {cur_len_timelines} due to not being created in period of interest."
        )
        twitter_timelines_nov_dec_df.index.get_level_values("created_at").min()
        twitter_timelines_nov_dec_df.index.get_level_values("created_at").max()

        return twitter_timelines_nov_dec_df

    def preprocess_mastodon_timelines(mastodon_timelines_df):
        """
        Clean Mastodon timelines: Remove handles, urls, newline chars, and
        spaces from mastodon posts, and remove posts without text content.
        """

        mastodon_timelines_nov_dec_df = mastodon_timelines_df.copy()
        mastodon_timelines_nov_dec_df["text_final"] = mastodon_timelines_nov_dec_df[
            "text"
        ].parallel_apply(remove_handles_and_urls)
        mastodon_timelines_nov_dec_df["text_final"] = mastodon_timelines_nov_dec_df[
            "text_final"
        ].parallel_apply(remove_newline_chars_spaces)

        # remove toots that do not have any text content
        cur_len_mastodon_timelines = len(mastodon_timelines_nov_dec_df)
        mastodon_timelines_nov_dec_df = mastodon_timelines_nov_dec_df[
            mastodon_timelines_nov_dec_df["text"].apply(len) > 0
        ]
        print(
            f"removing {cur_len_mastodon_timelines - len(mastodon_timelines_nov_dec_df)} toots out of {cur_len_mastodon_timelines} due to missing text content."
        )

        return mastodon_timelines_nov_dec_df

    def preprocess_mastodon_profile_descriptions(profiles_researchers_df):
        """
        Clean mastodon profile descriptions, removing html tags, handles, urls,
        newline chars, and spaces
        """

        profiles_researchers_df[
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ] = profiles_researchers_df[
            "account_created_or_revitalized_nov_dec_description_combined"
        ].parallel_apply(
            clean_text
        )
        profiles_researchers_df[
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ] = profiles_researchers_df[
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ].parallel_apply(
            wrapper_remove_handles_and_urls
        )
        profiles_researchers_df[
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ] = profiles_researchers_df[
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ].parallel_apply(
            wrapper_remove_newline_chars_spaces
        )

        return profiles_researchers_df

    def preprocess_twitter_profile_descriptions(profiles_researchers_df):
        """
        Clean twitter profile descriptions, removing handles, urls, newline
        chars, and spaces
        """

        profiles_researchers_df["description_final"] = profiles_researchers_df[
            "description"
        ].parallel_apply(remove_handles_and_urls)
        profiles_researchers_df["description_final"] = profiles_researchers_df[
            "description_final"
        ].parallel_apply(remove_newline_chars_spaces)

        return profiles_researchers_df

    def flagg_valid_profile_descriptions(profiles_researchers_df):
        """
        Mark empty profiles descriptions: some profile descriptions are empty
        strings, or have just a few characters. for now, we flagg those as valid
        that are not empty so to exculde empty descriptions from the immediacy
        calculation later. But we may want to exclude short descriptions too.
        """

        # print: many non-migrated users dont have twitter profile description
        profiles_researchers_df[profiles_researchers_df["is_migrated"] == False][
            "description_final"
        ].apply(lambda x: len(x)).value_counts(dropna=False)

        # print: some migrated users dont have mastodon profile description
        profiles_researchers_df[profiles_researchers_df["is_migrated"] == True][
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ].apply(lambda x: len(x)).value_counts(dropna=False)

        # flagg valid twitter descriptions
        profiles_researchers_df["description_twitter_is_valid"] = (
            profiles_researchers_df["description_final"].apply(len) > 0
        )

        # flagg valid mastodon descriptions
        profiles_researchers_df["description_mastodon_is_valid"] = (
            profiles_researchers_df[
                "account_created_or_revitalized_nov_dec_description_combined_final"
            ]
            .fillna("")  # replace None with empty string
            .apply(len)
            > 0
        )

        return profiles_researchers_df

    twitter_timelines_nov_dec_df = preprocess_twitter_timelines(twitter_timelines_df)
    mastodon_timelines_nov_dec_df = preprocess_mastodon_timelines(mastodon_timelines_df)
    profiles_researchers_df = preprocess_mastodon_profile_descriptions(
        profiles_researchers_df
    )
    profiles_researchers_df = preprocess_twitter_profile_descriptions(
        profiles_researchers_df
    )
    profiles_researchers_df = flagg_valid_profile_descriptions(profiles_researchers_df)

    return (
        twitter_timelines_nov_dec_df,
        mastodon_timelines_nov_dec_df,
        profiles_researchers_df,
    )


def get_posts_pre_post_split(
    id,
    profiles_researchers_df,
    twitter_timelines_nov_dec_df,
    mastodon_timelines_nov_dec_df,
    start_date_nov,
    end_date_dec,
):
    """
    Get posts and profile description based on migration status of a
    user.

    For migrated users, combine all Twitter posts before migration with Mastodon
    posts after migration. For non-migrated users, use only Twitter post.
    Based on migration status, Twitter or Mastodon profile description is used
    as the first post if valid (i.e., not empty string).

    Parameters:
        id (str): The unique identifier of the researcher whose social
    media posts are to be retrieved.

    Returns:
        A tuple containing:
        - twitter_username (str): The Twitter username of the user.
        - is_migrated (int): A flag indicating whether the user has migrated
        - description (str): The profile description text vased on migration status.
        - description_is_valid (bool): A flag indicating whether the profile
          description is considered valid (non-empty).
        - description_text_combined_all (list of str): A list of all processed
          posts, potentially starting with the valid profile description.
        - text_combined_original (list of str): A list of only original posts,
          filtered to exclude retweets and reblogs.
    """

    row = profiles_researchers_df[profiles_researchers_df["id"] == id]

    # for migrated users, we use a combination of twitter and mastodon posts
    if row["is_migrated"].iloc[0] == True:
        start_date_activity_comparison = row["start_date_activity_comparison"].iloc[0]

        # all twitter posts from Nov 1st until account creation/revitalization
        timeline_twitter_all = twitter_timelines_nov_dec_df.loc[
            (id, start_date_nov):(id, start_date_activity_comparison)
        ]
        text_twitter_all = timeline_twitter_all["text_final"].tolist()

        # all mastodon posts from account creation/revitalization until Dec 31st
        mask = (
            mastodon_timelines_nov_dec_df.handle.isin(
                row["account_created_or_revitalized_nov_dec_handles"].iloc[0]
            )
            & (
                start_date_activity_comparison
                <= mastodon_timelines_nov_dec_df.created_at
            )
            & (mastodon_timelines_nov_dec_df.created_at <= end_date_dec)
        )
        timeline_mastodon_all = mastodon_timelines_nov_dec_df.loc[mask]
        text_mastodon_all = timeline_mastodon_all["text_final"].tolist()

        # combine all twitter and mastodon posts and add mastodon profile
        # description in first position if valid
        description_text_combined_all = text_twitter_all + text_mastodon_all
        description = row[
            "account_created_or_revitalized_nov_dec_description_combined_final"
        ].iloc[0]
        description_is_valid = row["description_mastodon_is_valid"].iloc[0]
        if description_is_valid == True:
            description_text_combined_all.insert(
                0,
                description,
            )

        # only original twitter posts from Nov 1st until account creation/revitalization
        # NOTE: dropping original tweets that start with "RT @": some "original"
        # tweets returned by the API are actually retweets (with Mastodon
        # account handles, likely cross-postings) that we want to remove
        timeline_twitter_original = timeline_twitter_all[
            timeline_twitter_all["is_original_tweet"] == 1
        ]
        timeline_twitter_original = timeline_twitter_original[
            ~(timeline_twitter_original["text"].str.contains("RT @"))
        ]
        text_twitter_original = timeline_twitter_original["text_final"].tolist()

        # only original mastodon posts from account creation/revitalization until Dec 31st
        mastodon_timeline_original = timeline_mastodon_all[
            timeline_mastodon_all["is_reblog"] == False
        ]
        text_mastodon_original = mastodon_timeline_original["text_final"].tolist()

        # combine all original posts
        text_combined_original = text_twitter_original + text_mastodon_original

        is_migrated = 1
        twitter_username = row["username"].iloc[0]

    # for non-migrated users, we only use twitter posts (from Nov 1st until Dec 31st)
    elif row["is_migrated"].iloc[0] == False:

        # all twitter posts from Nov 1st until Dec 31st
        timeline_twitter_all = twitter_timelines_nov_dec_df.loc[
            (id, start_date_nov):(id, end_date_dec)
        ]
        text_twitter_all = timeline_twitter_all["text_final"].tolist()

        # here, using only twitter posts for combined text
        description_text_combined_all = text_twitter_all

        # combine all twitter posts and add twitter profile description in first
        # position if valid
        description = row["description_final"].iloc[0]
        description_is_valid = row["description_twitter_is_valid"].iloc[0]
        if description_is_valid == True:
            description_text_combined_all.insert(
                0,
                description,
            )

        # only original twitter posts from Nov 1st until account creation/revitalization
        # NOTE: dropping original tweets that start with "RT @": some "original"
        # tweets returned by the API are actually retweets (with Mastodon
        # account handles, likely cross-postings) that we want to remove
        timeline_twitter_original = timeline_twitter_all[
            timeline_twitter_all["is_original_tweet"] == 1
        ]
        timeline_twitter_original = timeline_twitter_original[
            ~(timeline_twitter_original["text"].str.contains("RT @"))
        ]
        text_twitter_original = timeline_twitter_original["text_final"].tolist()

        # combine all original posts
        text_combined_original = text_twitter_original

        is_migrated = 0
        twitter_username = row["username"].iloc[0]

    return (
        twitter_username,
        is_migrated,
        description,
        description_is_valid,
        description_text_combined_all,
        text_combined_original,
    )
