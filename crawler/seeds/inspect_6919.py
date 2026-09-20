#!/usr/bin/env python3
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase

def main():
    sb = get_supabase()
    card_id = 6919
    res = sb.table("prices_jp").select("*").eq("card_id", card_id).order("fetched_at", desc=True).limit(50).execute()
    out = {
        "error": getattr(res, "error", None),
        "count": len(res.data or []),
        "data": res.data or [],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    main()
