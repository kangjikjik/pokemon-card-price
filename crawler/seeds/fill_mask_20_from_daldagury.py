"""변환의 가면부터 20개 한국판 세트의 달다구리 이미지 적용."""
from __future__ import annotations

import fill_mega_sets_from_daldagury as runner


runner.TARGETS = {
    "SV5K": 26,   # 변환의 가면
    "SV5M": 27,   # 크림슨헤이즈
    "SV4x": 278,  # 사이버저지
    "SV4": 277,   # 와일드포스
    "SV4a": 14,   # 샤이니 트레저 ex
    "SV4K": 276,  # 고대의 포효
    "SV4M": 15,   # 미래의 일섬
    "SV3a": 275,  # 레이징서프
    "SV3": 366,   # 흑염의 지배자
    "SV2a": 17,   # 포켓몬 카드 151
    "SV2D": 273,  # 클레이버스트
    "SV2P": 272,  # 스노해저드
    "SV1a": 271,  # 트리플렛 비트
    "SV1V": 270,  # 바이올렛 ex
    "SV1S": 269,  # 스칼렛 ex
    "S12a": 18,   # VSTAR 유니버스
    "S12": 268,   # 패러다임 트리거
    "S11a": 267,  # 백열의 아르카나
    "S11": 266,   # 로스트 어비스
    "S10b": 265,  # 다크 판타스마
}
runner.REPORT = runner.Path("_audit_out/mask_20_daldagury_apply.json")


if __name__ == "__main__":
    runner.main()
