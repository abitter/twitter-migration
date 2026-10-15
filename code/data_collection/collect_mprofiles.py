from mastodon import Mastodon
from pathlib import Path
import pandas as pd
import jsons
import warnings
import logging

from utils.utils import (
    get_path,
)


def collect_mprofiles(cfg):
    """
    Function for loading tokens and scraping profiles for mastodon handles
    identified in twitter profiles. logging erros that occur while scraping, not
    errors that occur while loading credentials (some may be missing), this is
    handled in the previous script.

    NOTE: updated the twitter profiles file (with deduplicated handles) and ran
    the script again, given that we have now also collected some more tokens so
    we get some more mastodon profiles. Essentially, we are only collecting
    additional profiles if they dont exist already.

    NOTE: account_search returns the "best guess" for the handle. there are some
    cases were the returned account simply has different casing but it is the
    same person. these cases are logged as warning. however, there are also
    cases where a completely different handle is matched, which is bad (also
    logged as warning). The logging file is manually screened for these invalid
    matches and they are removed at the end.
    """

    # logging errors
    logging_errors_path = get_path(
        cfg,
        "raw",
        "mastodon",
        "profiles",
        "#collect_profiles_errorsLog.log",
    )
    logging.basicConfig(
        filename=logging_errors_path,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # read twitter profiles with mastodon handles
    path_profiles_researchers = get_path(
        cfg,
        "processed",
        "twitter",
        "extract_handles",
        # "profiles_researchers_combined_handles.json",
        "profiles_researchers_combined_handles_updated.json",  # updated, deduplicated handles
    )
    profiles_researchers_df = pd.read_json(
        path_profiles_researchers, orient="records", lines=True
    )

    for index, row in profiles_researchers_df.iterrows():
        if row["handles_valid_known_combined"]:  # skipping empty lists (no handles)
            for handle in row["handles_valid_known_combined"]:
                # extracting instance from handle
                username, instance = handle[1:].split(
                    "@"
                )  # splitting by '@' and removing the leading '@'

                # path to profile for handle
                path_profile = get_path(
                    cfg,
                    "raw",
                    "mastodon",
                    "profiles",
                    f"{handle}.json",
                )

                if not Path(path_profile).exists():
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

                    if (
                        Path(client_cred_path).exists()
                        and Path(user_cred_path).exists()
                    ):
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
                    else:
                        print(
                            f"Client and/or user credentials not found for {instance}, continuing..."
                        )
                        continue

                    # set up the Mastodon client for this instance using the loaded credentials
                    try:
                        mastodon = Mastodon(
                            client_id=client_id,
                            client_secret=client_secret,
                            access_token=access_token,
                            api_base_url=f"https://{instance}",
                        )

                        # lookup the user by their handle using account_search
                        accounts = mastodon.account_search(handle)
                    except Exception as e:
                        logging.error(f"Error while scraping {handle}: {e}")
                        continue

                    if not accounts:
                        logging.error(
                            f"No accounts found for {handle} using account_search(); maybe handle wrong or account deleted?"
                        )
                        continue

                    # the first account should be the right one, but we check below using the url
                    account = accounts[0]

                    def reformat_handle(handle):
                        username, domain = handle.rsplit(
                            "@", 1
                        )  # splitting on the last @
                        return f"https://{domain}/{username}"

                    # sanity check
                    if account["url"] != reformat_handle(handle):
                        # NOTE: account_search returns the best guess for the
                        # account. there are some cases were the returned
                        # account simply has different casing but it is the same
                        # person. these cases are logged as warning. however,
                        # there are also cases where a completely different
                        # handle is matched, which is bad (also logged as
                        # warning). The logging file is manually screened for
                        # these invalid matches and they are removed.
                        error_message = (
                            f"Error: url reformatted from handle {reformat_handle(handle)} does not match "
                            f"the url for the account returned by account_search: {account['url']}"
                            f"- we may be able to rescue this person, maybe it is just do to capitalization?"
                        )
                        logging.error(error_message)

                    # apply jsons dump, supressing warning
                    warnings.filterwarnings(
                        "ignore",
                        category=UserWarning,
                        module="jsons._common_impl",
                        message=".*datetime-without-tz.*",
                    )
                    json_string = jsons.dumps(account)

                    # save json file
                    with open(path_profile, "w") as f:
                        f.write(json_string)

                else:
                    continue

    # postprocessing: deleting manually screened invalid matches
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
            "profiles",
            f"{handle}.json",
        )
        if Path(path_nonmatching).exists():
            # delete file
            Path(path_nonmatching).unlink()
            # print
            print(f"Deleted {path_nonmatching}")
