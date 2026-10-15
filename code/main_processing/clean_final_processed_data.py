from utils.data_loaders import load_influencer_tprofiles_main


def clean_final_processed_data(
    cfg, profiles_researchers_df, start_date_nov, common_timezone
):

    # new column account age for use as covariate: difference between
    # the current date and the 'created_at' date in days
    profiles_researchers_df["created_at"] = (
        profiles_researchers_df["created_at"]
        .dt.tz_localize("UTC")
        .dt.tz_convert(common_timezone)
    )
    profiles_researchers_df["twitter_account_age"] = (
        start_date_nov.astimezone(common_timezone)
        - profiles_researchers_df["created_at"]
    ).dt.days

    # convert is_migrated to int
    profiles_researchers_df["is_migrated"] = profiles_researchers_df[
        "is_migrated"
    ].astype(int)

    # new column coding whether a person has a mastodon account created or
    # revitalized in Nov/Dec (which we were able to scrape)
    profiles_researchers_df["is_m_created_or_revital_nov_dec"] = 0
    profiles_researchers_df.loc[
        profiles_researchers_df["account_created_or_revitalized_nov_dec_handles"].apply(
            lambda x: True if isinstance(x, list) else False
        ),
        "is_m_created_or_revital_nov_dec",
    ] = 1

    # from influencer_profiles_weighted_df merge some columns with
    # profiles_researchers_df for plotting
    influencer_profiles_weighted_df = load_influencer_tprofiles_main(cfg)
    profiles_researchers_df = profiles_researchers_df.merge(
        influencer_profiles_weighted_df[
            [
                "id",
                "tweet_count",
                "retweet_count",
                "like_count",
                "mention_count",
                "influence_score_20-80_weighted",
            ]
        ],
        how="left",
        on="id",
    )

    # rename columns
    profiles_researchers_df.rename(
        columns={
            "public_metrics.followers_count": "twitter_followers_count",
            "public_metrics.following_count": "twitter_following_count",
            "public_metrics.tweet_count": "twitter_tweet_count",
            "public_metrics.listed_count": "twitter_listed_count",
            "tweet_count": "influencer_twitter_tweet_count",
            "retweet_count": "influencer_twitter_retweet_count",
            "like_count": "influencer_twitter_like_count",
            "mention_count": "influencer_twitter_mention_count",
            "influence_score_20-80_weighted": "influencer_influence_score_20-80_weighted",
        },
        inplace=True,
    )

    # retain only relevant variables
    profiles_researchers_df = profiles_researchers_df[
        [
            "id",
            "is_m_created_or_revital_nov_dec",
            "is_migrated",
            "is_returned",  # NEW
            "is_os_endorsement",
            "is_influencer",
            "SI_S",
            "SI_N",
            "SI_I",
            "SI_S_abs_minmax_sign",
            "SI_N_minmax",
            "SI_I_minmax",
            "social_impact",
            "twitter_followers_count",
            "twitter_following_count",
            "twitter_tweet_count",
            "twitter_listed_count",
            "twitter_account_age",
            "twitter_activity_since_activity_comp",
            "mastodon_activity_nov_dec",
            "influencer_twitter_tweet_count",
            "influencer_twitter_retweet_count",
            "influencer_twitter_like_count",
            "influencer_twitter_mention_count",
            "influencer_influence_score_20-80_weighted",
        ]
    ]

    return profiles_researchers_df
