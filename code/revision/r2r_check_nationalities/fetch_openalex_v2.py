#!/usr/bin/env python
"""Fetch OpenAlex author records for the country/region analysis (v2).

Resumable and, with --wait, unattended: when the daily OpenAlex request budget
runs out, the script sleeps until it resets and continues.

    python fetch_openalex_v2.py --wait       # run to completion over several days
    python fetch_openalex_v2.py              # one pass, stop when the budget runs out
    python fetch_openalex_v2.py --status     # progress only, spends nothing
    python fetch_openalex_v2.py --budget 4000    # in one go, if credit has been bought

Background: since 2026 the OpenAlex API is metered; the free tier allows 1,000
requests per day, resetting at midnight UTC. The whole job is about 4,685
requests (234,244 author ids, 50 per request), i.e. about five days on the free
tier.

Progress is checkpointed to openalex_results_v2_partial.json.gz every 200
requests and before every sleep. openalex_results_v2.json.gz is written once
all batches are complete. Progress is also logged to fetch_openalex_v2.log.
"""
import argparse
import datetime as dt
import gzip
import json
import os
import signal
import time

import pandas as pd
import requests
import yaml
from tqdm import tqdm

WORK_DIR   = "/home/lauer/projects/Mastodon/code/revision/r2r_check_nationalities"
# data files live in the shared data folder (config.yml: paths.data.processed.countries)
DATA_DIR   = yaml.safe_load(open("/home/lauer/projects/Mastodon/config.yml"))["paths"]["data"]["processed"]["countries"]
IDS        = os.path.join(DATA_DIR, "author_ids_to_fetch_v2.csv")
PARTIAL    = os.path.join(DATA_DIR, "openalex_results_v2_partial.json.gz")
FINAL      = os.path.join(DATA_DIR, "openalex_results_v2.json.gz")
UNRESOLVED = os.path.join(WORK_DIR, "unresolved_author_ids_v2.csv")
LOGFILE    = os.path.join(WORK_DIR, "fetch_openalex_v2.log")

BASE_URL      = "https://api.openalex.org/authors"
BATCH_SIZE    = 50                              # max OR-values in an ids.openalex filter
SELECT_FIELDS = "id,affiliations,works_count"
MAILTO        = os.environ.get("OPENALEX_MAILTO", "")   # your e-mail for the OpenAlex polite pool
COST_PER_REQ  = 0.0001
PACE          = 0.15                            # seconds between requests
SLEEP_MARGIN  = 120                             # extra seconds after a reset, to be safe
SLEEP_CHUNK   = 1800                            # log a heartbeat every 30 min while waiting


def log(msg):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    tqdm.write(line)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")


def load_ids():
    return pd.read_csv(IDS)["openalex_author_id"].tolist()


def load_partial():
    """Records fetched so far: the checkpoint while a run is in progress, the
    final file once the run is complete (the checkpoint is then redundant)."""
    path = PARTIAL if os.path.exists(PARTIAL) else FINAL
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def save(records, path):
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(records, f)
    os.replace(tmp, path)                       # atomic: never a half-written file


def dedupe(records):
    seen, out = set(), []
    for r in records:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out


def batches_left(records, ids, n_batches):
    """A batch counts as done if any of its ids came back.

    Diffing on ids alone would re-request the ~11% OpenAlex has retired on every
    run. A batch whose ids are all retired looks undone and gets retried once
    more, which is rare and harmless.
    """
    have = {r["id"].split("/")[-1] for r in records}
    return [b for b in range(n_batches)
            if not any(a in have for a in ids[b * BATCH_SIZE:(b + 1) * BATCH_SIZE])]


def sleep_until_reset(seconds):
    """Sleep in chunks, logging a heartbeat, so a long wait visibly stays alive."""
    wake = dt.datetime.now() + dt.timedelta(seconds=seconds)
    log(f"sleeping {seconds / 3600:.1f} h - resuming at {wake:%Y-%m-%d %H:%M:%S}")
    remaining = seconds
    while remaining > 0:
        nap = min(SLEEP_CHUNK, remaining)
        time.sleep(nap)
        remaining -= nap
        if remaining > 0:
            log(f"still waiting - {remaining / 3600:.1f} h to go")


