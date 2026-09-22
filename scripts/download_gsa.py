"""FAST downloader: GSA prime contract transactions via spending_by_transaction.

Uses ONLY the paginated transaction endpoint (no bulk Custom Award files),
requesting the smallest practical field set for vendor-spend/concentration
analytics. One page = 100 rows (API max); pages stream straight to CSV.

Usage:
    python scripts/download_gsa.py --test                # FY2021, 100 rows, no files
    python scripts/download_gsa.py --fy 2021             # one full year
    python scripts/download_gsa.py --fy 2021 --time-budget 45  # bounded chunk, rerun to resume
    python scripts/download_gsa.py --fy all              # all six years, sequential
    python scripts/download_gsa.py --fy 2021 --force     # redownload existing file
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
META_PATH = RAW_DIR / "GSA_download_metadata.json"

BASE_URL = "https://api.usaspending.gov"
SEARCH_URL = f"{BASE_URL}/api/v2/search/spending_by_transaction/"
COUNT_URL = f"{BASE_URL}/api/v2/search/spending_by_transaction_count/"

AGENCY_NAME = "General Services Administration"
AWARD_TYPE_CODES = ["A", "B", "C", "D"]  # prime contracts only (no IDVs/grants/loans)

FY_DATES = {
    2001: ("2000-10-01", "2001-09-30"),
    2006: ("2005-10-01", "2006-09-30"),
    2011: ("2010-10-01", "2011-09-30"),
    2016: ("2015-10-01", "2016-09-30"),
    2021: ("2020-10-01", "2021-09-30"),
    2026: ("2025-10-01", "2026-09-30"),
}
ALL_FYS = [2001, 2006, 2011, 2016, 2021, 2026]

# Minimal field set, every name verified live against the API 2026-09-13
# (invalid names return HTTP 400 with the full valid-values list).
# Substitutions vs. the wish list (documented, not silent):
#   - "Transaction Amount" IS the federal action obligation on this endpoint.
#   - "Current Award Amount / Total Obligated" UNAVAILABLE here -> aggregate
#     Transaction Amount per Award ID in analysis instead.
#   - "Extent Competed", "Type of Set Aside", "Number of Offers Received",
#     "Solicitation Procedures" UNAVAILABLE on spending_by_transaction (they
#     exist only in bulk-download exports) -> competition work uses Award Type
#     + Transaction Description text; flag sole-source limits in analysis.
#   - "NAICS" wish-list item split into exact "naics_code"+"naics_description".
FIELDS = [
    "Award ID",                      # PIID
    "Mod",                           # modification number
    "Recipient Name",                # vendor
    "Recipient UEI",                 # vendor UEI
    "Awarding Agency",               # = GSA
    "Awarding Sub Agency",           # sub-tier
    "Funding Agency",
    "Transaction Amount",            # federal action obligation
    "Action Date",
    "Action Type",
    "Award Type",                    # contract type grouping
    "naics_code",
    "naics_description",
    "product_or_service_code",
    "product_or_service_description",
    "Transaction Description",
    "generated_internal_id",         # dedup key
    "internal_id",                   # dedup key
]

PAGE_SIZE = 100  # API max (larger -> HTTP 422)
RESULT_CAP = 50000  # API hard cap: page*limit must stay <= 50,000 (else 422)
WINDOW_SAFE_MAX = 45000  # keep each sub-query below the cap with margin
TIMEOUT = 60
MAX_RETRIES = 6
RETRYABLE = {429, 500, 502, 503, 504}
PAGE_DELAY = 1.0  # politeness delay; raised after API 503 storms at 0.3s


def build_filters(fy: int) -> dict:
    start, end = FY_DATES[fy]
    return {
        "agencies": [{"type": "awarding", "tier": "toptier", "name": AGENCY_NAME}],
        "award_type_codes": list(AWARD_TYPE_CODES),
        "time_period": [{"start_date": start, "end_date": end}],
    }


def fy_windows(fy: int) -> list[tuple[str, str]]:
    """Split the FY into 7-day windows so every sub-query stays under the
    API's 50,000-result cap (GSA months run 78k-129k rows; weeks ~20-33k)."""
    start = dt.date.fromisoformat(FY_DATES[fy][0])
    end = dt.date.fromisoformat(FY_DATES[fy][1])
    windows = []
    cur = start
    while cur <= end:
        nxt = min(cur + dt.timedelta(days=6), end)
        windows.append((cur.isoformat(), nxt.isoformat()))
        cur = nxt + dt.timedelta(days=1)
    return windows


