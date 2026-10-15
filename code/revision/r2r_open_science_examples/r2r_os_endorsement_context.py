"""Aggregate context of the open-science terms matched in researchers' profile
descriptions (revision, September 2026; Supplementary Appendix 7).

For the researchers flagged as endorsing open science, this script reports, per
matched term group, how many people matched it, how many were flagged by that
term alone, and the most frequent words immediately before and after the match.
Only aggregates are written; no profile description or fragment of one leaves
this script, because even short fragments were found to identify individuals.

Input : final sample (data/final_analyzed.csv) and the cleaned profile
        descriptions used for the flag (posts_research_aggregated.json).
Output: table_os_endorsement_context.csv in this folder.

    conda activate Twitter-Migration
    python r2r_os_endorsement_context.py
"""
import collections
import json
import os
import re

import pandas as pd
import yaml

CONFIG = "/home/lauer/projects/Mastodon/config.yml"
FINAL_SAMPLE = "/home/lauer/projects/Mastodon/data/final_analyzed.csv"
DESCRIPTIONS = ("/home/shared_folder/twitter_migration/data/processed/social_impact/"
                "posts_research_aggregated.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "table_os_endorsement_context.csv")
TOP_N = 8          # neighbouring words reported per side
WINDOW = 3         # look up to this many words away for the nearest non-stopword
STOP = {"and", "the", "of", "in", "a", "to", "for", "on", "with", "at", "i", "am", "my",
        "an", "is", "&", "|", "•", "·", "-", "–", "—", ""}

# the same regular expressions that produced the flag (config.yml)
cfg = yaml.safe_load(open(CONFIG))
patterns = [re.compile(p, re.IGNORECASE)
            for p in cfg["patterns"]["open_science_endorsement"]["open_science_patterns"]]

GROUPS = [  # (label, substring of the normalised match)
    ("open science", "openscience"), ("open access", "openaccess"), ("open data", "opendata"),
    ("open source", "opensource"), ("reproducibility / reproducible", "reproducib"),
    ("preregistration", "registration"),
]


def term_group(match):
    key = re.sub(r"[\s\-]", "", match.lower())
    for label, sub in GROUPS:
        if sub in key:
            return label
    return match.lower()


def normalise(word):
    return re.sub(r"^[^\w]+|[^\w]+$", "", word.lower())


def nearest_word(words, indices):
    for k in indices:
        w = normalise(words[k])
        if w and w not in STOP:
            return w
    return None


# --- flagged researchers and their descriptions --------------------------------
sample = pd.read_csv(FINAL_SAMPLE, usecols=["id", "is_os_endorsement"], dtype={"id": str})
flagged = set(sample.id[sample.is_os_endorsement == True])
descriptions = {}
with open(DESCRIPTIONS) as f:
    for line in f:
        record = json.loads(line)
        if record["id"] in flagged:
            descriptions[record["id"]] = record.get("description") or ""
assert len(descriptions) == len(flagged), "not every flagged researcher has a description"

# --- aggregate ------------------------------------------------------------------
people = collections.Counter()
only = collections.Counter()
before = collections.defaultdict(collections.Counter)
after = collections.defaultdict(collections.Counter)
n_groups = collections.Counter()
for text in descriptions.values():
    words = text.split()
    text = " ".join(words)
    # character span of every token, so that a match inside a token such as
    # "#openscience" is attributed to that whole token
    spans, pos = [], 0
    for w in words:
        spans.append((pos, pos + len(w)))
        pos += len(w) + 1
    groups = set()
    for pattern in patterns:
        for m in pattern.finditer(text):
            g = term_group(m.group(0))
            groups.add(g)
            first = next(i for i, (a, b) in enumerate(spans) if a <= m.start() < b)
            last = next(i for i, (a, b) in enumerate(spans) if a < m.end() <= b)
            w = nearest_word(words, range(first - 1, max(-1, first - 1 - WINDOW), -1))
            if w:
                before[g][w] += 1
            w = nearest_word(words, range(last + 1, min(len(words), last + 1 + WINDOW)))
            if w:
                after[g][w] += 1
    for g in groups:
        people[g] += 1
    if len(groups) == 1:
        only[next(iter(groups))] += 1
    n_groups[len(groups)] += 1

rows = []
for label, _ in GROUPS:
    rows.append({
        "term_group": label,
        "people_matched": people[label],
        "flagged_by_this_term_only": only[label],
        "most_frequent_words_before": "; ".join(f"{w} ({c})" for w, c in before[label].most_common(TOP_N)),
        "most_frequent_words_after": "; ".join(f"{w} ({c})" for w, c in after[label].most_common(TOP_N)),
    })
table = pd.DataFrame(rows)
table.to_csv(OUT, index=False)

print(f"flagged researchers: {len(flagged)} ; matching one / two / three or more term groups: "
      f"{n_groups[1]} / {n_groups[2]} / {sum(c for k, c in n_groups.items() if k >= 3)}")
pd.set_option("display.max_colwidth", 120); pd.set_option("display.width", 250)
print(table.to_string(index=False))
print(f"\nwritten {OUT}")
