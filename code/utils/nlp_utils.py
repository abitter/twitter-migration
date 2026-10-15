from bs4 import BeautifulSoup
import re


def extract_valid_mhandle(handle):
    """
    Extracts a valid Mastodon handle from a given input string.

    Applying a regular expression that breaks down as follows:

    1. [\w.-]+?: Matches one or more word characters (letters, digits, or
    underscores), dots, or hyphens, as few times as possible (non-greedy).
    This part allows for usernames with multiple dots or hyphens.
    2. @: Matches an at symbol (@) which typically follows the username, before
    the instance name should start.
    3. [\w.-]+?: Similar to step 1, this matches one or more word characters,
    dots, or hyphens, as few times as possible. This part allows for the
    instance name, including subdomains, with multiple dots or hyphens.
    4. \.: Matches a literal dot, ensuring that there is at least one dot
    followed by the top-level domain (TLD).
    5. \w+: Matches one or more word characters, representing the TLD, ensuring
    that the instance name ends with a valid TLD.
    (Anything after the last valid word character in the TLD is excluded,
    ensuring that only the valid portion of the handle is captured.)
    """

    handle_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", handle)

    if handle_match:
        return handle_match.group(0)


def categorize_mhandles_valid_invalid(handles):
    """
    Extract and categorize valid and invalid Mastodon handles in a list,
    outputting one list for each category.
    """

    valid_handles = []
    invalid_handles = []
    for handle in handles:
        extracted_handle = extract_valid_mhandle(handle)
        if extracted_handle:
            valid_handles.append(extracted_handle)
        else:
            invalid_handles.append(handle)
    return valid_handles, invalid_handles


def contains_known_minstance(handle, known_instances_set):
    """
    Extract instance substring from handle, convert to lowercase, and check
    if it contains a known instance using known_instances_set.
    """

    handle_lower = handle.split("@")[-1].lower()

    for instance in known_instances_set:
        # no checking for containment anymore but exact match, resulting in 38
        # less people, but thats ok!
        # if instance in handle_lower:
        if instance == handle_lower:
            return True
    return False


def lower_minstance_substring(handle):
    """
    Find the last '@' symbol in a Mastodon handle and convert everything
    after it (instance name) to lowercase.
    """
    last_at_index = handle.rfind("@")
    return handle[: last_at_index + 1] + handle[last_at_index + 1 :].lower()


def categorize_mhandles_known_unknown(handles, known_instances_set):
    """
    Categorizes valid mastodon handles in a list as belonging to known or
    unknown instances, outputting one list for each category.
    """

    known_handles = []
    unknown_handles = []
    for handle in handles:
        if contains_known_minstance(handle, known_instances_set):
            known_handles.append(handle)
        else:
            unknown_handles.append(handle)
    return known_handles, unknown_handles


def is_valid_mastodon_url(string, known_instances_set):
    """
    Check if a URL contains a valid Mastodon handle with a known instance.
    """

    # Check if the string starts with "https://"
    if not string.startswith("https://"):
        return False

    # Split the string by "/" to extract domain and path parts
    parts = string.split("/")

    # Check if there are enough parts (at least 3 for a valid URL)
    if len(parts) < 3:
        return False

    # Check if the domain part is in the known Mastodon instances set
    domain = parts[2]
    if domain not in known_instances_set:
        return False

    # Check if the last segment contains "@"
    last_segment = parts[-1]
    if "@" not in last_segment:
        return False

    return True


def reformat_url(url):
    """
    reformat urls with mastodon handles to extract handle in typical format.
    """
    segments = url.replace("https://", "").split("/")
    return segments[-1] + "@" + segments[0]


def deduplicate_mhandles(handles):
    """
    remove duplicates in a list of mastodon handles: keep the first occurrence
    of a handle in its original casing, dropping all other identical handles
    irrespective of casing. rationale: we don't want to search for and scrape
    the same profile more than once
    """
    seen = set()
    unique_handles = []

    for handle in handles:
        lowercase_handle = handle.lower()
        if lowercase_handle not in seen:
            unique_handles.append(handle)
            seen.add(lowercase_handle)

    return unique_handles


def clean_text(text):
    """
    clean mastodon timelines text as it is in html-format
    """
    if text is None:
        return None
    if text == "":
        return ""
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text(separator=" ")
    # remove the space between hashtag symbol and the actual hashtag text
    clean_text = re.sub(r"# ", "#", clean_text)
    # remove any space that might have been introduced between "https://"
    # and the rest of the URL
    clean_text = re.sub(r"https:// ", "https://", clean_text)
    return clean_text


def remove_handles_and_urls(text):
    """Remove different types of account handles and URLs from text"""

    # Remove account handles with domain-like structure
    domain_handle_pattern = r"@[A-Za-z0-9_]+@[A-Za-z0-9_.-]+"
    text = re.sub(domain_handle_pattern, "", text)

    # Remove regular account handles
    handle_pattern = r"@[A-Za-z0-9_]+"
    text = re.sub(handle_pattern, "", text)

    # Remove URLs
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    text = re.sub(url_pattern, "", text)

    return text


def remove_newline_chars_spaces(text):
    """
    clean text by replacing newline characters with spaces and then removing
    extra spaces.
    """
    return " ".join(text.replace("\n", " ").split())


def wrapper_remove_handles_and_urls(text):
    """wrapper for cleaning function to avoid error when text is None"""
    if text is not None:
        return remove_handles_and_urls(text)
    else:
        return None


def wrapper_remove_newline_chars_spaces(text):
    """wrapper for cleaning function to avoid error when text is None"""
    if text is not None:
        return remove_newline_chars_spaces(text)
    else:
        return None


def contains_os_pattern(description, open_science_patterns):
    """
    Check if a given string (description) contains any of the open science patterns.
    Returns True if at least one pattern is found, False otherwise.
    """
    return any(pattern.search(description) for pattern in open_science_patterns)