def window_filters(fy: int, start: str, end: str) -> dict:
    return {
        "agencies": [{"type": "awarding", "tier": "toptier", "name": AGENCY_NAME}],
        "award_type_codes": list(AWARD_TYPE_CODES),
        "time_period": [{"start_date": start, "end_date": end}],
    }


def truncate_torn_tail(dest: Path, fy: int) -> None:
    """Drop a partial last line left by a killed run.

    Complete csv rows always end in newline; a missing trailing newline
    means the run died mid-row. Bounded memory (scans back in blocks).
    """
    with open(dest, "r+b") as fh:
        fh.seek(0, 2)
        end = fh.tell()
        if not end:
            return
        fh.seek(end - 1)
        if fh.read(1) == b"\n":
            return
        pos = end - 1
        while pos > 0:
            blk = min(65536, pos)
            fh.seek(pos - blk)
            data = fh.read(blk)
            idx = data.rfind(b"\n")
            if idx != -1:
                fh.seek(pos - blk + idx + 1)
                fh.truncate()
                print(f"FY{fy}: dropped torn last line from killed run",
                      flush=True)
                return
            pos -= blk
        fh.seek(0)
        fh.truncate()


def load_metadata() -> dict:
    if META_PATH.exists():
        try:
            return json.loads(META_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def out_path(fy: int) -> Path:
    return RAW_DIR / f"GSA_FY{fy}.csv"


def post(session: requests.Session, url: str, payload: dict,
         stats: dict) -> requests.Response:
    """POST with retry on transient failures. Counts retries into stats."""
    delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.post(url, json=payload, timeout=TIMEOUT)
            if r.status_code in RETRYABLE:
                raise requests.HTTPError(f"retryable {r.status_code}")
            if 400 <= r.status_code < 500:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            return r
        except (requests.HTTPError, requests.ConnectionError,
                requests.Timeout) as exc:
            stats["retries"] += 1
            print(f"retry {attempt}/{MAX_RETRIES} "
                  f"({type(exc).__name__}: {exc})", flush=True)
            stats.setdefault("errors", []).append(
                f"{type(exc).__name__} attempt {attempt}: {exc}")
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"gave up after {MAX_RETRIES} tries: {exc}")
            time.sleep(min(delay, 60.0))
            delay *= 2


def fetch_page(session, filters, page, limit, stats):
    payload = {"filters": filters, "fields": FIELDS, "page": page,
               "limit": limit, "sort": "Transaction Amount", "order": "desc"}
    r = post(session, SEARCH_URL, payload, stats)
    body = r.json()
    return body.get("results", []), body.get("page_metadata", {}), len(r.content)


def get_count(session, filters, stats) -> int | None:
    try:
        r = post(session, COUNT_URL, {"filters": filters}, stats)
        return int(r.json()["results"]["contracts"])
    except Exception as exc:  # count is advisory only; never fatal
        stats.setdefault("errors", []).append(f"count failed: {exc}")
        return None


def run_test() -> None:
    """FAST TEST: FY2021, first 100 rows, no files written."""
    session = requests.Session()
    session.headers.update({"User-Agent": "federal-contract-analytics/0.1"})
    stats: dict = {"retries": 0}
    filters = build_filters(2021)
    t0 = time.time()
    rows, meta, nbytes = fetch_page(session, filters, 1, 100, stats)
    secs = time.time() - t0
    print(f"HTTP status   : 200 (ok, {secs:.1f}s)")
    print(f"Rows returned : {len(rows)}")
    print(f"Columns ({len(rows[0]) if rows else 0}): "
          f"{list(rows[0].keys()) if rows else []}")
    print(f"Response size : ~{nbytes / 1024:.1f} KiB")
    print(f"page_metadata : {meta}")
    print(f"Retries       : {stats['retries']}")
    for i, rec in enumerate(rows[:3]):
        print(f"--- record {i + 1} ---")
        for k, v in rec.items():
            print(f"  {k}: {v}")


