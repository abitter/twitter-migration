import re
from utils.data_loaders import load_posts_research_aggregated_probs_main
from utils.nlp_utils import contains_os_pattern


def flag_open_science_endorsement(cfg, profiles_researchers_df):
    """
    Flag open science endorsement based on open science patterns in the profile
    descriptions (either twitter or mastodon profile, depending on migration
    status).

    Returns:
        profiles_researchers_df with new column "is_os_endorsement" indicating
        whether the profile description contains an open science pattern.
    """

    # load posts with BERTopic document-topic probabilities (people who did not pass
    # the cosine similarity and for whom we can thus not calculate immediacy have
    # been removed)
    posts_research_aggregated = load_posts_research_aggregated_probs_main(cfg)

    # remove people who are not in profiles (influencers without twitter timelines
    # were removed)
    len_before = len(posts_research_aggregated)
    posts_research_aggregated = posts_research_aggregated[
        posts_research_aggregated.id.isin(profiles_researchers_df.id)
    ].reset_index(drop=True)
    print(
        f" {len_before - len(posts_research_aggregated)} / {len_before} people removed from posts_research_aggregated who are not in profiles_researchers_df"
    )

    # Compile regular expressions with the IGNORECASE flag from config file for
    # pattern matching
    open_science_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in cfg["patterns"]["open_science_endorsement"][
            "open_science_patterns"
        ]
    ]

    # flag whether os pattern is in description
    posts_research_aggregated["is_os_pattern_in_description"] = (
        posts_research_aggregated["description"].apply(
            lambda x: contains_os_pattern(x, open_science_patterns)
        )
    )

    # new column in profiles for os endorsement based os pattern in profile
    # description using posts data
    # NOTE: could also extract description from profiles df directly, but we
    # take the final processed posts where we removed mentions from the
    # descriptions (resulting in 15 people less)
    profiles_researchers_df = profiles_researchers_df.merge(
        posts_research_aggregated[["id", "is_os_pattern_in_description"]],
        on="id",
        how="left",
    )
    profiles_researchers_df.rename(
        columns={"is_os_pattern_in_description": "is_os_endorsement"}, inplace=True
    )

    return profiles_researchers_df
