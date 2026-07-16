"""Push crawler/.env Supabase vars to GitHub Actions secrets."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def normalize(value: str) -> str:
    return value.strip().strip('"').strip("'")


def validate(url: str, key: str) -> None:
    if not url or not key:
        raise ValueError("SUPABASE_URL 또는 SUPABASE_SERVICE_KEY가 비어 있습니다.")
    if not url.startswith("https://") or ".supabase.co" not in url:
        raise ValueError(
            "SUPABASE_URL 형식이 잘못되었습니다. "
            "https://YOUR_PROJECT.supabase.co 형태여야 합니다."
        )
    if len(key) < 20:
        raise ValueError("SUPABASE_SERVICE_KEY가 너무 짧습니다.")


def read_env(name: str) -> str:
    text = ENV_PATH.read_text(encoding="utf-8")
    m = re.search(r"^" + re.escape(name) + r"=(.*)$", text, re.M)
    if not m:
        return ""
    return normalize(m.group(1))


def set_secret(name: str, value: str) -> None:
    if not value:
        print(f"skip {name} (empty)")
        return
    subprocess.run(
        ["gh", "secret", "set", name, "--body", value],
        check=True,
    )
    print(f"set {name} (len={len(value)})")


def check_only() -> int:
    url = normalize(os.environ.get("SUPABASE_URL", ""))
    key = normalize(os.environ.get("SUPABASE_SERVICE_KEY", ""))
    try:
        validate(url, key)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print(f"ok SUPABASE_URL len={len(url)} key len={len(key)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate env vars already present in the process environment",
    )
    args = parser.parse_args()
    if args.check_only:
        return check_only()

    url = read_env("SUPABASE_URL")
    key = read_env("SUPABASE_SERVICE_KEY")
    cookie = read_env("COLLECTORY_COOKIE")

    try:
        validate(url, key)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    set_secret("SUPABASE_URL", url)
    set_secret("SUPABASE_SERVICE_KEY", key)
    set_secret("COLLECTORY_COOKIE", cookie)

    subprocess.run(["gh", "secret", "list"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
