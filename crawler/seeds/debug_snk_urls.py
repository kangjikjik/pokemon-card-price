"""Collectory SNKRDUNK URL 패턴 확인."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv
from lib.collectory_jp import build_jp_card_id_map
from utils.db import get_supabase

load_dotenv()
sb = get_supabase()

# MG6 제라오라 SAR
card = sb.table("cards").select("id,name_jp,rarity,card_number").eq("id", 3957).single().execute().data
client = httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"})
col_map = build_jp_card_id_map([card], client)
col_id = list(col_map.values())[0] if col_map else None
print("col_id", col_id)

if col_id:
    html = client.get(f"https://collectory.cc/cards/{col_id}").text
    snk_urls = re.findall(r'href="([^"]*snkrdunk[^"]*)"', html, re.I)
    print("snk_urls count", len(snk_urls))
    for u in snk_urls[:8]:
        print(" ", u)

    for m in re.finditer(r"<tr[^>]*>.*?SNKRDUNK.*?</tr>", html, re.DOTALL | re.I):
        row = m.group(0)
        hrefs = re.findall(r'href="([^"]+)"', row)
        text = re.sub(r"<[^>]+>", "|", row)
        text = re.sub(r"\|+", "|", text)
        print("row hrefs", hrefs)
        print("row text", text[:250])
        break

client.close()
