"""collectory.cc 세트 ID — kr_sets 마스터 기준"""

from kr_sets import COLLECTORY_IDS

COLLECTORY_SETS: dict[str, dict[str, str]] = {
    code: {"id": cid} for code, cid in COLLECTORY_IDS.items()
}

COLLECTORY_API = "https://collectory.cc/api"
