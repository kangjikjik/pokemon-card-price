"""블랙볼트부터 10개 한국판 세트의 달다구리 이미지 적용."""
from __future__ import annotations

import fill_mega_sets_from_daldagury as runner


runner.TARGETS = {
    "MG2": 16,    # 블랙볼트
    "MG2a": 7,    # 화이트플레어
    "MG1b": 8,    # 로켓단의 영광
    "MG1a": 281,  # 열풍의 아레나
    "SV8a": 380,  # 배틀파트너즈
    "SV8": 378,   # 테라스탈 페스타 ex
    "SV7": 11,    # 초전브레이커
    "SV6a": 280,  # 낙원드래고나
    "SV6": 374,   # 스텔라미라클
    "SV5a": 279,  # 나이트원더러
}
runner.REPORT = runner.Path("_audit_out/blackbolt_10_daldagury_apply.json")


if __name__ == "__main__":
    runner.main()