def finish(records, ids):
    records = dedupe(records)
    save(records, FINAL)
    returned = {r["id"].split("/")[-1] for r in records}
    missing = sorted(set(ids) - returned)
    pd.Series(missing, name="openalex_author_id").to_csv(UNRESOLVED, index=False)
    log("COMPLETE -> " + FINAL)
    log(f"  records            : {len(records)}")
    log(f"  ids requested      : {len(ids)}")
    log(f"  resolved           : {len(returned)} ({100 * len(returned) / len(ids):.1f}%)")
    log(f"  retired by OpenAlex: {len(missing)} ({100 * len(missing) / len(ids):.1f}%)"
        f"  -> {os.path.basename(UNRESOLVED)}")
    log("Now run the notebook top to bottom.")


def report(records, todo, n_batches):
    print(f"records collected : {len(records)}")
    print(f"batches done      : {n_batches - len(todo)} / {n_batches}")
    print(f"batches left      : {len(todo)}")
    if todo:
        print(f"  free tier       : {len(todo) / 950:.1f} more day(s) at ~950/day")
        print(f"  or buy outright : ${len(todo) * COST_PER_REQ:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wait", action="store_true",
                    help="sleep through daily budget resets and keep going until done")
    ap.add_argument("--budget", type=int, default=None,
                    help="cap the requests spent this run (default: let OpenAlex decide)")
    ap.add_argument("--max-days", type=int, default=10,
                    help="safety cap on how many budget resets --wait will sit through")
    ap.add_argument("--status", action="store_true", help="report progress and exit")
    ap.add_argument("--mailto", default=MAILTO, help="contact address for the polite pool")
    args = ap.parse_args()

    ids = load_ids()
    n_batches = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE
    records = load_partial()
    todo = batches_left(records, ids, n_batches)

    report(records, todo, n_batches)
    if args.status:
        return
    if not todo:
        finish(records, ids)
        return

    # make sure SIGTERM runs the finally block below rather than killing us outright
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    log(f"starting - {len(todo)} batches to go" + (" (--wait: will sit through resets)"
                                                   if args.wait else ""))
    spent = 0
    resets_waited = 0
    try:
        while True:
            todo = batches_left(records, ids, n_batches)
            if not todo:
                break

            progressed = False
            budget_hit = False
            bar = tqdm(todo, mininterval=5.0)

            for b in bar:
                if args.budget is not None and spent >= args.budget:
                    log(f"reached this run's cap of {args.budget} requests")
                    budget_hit = False
                    break

                params = {"filter": "ids.openalex:" + "|".join(
                              ids[b * BATCH_SIZE:(b + 1) * BATCH_SIZE]),
                          "per-page": BATCH_SIZE,
                          "select": SELECT_FIELDS}
                if args.mailto:
                    params["mailto"] = args.mailto

                try:
                    r = requests.get(BASE_URL, params=params, timeout=60)
                    spent += 1
                except Exception as e:
                    log(f"batch {b}: {e}")
                    time.sleep(5)
                    continue

                if r.status_code == 200:
                    data = r.json()
                    records.extend(data["results"])
                    progressed = True
                    if data.get("meta", {}).get("count", 0) > len(data["results"]):
                        log(f"batch {b}: {data['meta']['count']} matches but "
                            f"{len(data['results'])} returned - pagination is truncating!")
                elif r.status_code == 429:
                    budget_hit = True
                    wait = int(r.headers.get("Retry-After", 0)) or 3600
                    save(dedupe(records), PARTIAL)
                    log(f"daily budget exhausted after {spent} requests this run "
                        f"(~${spent * COST_PER_REQ:.2f})")
                    break
                else:
                    log(f"batch {b}: status {r.status_code} {r.text[:150]}")
                    time.sleep(2)

                if spent % 200 == 0:
                    save(dedupe(records), PARTIAL)
                time.sleep(PACE)

            bar.close()
            records = dedupe(records)
            save(records, PARTIAL)

            if not batches_left(records, ids, n_batches):
                break

            if budget_hit and args.wait:
                if resets_waited >= args.max_days:
                    log(f"hit --max-days ({args.max_days}) - stopping")
                    break
                sleep_until_reset(wait + SLEEP_MARGIN)
                resets_waited += 1
                spent = 0
                continue

            if budget_hit:
                log("stopping - run again after midnight UTC, or use --wait")
                break

            if args.budget is not None and spent >= args.budget:
                break

            if not progressed:
                log("a full pass made no progress - stopping to avoid a spin")
                break

    except KeyboardInterrupt:
        log("interrupted")
    finally:
        records = dedupe(records)
        save(records, PARTIAL)
        left = batches_left(records, ids, n_batches)
        log(f"records now: {len(records)} | batches left: {len(left)} "
            f"| spent this run: {spent} (~${spent * COST_PER_REQ:.2f})")
        if not left:
            finish(records, ids)


if __name__ == "__main__":
    main()
