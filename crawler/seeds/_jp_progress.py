"""JP 시세 진행 현황."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kr_sets import KR_SETS
from lib.yuyutei_prices import YUYU_VERS

DONE = {
    "MG6", "MG5a", "MG5", "MG4a", "MG4", "MG3a", "MG3", "MG2a", "MG2",
    "MG1b", "MG1a", "SV8a", "SV8", "SV7", "SV6a", "SV6", "SV5a", "SV5K",
    "SV5M", "SV4x", "SV4", "SV4a", "SV4K",
    "SV4M", "SV3a", "SV3", "SV2a", "SV2D",
    "SV2P", "SV1a", "SV1V", "SV1S", "S12a",
    "S12", "S11a", "S11", "S10b", "S10a",
    "S9a", "S9", "S8", "S8a", "S8b",
    "S7F", "CEL", "S7R", "S7D", "S6H",
    "S6G", "S6L", "S5F", "S5S", "S5P",
    "S4SV", "S4B", "S3H", "S3Z", "S2R",
    "S2", "S1a", "S1W", "S1H", "SM12a",
    "SM12", "SM11b", "SM11a", "SM10", "SM9",
    "SM8b", "SM9a", "SM8", "SM7", "SM6b",
    "SM6a", "SM6", "SM5+", "SM5", "SM4+", "SM4",
}

all_codes = [s.code for s in KR_SETS]
remaining = [c for c in all_codes if c not in DONE]
mapped = [c for c in remaining if c in YUYU_VERS]
unmapped = [c for c in remaining if c not in YUYU_VERS]

print(f"전체 featured: {len(all_codes)}팩")
print(f"완료: {len(DONE)}팩")
print(f"남음: {len(remaining)}팩 (vers 매핑 {len(mapped)} / 미매핑 {len(unmapped)})")
if remaining:
    print("다음:", ", ".join(remaining[:10]), ("..." if len(remaining) > 10 else ""))
