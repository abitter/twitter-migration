import jsons
import pandas as pd
from utils.utils import (
    get_path,
)
from utils.nlp_utils import clean_text


def extract_mtimeline_data(handle, cfg, common_timezone, start_date_nov, end_date_dec):
    try:  # load timeline using handle
        path_timeline = get_path(
            cfg,
            "raw",
            "mastodon",
            "timelines",
            f"{handle}.json",
        )
        with open(
            path_timeline,
            "r",
        ) as f:
            data = f.read()
        timeline = jsons.loads(data)

    except:
        return pd.DataFrame()  # Return empty DataFrame if timeline not found

    # get toots that fall inside desired date range
    toots_nov_dec = [
        {
            "handle": handle,
            "author_id": toot["account"]["id"],
            "toot_id": toot["id"],
            "text": toot["content"],
            "created_at": toot["created_at"].astimezone(common_timezone),
            # "reblog": toot["reblog"] if "reblog" in toot else None,
            "reblog": toot["reblog"],
            "is_reblog": toot["reblog"] is not None,
        }
        for toot in timeline
        if start_date_nov
        <= toot["created_at"].astimezone(common_timezone)
        <= end_date_dec
    ]

    return pd.DataFrame(toots_nov_dec)


def preprocess_mtimelines_main(mastodon_timelines_df, common_timezone):

    # for those reblogs with empty text column cell (almost all), we fill in the
    # text of the original toot, similar to the twitter df where the text columns
    # holds the content of retweets too.
    mask = mastodon_timelines_df["reblog"].notnull() & (
        mastodon_timelines_df["text"].str.len() == 0
    )
    mastodon_timelines_df.loc[mask, "text"] = mastodon_timelines_df.loc[
        mask, "reblog"
    ].apply(lambda x: x["content"])

    # timezone info: localize to UTC and convert to common_timezone.
    mastodon_timelines_df["created_at"] = mastodon_timelines_df[
        "created_at"
    ].dt.tz_localize(common_timezone)

    # clean mastodon timelines text column, removing html tags
    mastodon_timelines_df["text"] = mastodon_timelines_df["text"].parallel_apply(
        clean_text
    )

    return mastodon_timelines_df
