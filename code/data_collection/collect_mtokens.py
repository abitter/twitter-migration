from mastodon import Mastodon
import pandas as pd
from pathlib import Path
import logging
from utils.utils import (
    get_path,
)


def collect_mtokens(cfg):
    """
    Function for collecting access tokens from account credentials for multiple
    instances. The script can be run multiple times: errors are logged
    continuously
    - EDIT: ran the script again to collect some mmore credentials as we updated
    the list of instances
    """

    # logging errors
    logging_errors_path = get_path(
        cfg,
        "raw",
        "mastodon",
        "known_instances/tokens",
        "#collect_tokens_errorsLog.log",
    )
    logging.basicConfig(filename=logging_errors_path, level=logging.ERROR)

    ## load/preprocess csv with instance credentials

    # Load csv
    patch_instances = get_path(
        cfg,
        "processed",
        "mastodon",
        "instances_identification",
        # "instances_users_check_TOS_evaluated.csv",
        "instances_users_check_TOS_evaluated_updated_v2.csv",  # updated instances
    )
    df = pd.read_csv(patch_instances)

    # retain only instances where data collection is not prohibited in TOS
    df = df[df["data_collection_prohibited"] == "0"]

    # retain only instances for which we were able to get credentials
    df = df[df.status == "done"]

    # new column api_base_url from instance name
    df["api_base_url"] = df["instance"].apply(lambda x: f"https://{x}")

    # retain only relevant columns
    df = df[["api_base_url", "email", "password"]]

    # convert dataframe to list of dictionaries
    instances_credentials_list = df.to_dict(orient="records")

    ## for each instance, create app and save tokens

    not_working_apps = []
    not_working_user_credentials = []
    for creds in instances_credentials_list:
        # create an app (if not exist), saving the client credentials to a file
        client_cred_path = get_path(
            cfg,
            "raw",
            "mastodon",
            "known_instances/tokens",
            f"{creds['api_base_url'].split('//')[-1]}_clientcred.secret",
        )
        if not Path(client_cred_path).exists():
            try:
                Mastodon.create_app(
                    "test_app",
                    api_base_url=creds["api_base_url"],
                    to_file=client_cred_path,
                )
                print(f"Created app for {creds['api_base_url']}")
            except Exception as e:
                logging.error(
                    f"Error while creating app for {creds['api_base_url']}: {e}"
                )
                not_working_apps.append(creds["api_base_url"])
                continue  # Move on to the next set of credentials

        # log in (if not exist user credentials) and obtain user access token, saving
        # to file
        user_cred_path = get_path(
            cfg,
            "raw",
            "mastodon",
            "known_instances/tokens",
            f"{creds['api_base_url'].split('//')[-1]}_usercred.secret",
        )
        if not Path(user_cred_path).exists():
            try:
                mastodon = Mastodon(
                    client_id=client_cred_path, api_base_url=creds["api_base_url"]
                )
                mastodon.log_in(
                    creds["email"], creds["password"], to_file=user_cred_path
                )
                print(f"Logged in to {creds['api_base_url']}")
            except Exception as e:
                logging.error(f"Error while logging in to {creds['api_base_url']}: {e}")
                not_working_user_credentials.append(creds["api_base_url"])
                continue  # Move on to the next set of credentials
    print(
        f"Was not able to create {len(not_working_apps)}/{len(instances_credentials_list)} apps: "
        f"{not_working_apps} "
        f"Was not able to log in to {len(not_working_user_credentials)}/{len(instances_credentials_list)} instances: "
        f"{not_working_user_credentials} "
    )
