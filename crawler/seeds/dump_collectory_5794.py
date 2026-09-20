#!/usr/bin/env python3
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from lib.collectory_public import TR_ROW_RE, _parse_transaction_row_jp

CID = "08fe6cec-d1bb-4e65-9ac3-55adfa8084e8"
URL = f"https://collectory.cc/cards/{CID}"


def main() -> None:
    client = httpx.Client(timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    res = client.get(URL)
    html = res.text
    out_dir = os.path.join(os.path.dirname(__file__), "_audit_out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "collectory_5794.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("status", res.status_code, "bytes", len(html), "saved", path)

    rows = TR_ROW_RE.findall(html)
    print("tr_count", len(rows))
    parsed = []
    for i, row in enumerate(rows):
        q = _parse_transaction_row_jp(row)
        if q:
            parsed.append((i, q))
    print("parsed_count", len(parsed))
    for i, q in parsed:
        print(i, q.tier, q.source, q.price_krw, (q.title or "")[:120])

    if "SNKRDUNK" in html:
        print("html_contains_SNKRDUNK", True)
        for m in re.finditer(r".{0,80}SNKRDUNK.{0,120}", html):
            print("context:", m.group(0).replace("\n", " ")[:200])
    else:
        print("html_contains_SNKRDUNK", False)

    for token in ("Transactions", "체결", "거래", "sold", "호가", "listing"):
        print(f"contains_{token}", token in html)

    client.close()


if __name__ == "__main__":
    main()
