#!/usr/bin/env python3
"""로컬 /search 스모크 테스트. 서버 예: uvicorn backend.main:app --reload --port 8000"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    base = os.environ.get("SAMSUN_API", "http://127.0.0.1:8000").rstrip("/")
    q = os.environ.get("SEARCH_Q", "엔비디아 최신 GPU")
    url = f"{base}/search?q={urllib.parse.quote(q)}&top_k=10"
    r = requests.get(url, timeout=60)
    print("GET", url)
    print("status", r.status_code)
    try:
        data = r.json()
    except json.JSONDecodeError:
        print(r.text[:500])
        sys.exit(1)
    print("expanded_query:", data.get("expanded_query", "")[:240])
    n = len(data.get("results") or [])
    print("results:", n)
    if n:
        row = data["results"][0]
        print(
            "top1:",
            row.get("title_ko") or row.get("title"),
            "| sim=",
            row.get("similarity"),
        )


if __name__ == "__main__":
    main()
