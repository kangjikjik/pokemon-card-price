"""Apply aggressive proposals: update DB name_kr and image_url from proposals (safe apply)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()
from utils.db import get_supabase
from kr_sets import KR_SETS

PROPOSAL = Path("_audit_out/aggressive_proposals.json")
OUT = Path("_audit_out/aggressive_applied.json")


def find_set_by_name(name_kr: str):
    for s in KR_SETS:
        if s.name_kr == name_kr or name_kr in s.name_kr:
            return s
    return None


def normalize_printed(p: str) -> str:
    # return number portion before slash
    return p.split("/")[0]


def apply_one(sb, s, printed, candidate) -> dict | None:
    if not candidate:
        return None
    set_row = sb.table("card_sets").select("id,set_code").eq("set_code", s.code).single().execute().data
    if not set_row:
        return None
    set_id = set_row["id"]
    num = normalize_printed(printed)
    # try exact card_number starting with num + '/'
    q1 = sb.table("cards").select("id,card_number,name_kr,image_url").eq("set_id", set_id).like("card_number", f"{num}/%").execute().data or []
    q = q1 or sb.table("cards").select("id,card_number,name_kr,image_url").eq("set_id", set_id).ilike("card_number", f"%{num}%").execute().data or []
    if not q:
        return {"set": s.name_kr, "printed": printed, "status": "not_found"}
    # pick best candidate: if single, use it, else try match rarity/name later — for now pick first
    db = q[0]
    payload = {}
    new_name = (candidate.get("name_kr") or "").strip()
    new_img = (candidate.get("image_url") or "").split("?")[0]
    old_name = (db.get("name_kr") or "").strip()
    old_img = (db.get("image_url") or "").split("?")[0]
    if new_name and new_name != old_name:
        payload["name_kr"] = new_name
    if new_img and new_img != old_img:
        payload["image_url"] = new_img
    if not payload:
        return {"set": s.name_kr, "printed": printed, "status": "no_change"}
    sb.table("cards").update(payload).eq("id", db["id"]).execute()
    out = {"set": s.name_kr, "printed": printed, "card_id": db["id"], "changes": payload}
    return out


def main():
    if not PROPOSAL.exists():
        print("proposal file missing", PROPOSAL)
        return
    data = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    props = data.get("proposals", [])
    sb = get_supabase()
    applied = []
    for p in props:
        set_name = p.get("set")
        printed = p.get("printed")
        candidate = p.get("candidate")
        s = find_set_by_name(set_name)
        if not s:
            applied.append({"set": set_name, "printed": printed, "status": "set_not_found"})
            continue
        res = apply_one(sb, s, printed, candidate)
        applied.append(res or {"set": set_name, "printed": printed, "status": "skipped"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"applied": applied, "count": sum(1 for r in applied if r and r.get("changes"))}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "count", sum(1 for r in applied if r and r.get("changes")))


if __name__ == "__main__":
    main()

