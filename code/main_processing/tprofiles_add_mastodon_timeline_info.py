import jsons
from datetime import datetime
import pandas as pd
import numpy as np


def get_m_timeline_info(
    handle,
    path_timeline_folder,
    start_date,
    end_date,
    common_timezone,
    start_date_revitalized,
    end_date_revitalized,
    start_date_return,
    end_date_return,
):
    """
    Extract relevant information from a single Mastodon user's timeline using
    the handle as identifier.

    Parameters:
        handle (str): Mastodon handle of the user. start_date(datetime): Start
        date for migration period end_date (datetime): End date for migration
        period common_timezone (timezone): Common timezone for all dates
        start_date_revitalized (datetime): Start date for revitalization period
        end_date_revitalized (datetime): End date for revitalization period
        start_date_return (datetime): Start date for return to Twitter period

    Returns:
        dict: A dictionary containing various relevant extracted information
        (handle, account_creation_date, activity_nov_dec, activity_jan_oct,
        activity_apr, activity_total, is_account_created_nov_dec,
        is_account_revitalized_nov_dec, is_missing_timeline,
        profile_description, is_bot, earliest_post_nov_dec_date,
    """

    try:
        # load timeline using handle
        path_timeline = path_timeline_folder + f"/{handle}.json"
        with open(
            path_timeline,
            "r",
        ) as f:
            data = f.read()
        timeline = jsons.loads(data)

    except:
        # flag missing timeline to filter out later
        return {"handle": handle, "is_missing_timeline": 1}

    # extract account creation date
    account_creation_date = timeline[0]["account"]["created_at"].astimezone(
        common_timezone
    )
    assert isinstance(
        account_creation_date, (datetime, pd.Timestamp)
    ), "Date variable is not a datetime object"  # TEMP

    # get toots that fall inside desired date range
    toots_nov_dec = [
        toot
        for toot in timeline
        if start_date <= toot["created_at"].astimezone(common_timezone) <= end_date
    ]
    activity_nov_dec = len(toots_nov_dec)

    # get earliest post for Nov/Dec to later get the start date activity
    # comparison for revitalized accounts (for accounts created between Nov/Dec,
    # the start date is always account creation date)
    earliest_post_nov_dec_date = (
        min([toot["created_at"].astimezone(common_timezone) for toot in toots_nov_dec])
        if toots_nov_dec
        else None
    )
    assert earliest_post_nov_dec_date is None or isinstance(
        earliest_post_nov_dec_date, (datetime, pd.Timestamp)
    ), "Date variable is not a datetime object"

    # check if any of the toots were made by bots
    is_bot = any(toot.get("account", {}).get("bot", False) for toot in toots_nov_dec)

    # get toots that fall inside desired date range for revitalized accounts
    toots_jan_oct = [
        toot
        for toot in timeline
        if start_date_revitalized
        <= toot["created_at"].astimezone(common_timezone)
        <= end_date_revitalized
    ]
    activity_jan_oct = len(toots_jan_oct)

    # binary for newly created accounts in Nov/Dec
    is_account_created_nov_dec = int(
        start_date <= account_creation_date.astimezone(common_timezone) <= end_date
    )

    # binary for revitalized accounts in Nov/Dec
    # NOTE: corrected a minor bug (<= to <) so that there are no overlapping
    # normal and revitalized accounts on the same day (nov 1st). this may have
    # slightly affected e.g. start date of activity comparison.
    is_account_revitalized_nov_dec = int(
        (
            account_creation_date.astimezone(common_timezone)
            # <= start_date  # account creation date before Nov 2022 # minor bug
            < start_date  # account creation date before Nov 2022 # NEW
        )
        and (activity_jan_oct == 0)
        and (activity_nov_dec > 0)
    )

    # get toots that fall inside desired date range for returing to twitter
    toots_apr = [
        toot
        for toot in timeline
        if start_date_return
        <= toot["created_at"].astimezone(common_timezone)
        <= end_date_return
    ]
    activity_apr = len(toots_apr)

    # total activity of user
    activity_total = len(timeline)

    # extracting profile description from most recent toot (compared this
    # description with the corresponding scraped profile: identical!)
    profile_description = timeline[0]["account"]["note"]

    # return dictionary with relevant information
    return dict(
        handle=handle,
        account_creation_date=account_creation_date,
        activity_nov_dec=activity_nov_dec,
        activity_jan_oct=activity_jan_oct,
        activity_apr=activity_apr,
        activity_total=activity_total,
        is_account_created_nov_dec=is_account_created_nov_dec,
        is_account_revitalized_nov_dec=is_account_revitalized_nov_dec,
        is_missing_timeline=0,
        profile_description=profile_description,
        is_bot=is_bot,
        earliest_post_nov_dec_date=earliest_post_nov_dec_date,
    )


def new_cols_from_info_col(profiles_researchers_df):

    # new column for accounts created or revitalized in nov-dec
    profiles_researchers_df["account_created_or_revitalized_nov_dec"] = (
        profiles_researchers_df.mastodon_timeline_info.apply(
            lambda x: [
                elem
                for elem in x
                if (elem.get("is_account_created_nov_dec", 0) == 1)
                or (elem.get("is_account_revitalized_nov_dec", 0) == 1)
            ]
        )
    )

    # handles of accounts created or revitalized in Nov/Dec
    profiles_researchers_df["account_created_or_revitalized_nov_dec_handles"] = (
        profiles_researchers_df["account_created_or_revitalized_nov_dec"].apply(
            lambda x: np.nan if not x else [elem["handle"] for elem in x]
        )
    )

    # profile description of accounts created or revitalized in Nov/Dec
    profiles_researchers_df["account_created_or_revitalized_nov_dec_description"] = (
        profiles_researchers_df["account_created_or_revitalized_nov_dec"].apply(
            lambda x: np.nan if not x else [elem["profile_description"] for elem in x]
        )
    )

    def combine_descriptions(list_of_descriptions):
        """
        Combines profile descriptions into a single string if multiple accounts, or
        returns the profile description if just one account.
        """
        if isinstance(list_of_descriptions, list):
            if len(list_of_descriptions) > 1:
                return " ".join(list_of_descriptions)
            else:
                return list_of_descriptions[0]

    # combined profile descriptions per person (if more than one account)
    profiles_researchers_df[
        "account_created_or_revitalized_nov_dec_description_combined"
    ] = profiles_researchers_df[
        "account_created_or_revitalized_nov_dec_description"
    ].apply(
        combine_descriptions
    )

    # mastodon activity (sum of toots, reposts etc.) for nov-dec for each person
    # with account created or revitalized in nov-dec. If multiple accounts: sum
    # of activity. If no mastodon account, assigning NaN instead of 0.
    profiles_researchers_df["mastodon_activity_nov_dec"] = profiles_researchers_df[
        "account_created_or_revitalized_nov_dec"
    ].apply(
        lambda x: np.nan if not x else sum([elem["activity_nov_dec"] for elem in x])
    )

    # start date acvitity comparison based on mastodon account creation date or,
    # in the case of revitalized account, the date of the first post in our time
    # period of interest. if multiple accounts, we use the min.
    profiles_researchers_df["start_date_activity_comparison"] = (
        profiles_researchers_df.account_created_or_revitalized_nov_dec.apply(
            lambda x: (
                np.nan
                if not x
                else min(
                    [
                        (
                            elem["earliest_post_nov_dec_date"]
                            if elem["is_account_revitalized_nov_dec"]
                            else elem["account_creation_date"]
                        )
                        for elem in x
                    ]
                )
            )
        )
    )

    return profiles_researchers_df
