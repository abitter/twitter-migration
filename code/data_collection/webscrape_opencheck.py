# !pip install BeautifulSoup4
import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from utils.utils import get_path


def webscrape_opencheck(cfg):
    """
    Scrape the opencheck website where people openly share their Twitter and/or
    Mastodon account information. For each listed discipline, retrieve all
    listed people and corresponding Twitter/Mastodon accounts. Output is a csv
    file with columns person, twitter, mastodon, and discipline.

    Parameters:
        cfg (dict): The config with the data paths and urls.

    Returns:
        None
    """

    # url to scrape
    url = cfg["urls"]["open_check"]

    # path output csv file
    file_path = get_path(
        cfg,
        "raw",
        "open_datasets",
        "opencheck",
        "All_disciplines.csv",
    )

    # parse the HTML content using BeautifulSoup and get all links on the page
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all("a")

    # make list of all links that contain "topic" in the href and add
    # https://opencheck.is/ to the beginning to get the full url for each
    # discipline
    links_full = []
    for link in links:
        if "topic" in link.get("href"):
            link = "https://opencheck.is" + link.get("href")
            links_full.append(link)

    # looping over disciplines
    for index, url in enumerate(links_full):
        # parse the HTML content of discipline website using BeautifulSoup
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # make list of all text, splitting by \n
        text_list = soup.get_text().split("\n")

        # the information for each person is now surrounded by whitespaces (and
        # there are no whitespaces "within" a person); create a new list of
        # sublists with each person's information (don't worry about artefacts
        # at top/bottom of webpage - will be removed later)
        result = []
        sublist = []
        for item in text_list:
            if item != "":
                sublist.append(item)
            elif sublist:
                result.append(sublist)
                sublist = []
        if sublist:  # handle any remaining items
            result.append(sublist)

        # in each sublist, retain only the first string (name) and strings that
        # contain "Twitter" or "Mastodon"
        for i in range(len(result)):
            result[i] = [
                x
                for x in result[i]
                if x == result[i][0] or "Twitter" in x or "Mastodon" in x
            ]

        # pandas dataframe
        df = pd.DataFrame(result)

        # if there are less than 3 columns (person doesn't have twitter and/or
        # mastodon), add empty columns so that dfs can be concatenated later
        if len(df.columns) == 2:
            df[2] = None
        elif len(df.columns) == 1:
            df[1] = None
            df[2] = None
        df = df.rename(columns={0: "person", 1: "twitter", 2: "mastodon"})

        # for each string in the twitter column, check if the string contains
        # characters "Twitter: " and remove to get just the account name (also
        # do this for the mastodon column)
        for i in range(len(df)):
            if df["twitter"][i] is not None:
                if "Twitter: " in df["twitter"][i]:
                    df["twitter"][i] = df["twitter"][i].replace("Twitter: ", "")
                else:
                    raise ValueError(
                        "Twitter column does not contain string 'Twitter: '"
                    )
            if df["mastodon"][i] is not None:
                if "Mastodon: " in df["mastodon"][i]:
                    df["mastodon"][i] = df["mastodon"][i].replace("Mastodon: ", "")
                else:
                    raise ValueError(
                        "Mastodon column does not contain string 'Mastodon: '"
                    )

        # remove all rows where both twitter and mastodon columns are None
        # (removing people without accounts as well as artefacts at the
        # top/bottom of webpage)
        df = df.dropna(subset=["twitter", "mastodon"], how="all")

        # add column with discipline name using regular expression on the url
        # (e.g. "https://opencheck.is/topic/psychiatry" --> "psychiatry")
        df["discipline"] = re.findall(r"topic/(.*)", url)[0]

        # append dataframe to (existing) csv file
        if index == 0:  # add header only on the first iteration
            df.to_csv(file_path, mode="a", header=True, index=False)
        else:
            df.to_csv(file_path, mode="a", header=False, index=False)
