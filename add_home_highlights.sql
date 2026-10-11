-- 카드·세트(박스) 조회를 날짜별로 쌓고, 크롤이 홈 순서를 여기에 적는다.
-- Supabase SQL Editor에서 한 번 실행.

ALTER TABLE cards
  ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_cards_view_count ON cards (view_count DESC);

CREATE TABLE IF NOT EXISTS card_view_days (
  card_id    INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  view_date  DATE NOT NULL,
  view_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (card_id, view_date)
);

CREATE TABLE IF NOT EXISTS set_view_days (
  set_id     INTEGER NOT NULL REFERENCES card_sets(id) ON DELETE CASCADE,
  view_date  DATE NOT NULL,
  view_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (set_id, view_date)
);

CREATE INDEX IF NOT EXISTS idx_card_view_days_date ON card_view_days (view_date);
CREATE INDEX IF NOT EXISTS idx_set_view_days_date ON set_view_days (view_date);

-- kind: hot_card | trending_card | featured_set
CREATE TABLE IF NOT EXISTS home_highlights (
  kind         TEXT NOT NULL,
  rank         INTEGER NOT NULL,
  card_id      INTEGER REFERENCES cards(id) ON DELETE CASCADE,
  set_id       INTEGER REFERENCES card_sets(id) ON DELETE CASCADE,
  view_count   INTEGER NOT NULL DEFAULT 0,
  period_start DATE NOT NULL,
  period_end   DATE NOT NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (kind, rank)
);

ALTER TABLE card_view_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE set_view_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE home_highlights ENABLE ROW LEVEL SECURITY;
