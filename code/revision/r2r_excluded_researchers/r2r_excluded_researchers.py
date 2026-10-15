"""Excluded vs. included researchers (revision, September 2026; Section 2.3).

Of the 410,182 Twitter profiles, 258,409 form the final sample. This script
compares the excluded researchers with the included ones on the profile metadata
available for everyone (account age, follower/following/tweet/listed counts,
protected and verified status) and on whether a valid Mastodon handle was found
and whether that account posted during the migration period (Nov-Dec 2022).
Reads only; writes one aggregate table (table_excluded_vs_included.csv).

    conda activate Twitter-Migration
    python r2r_excluded_researchers.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

CODE_DIR = "/home/lauer/projects/Mastodon/code"
sys.path.append(CODE_DIR)
import utils.utils as utils            # noqa: E402
import utils.data_loaders as loaders   # noqa: E402

cfg = utils.load_config("/home/lauer/projects/Mastodon/config.yml")
FINAL_SAMPLE = "/home/lauer/projects/Mastodon/data/final_analyzed.csv"
MASTODON_TIMELINES = utils.get_path(cfg, "processed", "mastodon", "setup", "timelines_combined.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "table_excluded_vs_included.csv")
START_NOV = pd.Timestamp("2022-11-01", tz="UTC")

# --- all 410,182 profiles, ids fixed and public metrics unnested by the project's own loader
profiles = loaders.load_unnest_tprofiles_main(cfg)
profiles["id"] = profiles["id"].astype(str)
profiles.columns = [c.replace("public_metrics.", "") for c in profiles.columns]  # unnested metric columns
final_ids = set(pd.read_csv(FINAL_SAMPLE, usecols=["id"], dtype={"id": str})["id"])
profiles["included"] = profiles["id"].isin(final_ids)
print(f"profiles: {len(profiles)} | included: {profiles.included.sum()} | excluded: {(~profiles.included).sum()}")

# --- Twitter profile metadata
profiles["account_age_days"] = (START_NOV - pd.to_datetime(profiles["created_at"], unit="ms", utc=True)).dt.days
profiles["has_mastodon_handle"] = profiles["handles_valid_known_combined"].apply(lambda x: isinstance(x, list) and len(x) > 0)

# --- Mastodon activity in Nov-Dec 2022 per handle (the timelines file holds only that period)
toots_per_handle = {}
with open(MASTODON_TIMELINES) as f:
    for line in f:
        h = json.loads(line)["handle"]
        toots_per_handle[h] = toots_per_handle.get(h, 0) + 1
sample_handles = profiles.loc[profiles.has_mastodon_handle, "handles_valid_known_combined"].iloc[0]
print("handle format in profiles:", sample_handles[:2], "| in timelines:", list(toots_per_handle)[:2])
profiles["mastodon_toots_novdec"] = profiles["handles_valid_known_combined"].apply(
    lambda hs: sum(toots_per_handle.get(h, 0) for h in hs) if isinstance(hs, list) else 0)
profiles["mastodon_active_novdec"] = profiles["mastodon_toots_novdec"] > 0

# --- comparison table
def summarise(d):
    return pd.Series({
        "n": len(d),
        "account_age_days_median": d.account_age_days.median(),
        "followers_median": d.followers_count.median(),
        "following_median": d.following_count.median(),
        "tweet_count_median": d.tweet_count.median(),
        "listed_median": d.listed_count.median(),
        "protected_pct": 100 * d.protected.mean(),
        "verified_pct": 100 * d.verified.mean(),
        "mastodon_handle_pct": 100 * d.has_mastodon_handle.mean(),
        "mastodon_active_novdec_pct": 100 * d.mastodon_active_novdec.mean(),
        "mastodon_active_novdec_n": int(d.mastodon_active_novdec.sum()),
    })
table = pd.DataFrame({"included": summarise(profiles[profiles.included]),
                      "excluded": summarise(profiles[~profiles.included])})
table.to_csv(OUT)
pd.set_option("display.width", 200)
print("\n", table.round(2).to_string())

exc = profiles[~profiles.included]
print(f"\nexcluded researchers with a Mastodon handle: {exc.has_mastodon_handle.sum()} "
      f"({100 * exc.has_mastodon_handle.mean():.2f}%); of these, active on Mastodon in Nov-Dec 2022: "
      f"{exc.mastodon_active_novdec.sum()} ({100 * exc.mastodon_active_novdec.mean():.2f}% of all excluded)")
inc = profiles[profiles.included]
print(f"included researchers with a Mastodon handle: {inc.has_mastodon_handle.sum()} "
      f"({100 * inc.has_mastodon_handle.mean():.2f}%); active on Mastodon in Nov-Dec 2022: "
      f"{inc.mastodon_active_novdec.sum()} ({100 * inc.mastodon_active_novdec.mean():.2f}%)")
print(f"excluded and protected: {exc.protected.sum()} ({100 * exc.protected.mean():.1f}%) | included and protected: {inc.protected.sum()}")
print(f"\nwritten {OUT}")

# --- caveat: handles on instances that were never queried (rules prohibited collection
# or no retrievable posts) cannot show activity; quantify how many excluded researchers
# with a handle fall into this group, to bound the number of possible unobserved migrants
queried_instances = {h.split("@")[-1] for h in toots_per_handle}
def on_unqueried_instance(hs):
    return isinstance(hs, list) and len(hs) > 0 and all(h.split("@")[-1] not in queried_instances for h in hs)
exc_handle = exc[exc.has_mastodon_handle]
n_unq = exc_handle["handles_valid_known_combined"].apply(on_unqueried_instance).sum()
print(f"\nexcluded researchers with a handle only on instances absent from the timelines data: {n_unq} of {len(exc_handle)}")
print(f"upper bound on excluded migrants if all of these and all 471 active ones migrated: "
      f"{n_unq + int(exc.mastodon_active_novdec.sum())} of {len(exc)} = {100 * (n_unq + exc.mastodon_active_novdec.sum()) / len(exc):.2f}%")
