from mastodon import Mastodon
from pathlib import Path
import pandas as pd
import jsons
import pytz
import logging
import pytz
import glob
from tqdm import tqdm
import warnings
import jsons
from utils.utils import (
    get_path,
)


def collect_mtimelines(cfg):
    """
    Function for loading tokens and scraping timelines based on collected
    profiles, using id contained in profile. logging erros that occur while
    scraping timelines, not errors that occur while loading credentials or
    scraping profiles (some may be missing), see other functions

    NOTE: scraping again because we scraped some more profiles. Included
    post-processing step at the end where some invalid matches that were
    manually identified are deleted
    """

    # logging errors
    logging_errors_path = get_path(
        cfg,
        "raw",
        "mastodon",
        "timelines",
        "#collect_timelines_errorsLog.log",
    )
    logging.basicConfig(
        filename=logging_errors_path,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # path to profiles
    path_profiles = get_path(cfg, "raw", "mastodon", "profiles", "")

    # to convert time of toots to common timezone (UTC)
    common_timezone = pytz.timezone("UTC")

    # all json profiles paths
    all_profiles = glob.glob(path_profiles + "/*.json")

    for index, profile in tqdm(enumerate(all_profiles)):
        handle = (profile.split("/")[-1]).split(".json")[0]

        username, instance = handle[1:].split(
            "@"
        )  # Splitting by '@' and removing the leading '@'

        # path to timeline for handle
        path_timeline = get_path(
            cfg,
            "raw",
            "mastodon",
            "timelines",
            f"{handle}.json",
        )

        if not Path(path_timeline).exists():
            # path to client and user credentials for extracted instance
            client_cred_path = get_path(
                cfg,
                "raw",
                "mastodon",
                "known_instances/tokens",
                f"{instance}_clientcred.secret",
            )
            user_cred_path = get_path(
                cfg,
                "raw",
                "mastodon",
                "known_instances/tokens",
                f"{instance}_usercred.secret",
            )

            # load the client credentials and user access token from the .secret files
            with open(client_cred_path, "r") as f:
                lines = f.readlines()
                client_id = lines[0].strip()
                client_secret = lines[1].strip()

            with open(user_cred_path, "r") as f:
                lines = f.readlines()
                access_token = lines[
                    0
                ].strip()  # assuming the access_token is on the first line

            # set up the Mastodon client for this instance using the loaded credentials
            mastodon = Mastodon(
                client_id=client_id,
                client_secret=client_secret,
                access_token=access_token,
                api_base_url=f"https://{instance}",
            )

            # Load the JSON profile
            with open(
                profile,
                "r",
            ) as f:
                profile_data_json = f.read()

            # deserialize the JSON data into a Python object
            profile_data = jsons.loads(profile_data_json)

            # get id from profile
            user_id = profile_data["id"]

            # Initialize an empty list to store the collected toots
            collected_toots = []

            # coninously fetch toots until oldest toot is before start date using max_id
            max_id = None
            broke_out_unexpectedly = False  # flag for continuing with outer for loop if while loop broke unexpectedly
            while True:
                try:
                    # fetch the user's timeline
                    # TODO: do we need to check that 40 is the right limit for all instances?
                    user_toots = mastodon.account_statuses(
                        user_id, max_id=max_id, limit=40
                    )
                except Exception as e:
                    logging.error(f"Error fetching statuses for {handle}: {e}")
                    broke_out_unexpectedly = True
                    break  # break while loop: error while fetching

                if not user_toots:
                    break  # break while loop: no more toots to fetch

                # extend collected toots with batch
                collected_toots.extend(user_toots)

                # set the id of the oldest toot as the new max_id for the next batch
                max_id = user_toots[-1]["id"]

            # if while loop broke unexpectedly (error while fetching) or no toots
            # were collected bc there are none, continue with next iteration of
            # outer for loop
            if broke_out_unexpectedly or not collected_toots:
                continue

            # sanity check: logg any difference between number of collected toots and statuses_count
            if len(collected_toots) < collected_toots[0]["account"]["statuses_count"]:
                logging.warning(
                    f"For {handle}, fetched {len(collected_toots)} toots but "
                    f"{collected_toots[0]['account']['statuses_count']} total toots "
                    f"indicated by profile field. Small difference OK, large not."
                )

            # no warning for jsons dumps
            warnings.filterwarnings(
                "ignore",
                category=UserWarning,
                module="jsons._common_impl",
                message=".*datetime-without-tz.*",
            )

            # save as json file using jsons package
            json_string = jsons.dumps(collected_toots)
            with open(path_timeline, "w") as f:
                _ = f.write(json_string)  # _ to suppress output

        else:
            continue

    # postprocessing: deleting manually screened invalid matches, see collect_profiles.py
    path_nonmatching_accounts = get_path(
        cfg,
        "raw",
        "mastodon",
        "profiles",
        "exclude_not_matching_handles.csv",
    )
    nonmatching_accounts_df = pd.read_csv(
        path_nonmatching_accounts, header=None, names=["nonmatching"]
    )
    for index, row in nonmatching_accounts_df.iterrows():
        handle = row["nonmatching"]
        path_nonmatching = get_path(
            cfg,
            "raw",
            "mastodon",
            "timelines",
            f"{handle}.json",
        )
        if Path(path_nonmatching).exists():
            # delete file
            Path(path_nonmatching).unlink()
            # print
            print(f"Deleted {path_nonmatching}")
