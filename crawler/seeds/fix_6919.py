#!/usr/bin/env python3
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase

def main():
    sb = get_supabase()
    # Remove the bad listing that set price_jpy=53 (id=20159)
    target_id = 20159
    print("Deleting prices_jp row id =", target_id)
    res = sb.table("prices_jp").delete().eq("id", target_id).execute()
    print("delete error:", getattr(res, "error", None))
    print("deleted rows count (response):", len(res.data or []))
    # show latest entries after deletion
    res2 = sb.table("prices_jp").select("*").eq("card_id", 6919).order("fetched_at", desc=True).limit(10).execute()
    print(json.dumps({"count": len(res2.data or []), "data": res2.data or []}, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    main()
