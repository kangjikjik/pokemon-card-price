"""
커뮤니티 게시판 테이블 생성 안내 + 연결 확인.

실행: python setup_community_db.py
      python setup_community_db.py --check
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

SQL_PATH = Path(__file__).resolve().parents[2] / "add_community.sql"
SQL_V2_PATH = Path(__file__).resolve().parents[2] / "add_community_v2.sql"


def main() -> int:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY 필요 (crawler/.env)")
        return 1

    sb = create_client(url, key)
    try:
        sb.table("community_posts").select("id, edit_token, like_count").limit(1).execute()
        print("OK community_posts 테이블 존재")
        try:
            sb.table("community_post_likes").select("post_id").limit(1).execute()
            print("OK community_post_likes 테이블 존재 (v2)")
        except Exception:
            print("WARN community_post_likes 없음 → add_community_v2.sql 실행 필요")
            print(f"  {SQL_V2_PATH}")
            if SQL_V2_PATH.is_file():
                print()
                print("--- add_community_v2.sql ---")
                print(SQL_V2_PATH.read_text(encoding="utf-8"))
            return 1
        return 0
    except Exception as e:
        msg = str(e)
        if "community_posts" not in msg and "PGRST205" not in msg:
            print("오류:", e)
            return 1

    print("community_posts 테이블이 없습니다.")
    print()
    print("Supabase 대시보드 → SQL Editor 에서 아래 파일 내용을 실행하세요:")
    print(f"  {SQL_PATH}")
    print()
    if SQL_PATH.is_file():
        print("--- add_community.sql ---")
        print(SQL_PATH.read_text(encoding="utf-8"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
