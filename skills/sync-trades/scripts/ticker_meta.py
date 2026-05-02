#!/usr/bin/env python3
"""SPDX-License-Identifier: GPL-3.0-only"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lafmm.init import HUMAN_DATA, get_root
from lafmm.meta import ensure_ticker_meta


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch cached ticker metadata")
    parser.add_argument("symbols", nargs="+", help="ticker symbols to look up")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def _resolve_data_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    root = get_root()
    if root is None:
        print("error: lafmm not initialized. Run 'lafmm' first.", file=sys.stderr)
        sys.exit(1)
    return root / HUMAN_DATA


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    data_dir = _resolve_data_dir(args.data_dir)

    results = []
    for symbol in args.symbols:
        meta = ensure_ticker_meta(data_dir, symbol.upper())
        if meta is None:
            print(f"{symbol.upper()}: no data from yfinance", file=sys.stderr)
            continue
        results.append(meta)

    if not results:
        sys.exit(1)

    if args.json:
        from dataclasses import asdict

        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for meta in results:
            print(
                f"{meta.symbol:<6} "
                f"{meta.identity.sector} / {meta.identity.industry} "
                f"({meta.identity.quote_type})"
            )


if __name__ == "__main__":
    main()
