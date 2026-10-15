from utils.data_loaders import (
    load_influencer_tprofiles_main,
)


def remove_tprofiles_missing_ttimeline(
    cfg, profiles_researchers_df, twitter_timelines_df
):
    """
    This function removes people from profiles_researchers_df who do not have
    a twitter timeline because we can not calculate activity for them. Note that
    we do not remove influencers without twitter timelines for now, as they can
    be used for social impact calculation.

    Creating new columns is_influencer and is_missing_tTimeline in profiles
    researchers

    Parameters:
        cfg: config
        profiles_researchers_df: profiles researchers dataframe
        twitter_timelines_df: twitter timelines dataframe

    Returns:
        profiles_researchers_df with new columns
    """

    # load influencer profiles
    influencer_profiles_weighted_df = load_influencer_tprofiles_main(cfg)

    # new column in profiles researchers coding whether a person is an influencer or
    # not
    profiles_researchers_df["is_influencer"] = 0
    profiles_researchers_df.loc[
        profiles_researchers_df.id.isin(influencer_profiles_weighted_df.id),
        "is_influencer",
    ] = 1

    # new column in profiles researchers coding whether twitter timeline is missing or not
    profiles_researchers_df["is_missing_tTimeline"] = (
        ~profiles_researchers_df.id.isin(twitter_timelines_df.author_id)
    ).astype(int)

    # remove profiles with missing twitter timelines, but not those of influencers
    initial_profile_count = len(profiles_researchers_df)
    influencer_without_tTimeline_count = (
        (profiles_researchers_df.is_missing_tTimeline == 1)
        & (profiles_researchers_df.is_influencer == 1)
    ).sum()
    profiles_researchers_df = profiles_researchers_df[
        (profiles_researchers_df.is_missing_tTimeline == 0)
        | (profiles_researchers_df.is_influencer == 1)
    ].reset_index(drop=True)
    final_count = len(profiles_researchers_df)
    removed_profiles_count = initial_profile_count - final_count
    print(
        f"out of {initial_profile_count} profiles, {removed_profiles_count} were removed for not having twitter timeline."
    )
    print(
        f"note, did not remove {influencer_without_tTimeline_count} influencers without twitter timeline."
    )

    return profiles_researchers_df


def remove_tprofiles_missing_mtimeline(profiles_researchers_df):
    """
    This function removes people from profiles_researchers_df who do not have
    a mastodon timeline because we cannot calculate activity for them. Note that
    we do not remove influencers without mastodon timelines for now, as they can
    be used for social impact calculation.

    Creating new column is_missing_mTimeline in profiles researchers.

    Parameters:
        profiles_researchers_df: profiles researchers dataframe

    Returns:
        profiles_researchers_df with new column
    """

    # sanity check: among people with multiple mastodon handles from Nov-Dec,
    # there is noone with missing timeline
    profiles_researchers_df_nov_dec_mult_handles = profiles_researchers_df[
        profiles_researchers_df["account_created_or_revitalized_nov_dec"].apply(
            lambda x: len(x) > 1
        )
    ]
    mult_handles_is_missing_timeline = (
        profiles_researchers_df_nov_dec_mult_handles.mastodon_timeline_info.apply(
            lambda x: any([elem["is_missing_timeline"] == 1 for elem in x])
        )
    )
    assert (
        not mult_handles_is_missing_timeline.any()
    ), "expected no profiles with missing mtimelines among those with multiple handles from Nov-Dec"

    # given that there is noone with more than one handle AND at least one
    # missing timeline, we can safely remove people with missing mastodon
    # timeline(s). But we want to retain influencers with missing timelines for
    # the social impact calculation.

    # mask for people with missing mastodon timeline
    missing_timelines_mask = profiles_researchers_df["mastodon_timeline_info"].apply(
        lambda x: any([elem["is_missing_timeline"] == 1 for elem in x])
    )

    # new column in profiles researchers coding whether mastodon timeline is missing or not
    profiles_researchers_df["is_missing_mTimeline"] = missing_timelines_mask.astype(int)

    # mask for influencers
    is_influencer_mask = profiles_researchers_df["is_influencer"] == 1

    # count influencers without mastodon timelines
    influencers_with_missing_mtimeline_count = (
        missing_timelines_mask & is_influencer_mask
    ).sum()

    # count profiles before removal
    initial_profile_count = len(profiles_researchers_df)

    # remove profiles with missing mastodon timelines, but not those of influencers
    profiles_researchers_df = profiles_researchers_df[
        ~missing_timelines_mask | is_influencer_mask
    ].reset_index(drop=True)
    final_profile_count = len(profiles_researchers_df)
    removed_profiles_count = initial_profile_count - final_profile_count
    print(
        f"Out of {initial_profile_count} profiles, {removed_profiles_count} profiles were removed due to missing Mastodon timeline(s)."
    )
    print(
        f"Note: {influencers_with_missing_mtimeline_count} influencers with missing Mastodon timeline(s) were not removed."
    )

    return profiles_researchers_df


