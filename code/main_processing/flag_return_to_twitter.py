import numpy as np
from utils.data_loaders import load_ttimelines_main


def flag_return_to_twitter(
    cfg,
    profiles_researchers_df,
    start_date_apr,
    end_date_apr,
    common_timezone,
):
    """
    This function flags among migrating researchers who returned to twitter by
    April 2023, creating a new column "is_returned" in the
    profiles_researchers_df dataframe.

    Returns:
        profiles_researchers_df with new column "is_returned"
    """

    # load timelines
    twitter_timelines_df = load_ttimelines_main(cfg)

    # preprocess timelines
    # TODO: some redundancy with preprocess_ttimelines_main function
    twitter_timelines_df["created_at"] = (
        twitter_timelines_df["created_at"]
        .dt.tz_localize("UTC")
        .dt.tz_convert(common_timezone)
    )
    twitter_timelines_df.set_index(["author_id", "created_at"], inplace=True)
    twitter_timelines_df.sort_index(inplace=True)
    if not twitter_timelines_df.index.is_monotonic_increasing:
        raise ValueError("The index is not increasing.")

    # extract mastodon activity (sum of toots, reposts etc.) for apr for
    # migrated persons. If multiple accounts: sum of activity. If not migrated
    # assigning NaN.
    profiles_researchers_df["mastodon_activity_apr"] = profiles_researchers_df[
        "account_created_or_revitalized_nov_dec"
    ].apply(lambda x: np.nan if not x else sum([elem["activity_apr"] for elem in x]))
    profiles_researchers_df.loc[
        profiles_researchers_df["is_migrated"] == 0, "mastodon_activity_apr"
    ] = np.nan

    def get_twitter_activity_return(id):
        """
        Determine twitter activity count for a person (id) from April 1st to 31st, to
        see if person returned to Twitter.
        """

        activity_count = twitter_timelines_df.loc[
            (id, start_date_apr):(id, end_date_apr)
        ].shape[0]

        return activity_count

    # get twitter activity for apr for all researchers, creating new col
    profiles_researchers_df["twitter_activity_apr"] = profiles_researchers_df[
        "id"
    ].apply(get_twitter_activity_return)

    # if not migrated, assign NaN
    profiles_researchers_df.loc[
        profiles_researchers_df["is_migrated"] == 0, "twitter_activity_apr"
    ] = np.nan

    # flag migrated people that returned to twitter with True, others with False
    # (or NaN if not migrated)
    profiles_researchers_df["is_returned"] = (
        profiles_researchers_df["twitter_activity_apr"]
        > profiles_researchers_df["mastodon_activity_apr"]
    )
    print(
        f'{profiles_researchers_df["is_returned"].sum()} out of {profiles_researchers_df["is_migrated"].sum()} migrated persons returned to twitter by April 2023'
    )

    return profiles_researchers_df
