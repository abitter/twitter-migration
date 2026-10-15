import json
import yaml
from pathlib import Path
from tqdm import tqdm
import pandas as pd
from datetime import datetime
import pytz


def load_config(config_path):
    """
    Load the configuration from a given YAML file.

    Args:
    - config_path (str): The path to the configuration YAML file.

    Returns:
    - dict: A dictionary containing the loaded configuration.
    """
    with open(config_path, "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    return cfg


# TODO: possibly update function to better cover this workaround: get_path(cfg,
# "raw", "twitter", "timelines_mongeon_json/data", ""). The issue is that we
# want to be able to navigate to a nested folder without a final final name
# being part of the path, just to navigate to the folder, not a specific file.
# One should be able to remove the empty "" in this update.
def get_path(cfg, *args):
    """
    Construct a path based on a nested configuration dictionary and the provided arguments.

    Parameters:
    - cfg (dict): The configuration dictionary with nested path details.
    - *args: A variable-length argument list containing the keys to traverse
            the nested dictionary in `cfg` and ending with the filename or
            subdirectory you wish to append to the constructed path.

    Returns:
    - pathlib.Path: The constructed path.

    Usage example:
    Given a configuration `cfg` with the structure:
    {
        "Paths": {
            "Processed": {
                "Twitter": {
                    "0_setup": "/path/to/directory"
                }
            }
        }
    }
    Calling:
    get_path(cfg, 'Processed', 'Twitter', '0_setup', 'timelines_rds_combined.json')
    Returns:
    /path/to/directory/timelines_rds_combined.json
    """

    current_cfg = cfg["paths"]["data"]

    for arg in args[:-1]:  # we iterate till the second last argument
        current_cfg = current_cfg[arg]

    path = (
        Path(current_cfg) / args[-1]
    )  # last argument is treated as the file name or subdir
    return str(path)  # converting path object back to string


def check_json_format(file_path):
    with open(file_path, "r") as f:
        first_line = f.readline().strip()
        second_line = f.readline().strip()
        if first_line.startswith("["):
            return (
                "Array of objects, consider using pd.read_json with orient='records'."
            )
        elif first_line.startswith("{") and second_line.startswith("{"):
            return (
                "Line-delimited objects, consider using pd.read_json with lines=True."
            )
        else:
            ValueError("Format not easily determined. Manual inspection recommended.")


def check_json_dtypes(path_json, fields_to_check=["id"], error=True):
    """
    Check that specified fields in a json file are of string type to ensure that
    all IDs are correctly represented. Only works for records-orientated json
    files. Optionally raises an error or prints a warning when a field is not
    represented as a string.

    Parameters:
    - path_json: Path to the JSON file.
    - fields_to_check: List of fields to check for string type.
    - error: If True, raise an error when a non-string field is found. If False,
      print a warning instead.
    """
    all_correct = True  # flag to track if all fields are of the correct type
    with open(path_json, "r") as file:
        for line in tqdm(file):
            json_object = json.loads(line)
            # check that all specified fields are represented as strings
            for field in fields_to_check:
                if not isinstance(json_object.get(field), str):
                    message = f"The field '{field}' is not a string, but {type(json_object.get(field, 'None'))}"
                    all_correct = (
                        False  # update flag to indicate a type mismatch was found
                    )
                    if error:
                        raise ValueError(message)
                    else:
                        print(f"Warning: {message}")
        if all_correct:
            print("All fields checked have the correct type")


def check_df_dtypes(df, columns_to_check=["id"], error=True):
    """
    Check that specified columns in a pandas dataframe exclusively hold strings
    to ensure that all IDs are correctly represented. Optionally raises an error
    or prints a warning when a column does not exclusively hold strings.

    Parameters:
    - df: Pandas DataFrame to check.
    - columns_to_check: List of columns to check for string type.
    - error: If True, raise an error when a column does not exclusively hold
      strings. If False, print a warning instead.
    """
    all_correct = True  # Flag to track if all checks pass

    for column in columns_to_check:
        if not df[column].apply(lambda x: isinstance(x, str)).all():
            message = f"Column '{column}' does not have all values as type str"
            all_correct = False  # Indicate that a mismatch was found
            if error:
                raise ValueError(message)
            else:
                print(f"Warning: {message}")

    if all_correct:
        print("All columns checked hold the correct type: str")


def unnest_column(data, col):
    """Unnest a column of a dataframe that contains dicts."""

    # sanity check: column contains dictionaries
    if not all(isinstance(item, dict) for item in data[col]):
        raise TypeError(f"Column '{col}' does not contain dictionaries only")
    # sanity check: store the original index
    original_index = data.index
    # unnest the column
    unnested_col = pd.json_normalize(data[col])
    # sanity check: index after unnesting same as original index
    if not unnested_col.index.equals(original_index):
        raise ValueError("Index mismatch after unnesting column.")
    # rename new columns
    unnested_col.columns = [f"{col}.{suffix}" for suffix in unnested_col.columns]
    return unnested_col


def min_max_scale_column(df, col_name):
    """
    Min-max scales a column in a dataframe.

    Parameters:
    df (pandas.DataFrame): The dataframe containing the column to be scaled.
    col_name (str): The name of the column to be scaled.

    Returns:
    pandas.Series: The min-max scaled version of the column.
    """
    return (df[col_name] - df[col_name].min()) / (
        df[col_name].max() - df[col_name].min()
    )


def parse_config_date(date_string):
    """
    parse date strings from yml config file
    """
    return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f %Z").replace(
        tzinfo=pytz.utc
    )