def remove_tprofiles_mbot_accounts(profiles_researchers_df):
    """
    Function to remove people with at least one mastodon bot account from
    twitter profiles dataframe. This information is contained in the data
    originally collected from mastodon.

    Parameters:
        profiles_researchers_df: profiles researchers dataframe

    Returns:
        profiles_researchers_df with bot accounts removed
    """

    # remove anyone who has a mastodon bot account
    profiles_researchers_df["is_bot"] = (
        profiles_researchers_df.mastodon_timeline_info.apply(
            lambda x: 1 if any([elem.get("bot", False) for elem in x]) else 0
        )
    )
    n_bot_accounts = profiles_researchers_df["is_bot"].sum()
    print(
        f"out of {len(profiles_researchers_df)} profiles, {n_bot_accounts} profiles with Mastodon bot account(s) are removed."
    )
    profiles_researchers_df = profiles_researchers_df[
        profiles_researchers_df["is_bot"] == 0
    ].reset_index(drop=True)

    return profiles_researchers_df


def remove_tprofiles_created_after_startdate(
    profiles_researchers_df, start_date_nov, common_timezone
):
    """
    Function to remove twitter accounts from twitter profiles dataframe that
    were created after our start date of the migration. The aim is to see if
    people who are already on twitter switched or not.

    Parameters:
        profiles_researchers_df: profiles researchers dataframe start_date_nov:
        start date of the migration common_timezone: common timezone for all
        dates

    Returns:
        profiles_researchers_df with profiles removed that were created after
        the start date
    """

    profiles_researchers_df["created_at"] = (
        profiles_researchers_df["created_at"]
        .dt.tz_localize("UTC")
        .dt.tz_convert(common_timezone)
    )
    initial_count = len(profiles_researchers_df)
    profiles_researchers_df = profiles_researchers_df[
        profiles_researchers_df.created_at <= start_date_nov
    ]
    final_count = len(profiles_researchers_df)
    removed_profiles_count = initial_count - final_count
    print(
        f"Out of {initial_count} profiles, {removed_profiles_count} were removed for being created after the start date."
    )
    return profiles_researchers_df


def remove_tprofiles_without_topics_posts(
    profiles_researchers_df, posts_research_aggregated
):
    """
    Remove  remove people from profiles_researchers_df who dont have any posts
    that passed the cosine similarity threshold with any OpenAlex research
    discipline. this is necessary bc we cannot calculate immediacy for people
    who have no content matched to at least one topic (i.e., it is required for
    comparison between users/influencers).

    Parameters:
        profiles_researchers_df: profiles researchers dataframe
        posts_research_aggregated: posts research aggregated dataframe

    Returns:
        profiles_researchers_df with people removed who have no posts left
    """

    len_before = len(profiles_researchers_df)
    profiles_researchers_df = profiles_researchers_df[
        profiles_researchers_df.id.isin(posts_research_aggregated.id)
    ].reset_index(drop=True)
    print(
        f" {len_before - len(profiles_researchers_df)} people removed from profiles_researchers_df who have no posts left"
    )
    return profiles_researchers_df


def remove_influencers_without_ttimelines(profiles_researchers_df):
    """
    Function to remove influencers from profiles_researchers_df who do not have
    a twitter timeline because we cannot calculate activity for them (for the
    DV). They were only used for social impact calculation.

    Parameters:
        profiles_researchers_df: profiles researchers dataframe

    Returns:
        profiles_researchers_df with people removed that do not have a twitter
        timeline
    """

    initial_profile_count = len(profiles_researchers_df)
    profiles_researchers_df = profiles_researchers_df[
        profiles_researchers_df["is_missing_tTimeline"] == 0
    ].reset_index(drop=True)
    final_count = len(profiles_researchers_df)
    removed_profiles_count = initial_profile_count - final_count
    print(
        f"Out of {initial_profile_count} profiles, {removed_profiles_count} influencers were removed for not having twitter timeline."
    )
    return profiles_researchers_df


def remove_influencers_without_mtimelines(profiles_researchers_df):
    """
    Function to remove influencers from profiles_researchers_df who do not have
    a mastodon timeline because we cannot calculate activity for them (for the
    DV). They were only used for social impact calculation.

    Parameters:
        profiles_researchers_df: profiles researchers dataframe

    Returns:
        profiles_researchers_df with people removed that do not have a mastodon
        timeline
    """

    initial_profile_count = len(profiles_researchers_df)
    profiles_researchers_df = profiles_researchers_df[
        profiles_researchers_df["is_missing_mTimeline"] == 0
    ].reset_index(drop=True)
    final_count = len(profiles_researchers_df)
    removed_profiles_count = initial_profile_count - final_count
    print(
        f"Out of {initial_profile_count} profiles, {removed_profiles_count} influencers were removed for not having mastodon timeline."
    )
    return profiles_researchers_df
