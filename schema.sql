-- ============================================================
-- PokéPrice DB 스키마
-- Supabase 대시보드 > SQL Editor에서 전체 실행하세요.
-- ============================================================

-- 카드 세트(확장팩) 정보
CREATE TABLE IF NOT EXISTS card_sets (
  id          SERIAL PRIMARY KEY,
  set_code    VARCHAR(20) UNIQUE NOT NULL,
  name_kr     VARCHAR(100),
  name_jp     VARCHAR(100),
  name_en     VARCHAR(100),
  released_at DATE,
  image_url   TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- 개별 카드 정보
CREATE TABLE IF NOT EXISTS cards (
  id           SERIAL PRIMARY KEY,
  set_id       INTEGER REFERENCES card_sets(id),
  card_number  VARCHAR(20),
  name_kr      VARCHAR(100),
  name_jp      VARCHAR(100),
  name_en      VARCHAR(100),
  rarity       VARCHAR(30),
  rarity_rank  INTEGER DEFAULT 0,
  image_url    TEXT,
  image_color  VARCHAR(200),
  created_at   TIMESTAMP DEFAULT NOW()
);

-- 한국판 카드 시세 이력
CREATE TABLE IF NOT EXISTS prices_kr (
  id          SERIAL PRIMARY KEY,
  card_id     INTEGER REFERENCES cards(id),
  price_krw   INTEGER NOT NULL,
  source      VARCHAR(50),
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- 일본판 카드 시세 이력
CREATE TABLE IF NOT EXISTS prices_jp (
  id          SERIAL PRIMARY KEY,
  card_id     INTEGER REFERENCES cards(id),
  price_jpy   INTEGER NOT NULL,
  price_krw   INTEGER NOT NULL,
  source      VARCHAR(50),
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- 박스 시세 이력
CREATE TABLE IF NOT EXISTS prices_box (
  id          SERIAL PRIMARY KEY,
  set_id      INTEGER REFERENCES card_sets(id),
  region      VARCHAR(5) NOT NULL CHECK (region IN ('KR', 'JP')),
  price_krw   INTEGER NOT NULL,
  source      VARCHAR(50),
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- 환율 정보
CREATE TABLE IF NOT EXISTS exchange_rates (
  id          SERIAL PRIMARY KEY,
  jpy_to_krw  DECIMAL(10, 4) NOT NULL,
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 초기 Mock 데이터 삽입 (개발용)
-- ============================================================

-- 세트 데이터
INSERT INTO card_sets (set_code, name_kr, name_en, released_at) VALUES
  ('SV2a', '포켓몬 카드 151', 'Pokemon Card 151', '2023-07-28'),
  ('SV2D', '클레이버스트', 'Clay Burst', '2023-04-14'),
  ('S12a', 'VSTAR 유니버스', 'VSTAR Universe', '2022-12-02'),
  ('SV4a', '샤이니트레저 ex', 'Shiny Treasure ex', '2023-12-01')
ON CONFLICT (set_code) DO NOTHING;

-- 박스 시세 초기 데이터
INSERT INTO prices_box (set_id, region, price_krw, source)
SELECT id, 'KR', 65000, 'manual' FROM card_sets WHERE set_code = 'SV2a'
ON CONFLICT DO NOTHING;

INSERT INTO prices_box (set_id, region, price_krw, source)
SELECT id, 'JP', 140000, 'manual' FROM card_sets WHERE set_code = 'SV2a'
ON CONFLICT DO NOTHING;

-- 카드 데이터
INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '201/165', '리자몽 ex', 'Charizard ex', 'SAR', 6, 'from-orange-500 via-red-600 to-rose-700'
FROM card_sets WHERE set_code = 'SV2a';

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '208/165', '뮤 ex', 'Mew ex', 'UR', 7, 'from-fuchsia-500 via-purple-600 to-pink-500'
FROM card_sets WHERE set_code = 'SV2a';

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '173/165', '피카츄', 'Pikachu', 'AR', 4, 'from-yellow-300 via-yellow-400 to-amber-500'
FROM card_sets WHERE set_code = 'SV2a';

-- 초기 환율 데이터
INSERT INTO exchange_rates (jpy_to_krw) VALUES (9.50);

-- ============================================================
-- 조회 성능 최적화 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_prices_kr_card_id ON prices_kr(card_id);
CREATE INDEX IF NOT EXISTS idx_prices_kr_fetched ON prices_kr(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_prices_jp_card_id ON prices_jp(card_id);
CREATE INDEX IF NOT EXISTS idx_prices_jp_fetched ON prices_jp(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_prices_box_set_id ON prices_box(set_id);
CREATE INDEX IF NOT EXISTS idx_cards_set_id ON cards(set_id);
CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity);
