"""번역 실패 샘플 디버그"""
import json
from pathlib import Path
import sys
sys.path.insert(0, ".")
from seeds.update_kr_from_jp import translate_name, translate_en_name, fetch_pokemon_names, fetch_en_to_kr

jp = fetch_pokemon_names()
en = fetch_en_to_kr()

samples = [
    "フシギバナex", "リザードンex", "ナンジャモのハラバリーex",
    "メガユキメノコex", "Yveltal", "Amarys", "ジャッジマン",
]
for s in samples:
    kr_jp = translate_name(s, jp)
    kr_en = translate_en_name(s, en)
    print(f"{s:30} jp->{kr_jp or 'FAIL':20} en->{kr_en or 'FAIL'}")
