import sys
import requests
from pathlib import Path
import pandas as pd

# # import utils from code directory
# code_dir = Path(__file__).parent.parent.parent
# sys.path.append(str(code_dir))
from utils.utils import find_config, load_config, get_path

# # load config containing paths
# config_path = find_config(Path(__file__).parent)
# cfg = load_config(config_path)


def list_known_minstances(cfg):
    """
    Fetches the list of known Mastodon instances from the instances.social API
    and saves it to a CSV file.
    """

    # Get the secret token file path from config and securely read it
    token_file_path = cfg["paths"]["tokens"]["mastodon_instances_token"]
    with open(token_file_path, "r") as token_file:
        mastodon_instances_token = token_file.read().strip()

    # Use secret token in headers for API calls
    headers = {"Authorization": mastodon_instances_token}

    # Params
    params = {
        "count": 0,
        "include_dead": "false",
        "include_down": "true",
        "include_closed": "true",
    }

    # Path for saving the data
    output_path = get_path(
        cfg, "raw", "mastodon", "known_instances", "known_instances.csv"
    )

    # Fetch and save the data
    response = requests.get(
        cfg["urls"]["mastodon_instances_api"],
        headers=headers,
        params=params,
    )
    instance_names = [instance["name"] for instance in response.json()["instances"]]
    df = pd.DataFrame(instance_names, columns=["instance_name"])
    df.to_csv(output_path, index=False)


# def fetch_instances(headers, params, csv_path):
#     response = requests.get(
#         "https://instances.social/api/1.0/instances/list",
#         headers=headers,
#         params=params,
#     )

#     instance_names = [instance["name"] for instance in response.json()["instances"]]
#     df = pd.DataFrame(instance_names, columns=["instance_name"])
#     df.to_csv(csv_path, index=False)


# # Secret token
# headers = {
#     "Authorization": "Bearer INPUT_TOKEN_HERE"
# }

# # ==================================
# # Dead instances excluded
# # ==================================

# params1 = {
#     "count": 0,
#     "include_dead": "false",
#     "include_down": "true",
#     "include_closed": "true",
# }

# path1 = path_data_hashtags = get_path(
#     cfg, "raw", "mastodon", "known_instances", "known_instances.csv"
# )

# fetch_instances(
#     headers,
#     params1,
#     path1,
# )

# # ==================================
# # Dead instances included
# # ==================================

# params2 = {
#     "count": 0,
#     "include_dead": "true",
#     "include_down": "true",
#     "include_closed": "true",
# }

# path2 = path_data_hashtags = get_path(
#     cfg, "raw", "mastodon", "known_instances", "known_instances_dead.csv"
# )

# fetch_instances(
#     headers,
#     params2,
#     path2,
# )


#################################
