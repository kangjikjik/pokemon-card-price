"""Apply add_card_views.sql via Supabase REST (run once)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "crawler"))

for env_path in (ROOT / "web" / ".env.local", ROOT / "crawler" / "seeds" / ".env"):
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from utils.db import get_supabase

sb = get_supabase()

try:
    sb.table("cards").select("view_count").limit(1).execute()
    print("view_count column already exists")
except Exception as e:
    print("view_count missing — add via Supabase SQL Editor:", ROOT / "add_card_views.sql")
    print(e)
