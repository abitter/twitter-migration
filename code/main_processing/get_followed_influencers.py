from utils.data_loaders import (
    load_influencer_tprofiles_main,
    load_influencer_followers_main,
)

from utils.utils import check_df_dtypes


def prep_influencers_followers_df(cfg):
    """
    Load influencer profiles df and influencer followers df. Remove some
    non-influencers from the influencer profiles. Remove duplicate influencers
    in followers df.

    Parameters:
    cfg: The config with the data paths.

    Returns:
    influencer_followers_df (DataFrame): The DataFrame containing influencer
    followers data.
    """

    # load influencer profiles
    influencer_profiles_weighted_df = load_influencer_tprofiles_main(cfg)

    # load influencer followers
    influencer_followers_df = load_influencer_followers_main(cfg)

    # sanity check: both from_ids and to_ids should be strings
    check_df_dtypes(influencer_followers_df, columns_to_check=["to_id"], error=True)
    if (
        not influencer_followers_df["from_id"]
        .apply(lambda x: all(isinstance(i, str) for i in x))
        .all()
    ):
        raise ValueError("Not all from_ids are strings")

    # print: for how many influencers in final preprocessed influencer profiles do
    # we have follower data?
    n_found = (
        influencer_profiles_weighted_df["id"].isin(influencer_followers_df["to_id"])
    ).sum()
    print(
        f"{n_found} / {len(influencer_profiles_weighted_df)} influencers profiles IDs found in influencer_followers_df. For some we could not scrape any followers or they had none"
    )

    # removing some non-influencers (and follower info) from df: we collected some
    # followers for people who are not influencers according to the new ranking, so
    # excluding these people here. note: it may be surprising that not all retained
    # Ids are contained in profiles_researchers_df, but the reason is that we
    # removed some people from profiles for whom we could not scrape mastodon
    # accounts - but the influencers have their own profiles researchers df anyways.
    len_before = len(influencer_followers_df)
    influencer_followers_df = influencer_followers_df[
        influencer_followers_df["to_id"].isin(influencer_profiles_weighted_df["id"])
    ].reset_index(drop=True)
    print(
        f"{len_before-len(influencer_followers_df)} people (and their followers) excluded who are not actually influencers"
    )

    # remove duplicate influencers based on number of followers retrieved for them,
    # in descending order, keeping only the first occurrence of each influencer
    # (removing duplicates with fewer followers retrieved)
    print(
        f"{influencer_followers_df.to_id.duplicated().sum()} duplicates in influencer_followers_df. Removing those with fewer followers retrieved."
    )
    influencer_followers_df["from_id_length"] = influencer_followers_df[
        "from_id"
    ].apply(len)
    influencer_followers_df = influencer_followers_df.sort_values(
        by="from_id_length", ascending=False
    )
    influencer_followers_df.drop_duplicates(
        subset="to_id", keep="first", inplace=True, ignore_index=True
    )
    influencer_followers_df.drop(columns="from_id_length", inplace=True)

    # convert each list in the 'from_id' column to a set, so that any duplicate ids
    # among the followers are removed
    influencer_followers_df["from_id"] = influencer_followers_df["from_id"].apply(set)

    return influencer_followers_df


def get_followed_influencers_researcher(researcher_id, influencer_followers_df):
    """
    For a given researcher ID, get followed influencer IDs.

    Parameters:
    researcher_id (int): The ID of the researcher.
    influencer_followers_df (DataFrame): The DataFrame containing influencer followers data.

    Returns:
    dict: A dictionary containing the researcher ID and a list of followed influencer IDs.
    """

    mask = influencer_followers_df["from_id"].apply(lambda x: researcher_id in x)
    followed_influencer_ids = influencer_followers_df.loc[mask, "to_id"].tolist()

    return {
        "researcher_id": researcher_id,
        "followed_influencer_ids": followed_influencer_ids,
    }
