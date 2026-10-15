from utils.data_loaders import load_researchers_followed_influencer_IDs
from utils.utils import check_df_dtypes


def check_followed_influencers_dtype(cfg, profiles_researchers_df):

    researchers_followed_influencers_df = load_researchers_followed_influencer_IDs(cfg)

    check_df_dtypes(
        researchers_followed_influencers_df,
        columns_to_check=["researcher_id"],
        error=True,
    )
    if (
        not researchers_followed_influencers_df["followed_influencer_ids"]
        .apply(lambda x: all(isinstance(i, str) for i in x))
        .all()
    ):
        raise ValueError("Not all followed_influencer_ids are strings")
    profiles_researchers_df_copy = profiles_researchers_df.merge(
        researchers_followed_influencers_df[
            ["researcher_id", "followed_influencer_ids"]
        ],  # Ensure this is a DataFrame
        left_on="id",
        right_on="researcher_id",
        how="left",
    )
    if not profiles_researchers_df_copy.followed_influencer_ids_y.equals(
        profiles_researchers_df.followed_influencer_ids
    ):
        raise ValueError("followed_influencer_ids are not the same")