def download_fy(fy: int, force: bool, budget_min: float | None = None) -> dict:
    """Full download for one FY, one 7-day window at a time.

    Windows keep every sub-query under the API's 50,000-result cap.
    All windows share one CSV + one global dedup set; completed windows are
    recorded in GSA_download_metadata.json so reruns skip finished work.
    If budget_min is set, stop cleanly after that many minutes (the next
    run resumes from the recorded completed windows).
    """
    dest = out_path(fy)
    dest.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "federal-contract-analytics/0.1"})
    stats: dict = {"retries": 0, "errors": []}
    t0 = time.time()
    windows = fy_windows(fy)
    key = f"GSA_FY{fy}"

    all_meta = load_metadata()
    saved = all_meta.get(key, {})
    done_windows: set = set(saved.get("completed_windows", []))

    seen: set = set()
    if dest.exists() and not force:
        truncate_torn_tail(dest, fy)
        with open(dest, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if (reader.fieldnames or []) != FIELDS:
                raise RuntimeError(
                    f"{dest.name} has unexpected columns; use --force to redo")
            for row in reader:
                seen.add((row.get("generated_internal_id"),
                          row.get("internal_id")))
        print(f"FY{fy}: {len(seen)} rows on disk, "
              f"{len(done_windows)}/{len(windows)} windows done", flush=True)
    else:
        if dest.exists():
            dest.unlink()
        done_windows = set()

    expected = get_count(session, build_filters(fy), stats)
    print(f"FY{fy}: expected ~{expected} rows across "
          f"{len(windows)} weekly windows", flush=True)

    with open(dest, "a" if dest.exists() else "w",
               encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if fh.tell() == 0:
            writer.writeheader()
        for start, end in windows:
            wlabel = f"{start}..{end}"
            if wlabel in done_windows:
                continue
            if (budget_min is not None
                    and (time.time() - t0) / 60.0 >= budget_min):
                print(f"FY{fy}: time budget ({budget_min} min) reached; "
                      f"stopping cleanly at "
                      f"{len(done_windows)}/{len(windows)} windows",
                      flush=True)
                break
            wf = window_filters(fy, start, end)
            wcount = get_count(session, wf, stats)
            if wcount is not None and wcount > WINDOW_SAFE_MAX:
                raise RuntimeError(
                    f"window {wlabel} has {wcount} rows, over safe max "
                    f"{WINDOW_SAFE_MAX}; split further before proceeding")
            page, wnew, pages = 1, 0, 0
            while True:
                payload = {"filters": wf, "fields": FIELDS, "page": page,
                           "limit": PAGE_SIZE, "sort": "Transaction Amount",
                           "order": "desc"}
                r = post(session, SEARCH_URL, payload, stats)
                body = r.json()
                rows = body.get("results", [])
                meta = body.get("page_metadata", {})
                if not rows:
                    break
                fresh = [x for x in rows
                         if (x.get("generated_internal_id"),
                             x.get("internal_id")) not in seen]
                for x in fresh:
                    seen.add((x.get("generated_internal_id"),
                              x.get("internal_id")))
                writer.writerows(
                    [{k: rec.get(k, "") for k in FIELDS} for rec in fresh])
                fh.flush()
                wnew += len(fresh)
                pages += 1
                if pages % 25 == 0 or not meta.get("hasNext"):
                    print(f"FY{fy} [{wlabel}]: page {pages}, +{wnew} new "
                          f"| total {len(seen)} | {time.time() - t0:.0f}s",
                          flush=True)
                page = meta.get("next") or (page + 1)
                if not meta.get("hasNext"):
                    break
                time.sleep(PAGE_DELAY)
            done_windows.add(wlabel)
            all_meta[key] = {"completed_windows": sorted(done_windows)}
            META_PATH.write_text(json.dumps(all_meta, indent=2),
                                 encoding="utf-8")
            print(f"FY{fy} [{wlabel}]: count~{wcount} +{wnew} new | "
                  f"total {len(seen)} | {len(done_windows)}/{len(windows)} "
                  f"windows | {time.time() - t0:.0f}s", flush=True)
            time.sleep(PAGE_DELAY)

    result = validate(dest, fy)
    result.update({
        "fiscal_year": fy,
        "date_range": {"start_date": FY_DATES[fy][0],
                       "end_date": FY_DATES[fy][1]},
        "agency": AGENCY_NAME,
        "filters": build_filters(fy),
        "fields_requested": list(FIELDS),
        "row_count": len(seen),
        "file_size_bytes": dest.stat().st_size,
        "download_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "api_endpoint": SEARCH_URL,
        "expected_from_count_api": expected,
        "fy2026_is_partial": fy == 2026,
        "retries": stats["retries"],
        "api_errors": stats.get("errors", []),
        "elapsed_seconds": round(time.time() - t0, 1),
        "completed_windows": sorted(done_windows),
        "window_count": len(windows),
        "complete": len(done_windows) == len(windows),
    })
    return result


def validate(dest: Path, fy: int) -> dict:
    """Lightweight checks: columns, dates, amounts, dups, missing rates."""
    required = ["Award ID", "Recipient Name", "Transaction Amount", "Action Date"]
    n, bad_date, bad_amt, dups = 0, 0, 0, 0
    seen: set = set()
    missing: dict = {}
    cols: list = []
    with open(dest, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames or [])
        for row in reader:
            n += 1
            key = (row.get("generated_internal_id"), row.get("internal_id"))
            if key in seen:
                dups += 1
            seen.add(key)
            try:
                dt.date.fromisoformat((row.get("Action Date") or "")[:10])
            except ValueError:
                bad_date += 1
            try:
                float((row.get("Transaction Amount") or "").replace(",", ""))
            except ValueError:
                bad_amt += 1
            for c in FIELDS:
                if not (row.get(c) or "").strip():
                    missing[c] = missing.get(c, 0) + 1
    print(f"FY{fy} validation: rows={n}, cols={len(cols)}, "
          f"bad_dates={bad_date}, bad_amounts={bad_amt}, dup_keys={dups}",
          flush=True)
    for c in required:
        if c not in cols:
            print(f"FY{fy} validation WARNING: required column missing: {c}")
    empty = [c for c in cols if missing.get(c, 0) == n and n > 0]
    if empty:
        print(f"FY{fy} validation WARNING: completely empty columns: {empty}")
    return {
        "actual_fields_returned": cols,
        "missing_value_rates": {c: round(missing.get(c, 0) / n, 6) if n else 0.0
                                for c in FIELDS},
        "unparseable_action_dates": bad_date,
        "unparseable_amounts": bad_amt,
        "duplicate_key_count": dups,
        "completely_empty_columns": empty,
    }


def save_metadata(entry: dict) -> None:
    all_meta: dict = {}
    if META_PATH.exists():
        try:
            all_meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            all_meta = {}
    all_meta[f"GSA_FY{entry['fiscal_year']}"] = entry
    META_PATH.write_text(json.dumps(all_meta, indent=2), encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="FAST GSA prime-contracts downloader")
    ap.add_argument("--test", action="store_true",
                    help="FY2021 first-100-rows test only, writes no files")
    ap.add_argument("--fy", default="2021",
                    help="2001|2006|2011|2016|2021|2026 or 'all'")
    ap.add_argument("--force", action="store_true",
                    help="redownload even if the CSV already exists")
    ap.add_argument("--time-budget", type=float, default=None, metavar="MIN",
                    help="stop cleanly after MIN minutes; rerun to resume")
    args = ap.parse_args(argv)

    if args.test:
        run_test()
        return

    fys = ALL_FYS if args.fy == "all" else [int(args.fy)]
    for fy in fys:
        if fy not in FY_DATES:
            sys.exit(f"FY must be one of {ALL_FYS}")
    for fy in fys:
        print(f"=== GSA FY{fy} ===", flush=True)
        entry = download_fy(fy, force=args.force, budget_min=args.time_budget)
        save_metadata(entry)
        state = "COMPLETE" if entry["complete"] else "PARTIAL (rerun to resume)"
        print(f"FY{fy} {state}: {entry['row_count']} rows, "
              f"{entry['file_size_bytes'] / 1024 / 1024:.1f} MiB, "
              f"retries={entry['retries']}", flush=True)


if __name__ == "__main__":
    main()
