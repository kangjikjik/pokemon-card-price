"""스톰에메랄다부터 전설의 고동까지 20개 세트의 한국판 이미지를 적용한다."""
from __future__ import annotations

import fill_mega_sets_from_daldagury as runner


runner.TARGETS = {
    "MG7": 2744,  # 스톰에메랄다
    "S10a": 264,  # Pokémon GO
    "S9a": 354,  # 타임 게이저
    "S9": 263,  # 스페이스 저글러
    "S8": 262,  # 배틀 리전
    "S8a": 261,  # 스타버스
    "S8b": 260,  # VMAX 클라이맥스
    "S7F": 350,  # 퓨전아츠
    "CEL": 2393,  # 25주년 기념 컬렉션
    "S7R": 20,  # 창공스트림
    "S7D": 344,  # 마천퍼펙트
    "S6H": 342,  # 이브이 히어로즈
    "S6G": 256,  # 칠흑의 가이스트
    "S6L": 340,  # 백은의 랜스
    "S5F": 255,  # 쌍벽의 파이터
    "S5S": 338,  # 일격마스터
    "S5P": 339,  # 연격마스터
    "S4SV": 337,  # 샤이니스타 V
    "S4B": 21,  # 앙천의 볼트태클
    "S3H": 254,  # 전설의 고동
}
runner.REPORT = runner.Path("_audit_out/legacy_20_daldagury_apply.json")


if __name__ == "__main__":
    runner.main()
