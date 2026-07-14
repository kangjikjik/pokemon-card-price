"""S2R 이전(또는 직후 갭) — 2배치 15팩 후보 선정"""
from __future__ import annotations

import httpx

from analyze_timeline_gaps import MIN_CARDS, SKIP, eligible, norm
from gap_sets import CODE_BY_NAME
from kr_sets import FEATURED_SET_CODES, KR_BY_CODE

# S2R 직전~이전 구간: collectory 발매일 기준 S2R(2020-06-16) 이하 또는 직후 갭
S2R_DATE = KR_BY_CODE["S2R"].released_at


def main():
    # featured에 없는 eligible 중 S2R 이전(발매일 <= S2R) 또는 S2R~S3Z 사이 갭
    s3z_date = KR_BY_CODE["S3Z"].released_at
    candidates = []
    for e in eligible:
        name = e.get("name_ko") or ""
        if name not in CODE_BY_NAME:
            continue
        code, name_kr = CODE_BY_NAME[name]
        date = e.get("release_date_ko") or ""
        # S2R보다 이전이거나, S2R~S3Z 사이 빈틈
        if date <= S2R_DATE or (S2R_DATE < date < s3z_date):
            candidates.append({
                "code": code,
                "name_kr": name_kr,
                "collectory_date": date,
                "bs_code": e.get("set_code_ko", ""),
                "collectory_id": e["id"],
                "card_count": e["card_count"],
                "image_url": e.get("image_url") or "",
            })

    # 발매일 최신순 (S2R에 가까운 것부터)
    candidates.sort(key=lambda x: x["collectory_date"], reverse=True)
    batch = candidates[:15]

    print(f"S2R={S2R_DATE} S3Z={s3z_date}")
    print(f"candidates total={len(candidates)} batch2={len(batch)}")
    print()
    for i, c in enumerate(batch, 1):
        print(
            f"{i:2}. {c['code']:6} {c['collectory_date']:12} {c['name_kr'][:24]:24} "
            f"cards={c['card_count']:3} {c['bs_code']:14} {c['collectory_id']}"
        )


if __name__ == "__main__":
    main()
