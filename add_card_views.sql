-- 카드 상세 조회(시세 확인) 횟수 — 인기순·주간 핫카드 집계용
-- Supabase SQL Editor에서 실행

ALTER TABLE cards
  ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_cards_view_count ON cards (view_count DESC);
