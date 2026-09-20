"""남은 23개 한국판 세트의 달다구리 이미지 적용."""
from __future__ import annotations

import fill_mega_sets_from_daldagury as runner


runner.TARGETS = {
    "S3Z": 253,  # 무한존
    "S2R": 252,  # 폭염워커
    "S2": 331,  # 반역크래시
    "S1a": 251,  # VMAX라이징
    "S1W": 249,  # 소드
    "S1H": 250,  # 실드
    "SM12a": 324,  # TAG TEAM GX 태그올스타즈
    "SM12": 248,  # 얼터제네시스
    "SM11b": 247,  # 드림리그
    "SM11a": 246,  # 미라클트윈
    "SM10": 37,  # 더블블레이즈
    "SM9": 315,  # 나이트유니슨
    "SM8b": 314,  # GX 울트라샤이니
    "SM9a": 313,  # 태그볼트
    "SM8": 310,  # 플라스마 스파크
    "SM7": 240,  # 버스트임팩트
    "SM6b": 36,  # 창공의 카리스마
    "SM6a": 238,  # 챔피언로드
    "SM6": 307,  # 드래곤스톰
    "SM5+": 237,  # 금단의 빛
    "SM5": 236,  # 울트라포스
    "SM4+": 306,  # 울트라문
    "SM4": 305,  # 울트라썬
}
runner.REPORT = runner.Path("_audit_out/final_23_daldagury_apply.json")


if __name__ == "__main__":
    runner.main()
