#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///
"""Fetch IBKR Flex Query report via the Flex Web Service API.

Usage:
    uv run fetch_ibkr.py --token TOKEN --query-id ID [--out PATH]

Two-step:
  1. SendRequest with token + query_id → reference code
  2. GetStatement with token + reference code → CSV data
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path
from xml.etree import ElementTree

import requests

SEND_URL = (
    "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
)
GET_URL = (
    "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"
)


_NETWORK_ERRORS = (requests.ConnectionError, requests.Timeout)


def _backoff(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    delay = min(base * (2**attempt), cap)
    return delay + random.uniform(0, delay * 0.5)


def _log(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr)


def _get_with_retry(
    url: str,
    params: dict[str, str],
    max_attempts: int = 5,
) -> requests.Response:
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, params=params, timeout=30)
        except _NETWORK_ERRORS:
            wait = _backoff(attempt)
            _log(f"connection failed, retrying in {wait:.1f}s...")
            time.sleep(wait)
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            wait = _backoff(attempt)
            _log(f"server {resp.status_code}, retrying in {wait:.1f}s...")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        return resp

    _log("all retries exhausted")
    sys.exit(1)


_RETRYABLE_CODES = {"1018", "1019", "1021"}


def request_report(token: str, query_id: str) -> str:
    resp = _get_with_retry(SEND_URL, {"t": token, "q": query_id, "v": "3"})
    root = ElementTree.fromstring(resp.text)

    code = root.findtext("ErrorCode") or ""
    if code in _RETRYABLE_CODES:
        _log(f"rate limited ({code}), waiting 60s...")
        time.sleep(60)
        return request_report(token, query_id)

    if root.findtext("Status") != "Success":
        _log(f"error: {root.findtext('ErrorMessage') or resp.text}")
        sys.exit(1)

    ref_code = root.findtext("ReferenceCode")
    if not ref_code:
        _log(f"error: no reference code: {resp.text}")
        sys.exit(1)

    return ref_code


def fetch_report(token: str, ref_code: str, max_polls: int = 20) -> str:
    params = {"t": token, "q": ref_code, "v": "3"}

    for poll in range(max_polls):
        resp = _get_with_retry(GET_URL, params)

        if "<FlexStatementResponse" not in resp.text[:500]:
            return resp.text

        root = ElementTree.fromstring(resp.text)
        code = root.findtext("ErrorCode") or ""
        msg = root.findtext("ErrorMessage") or ""

        if code in _RETRYABLE_CODES or "try again" in msg.lower():
            wait = _backoff(poll, base=5.0, cap=30.0)
            _log(f"generating... {poll + 1}/{max_polls}, {wait:.1f}s")
            time.sleep(wait)
            continue

        _log(f"error ({code}): {msg or resp.text}")
        sys.exit(1)

    _log("report not ready after polling")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch IBKR Flex Query report")
    parser.add_argument("--token", required=True)
    parser.add_argument("--query-id", required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    _log("requesting report...")
    ref_code = request_report(args.token, args.query_id)
    _log(f"reference: {ref_code}, waiting for generation...")
    time.sleep(15)

    csv_data = fetch_report(args.token, ref_code)

    if args.out:
        args.out.write_text(csv_data)
        _log(f"saved to {args.out}")
    else:
        print(csv_data, end="")


if __name__ == "__main__":
    main()
