-- ============================================================
-- 추가 인기 카드 데이터
-- Supabase > SQL Editor 에서 실행하세요
-- ============================================================

-- 추가 세트 등록
INSERT INTO card_sets (set_code, name_kr, name_en, released_at) VALUES
  ('S11',  '로스트어비스',    'Lost Abyss',       '2022-07-15'),
  ('S12',  '패러다임트리거',  'Paradigm Trigger',  '2022-10-21'),
  ('SV3a', '포켓몬카드151 (재판)', 'Pokemon Card 151 Reprint', '2024-01-01')
ON CONFLICT (set_code) DO NOTHING;

-- ============================================================
-- 포켓몬 카드 151 (SV2a) 추가 카드
-- ============================================================
INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '207/165', '뮤 ex (SAR)', 'Mew ex SAR', 'SAR', 6, 'from-pink-400 via-fuchsia-500 to-purple-600'
FROM card_sets WHERE set_code = 'SV2a'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '190/165', '리자몽 ex (SR)', 'Charizard ex SR', 'SR', 5, 'from-orange-400 via-red-500 to-rose-600'
FROM card_sets WHERE set_code = 'SV2a'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '163/165', '이상해꽃 ex', 'Venusaur ex', 'RR', 3, 'from-green-400 via-emerald-500 to-teal-600'
FROM card_sets WHERE set_code = 'SV2a'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '165/165', '거북왕 ex', 'Blastoise ex', 'RR', 3, 'from-blue-400 via-cyan-500 to-sky-600'
FROM card_sets WHERE set_code = 'SV2a'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 클레이버스트 (SV2D) - 이온 SAR
-- ============================================================
INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '096/071', '이온', 'Iono', 'SAR', 6, 'from-lime-400 via-emerald-500 to-teal-600'
FROM card_sets WHERE set_code = 'SV2D'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '090/071', '이온 (SR)', 'Iono SR', 'SR', 5, 'from-lime-300 via-green-400 to-emerald-500'
FROM card_sets WHERE set_code = 'SV2D'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 로스트어비스 (S11) - 기라티나 V, SA
-- ============================================================
INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '131/100', '기라티나 VSTAR', 'Giratina VSTAR', 'SSR', 7, 'from-slate-700 via-indigo-800 to-purple-900'
FROM card_sets WHERE set_code = 'S11'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '111/100', '기라티나 V', 'Giratina V', 'SA', 8, 'from-slate-800 via-violet-900 to-purple-950'
FROM card_sets WHERE set_code = 'S11'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '105/100', '미라이돈 ex', 'Miraidon ex', 'SR', 5, 'from-yellow-400 via-amber-500 to-orange-600'
FROM card_sets WHERE set_code = 'S11'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 패러다임트리거 (S12) - 루기아 V, SA
-- ============================================================
INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '137/098', '루기아 VSTAR', 'Lugia VSTAR', 'SSR', 7, 'from-blue-300 via-indigo-400 to-purple-500'
FROM card_sets WHERE set_code = 'S12'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '110/098', '루기아 V', 'Lugia V', 'SA', 8, 'from-blue-400 via-blue-600 to-indigo-700'
FROM card_sets WHERE set_code = 'S12'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 샤이니트레저 ex (SV4a) - 인기 카드
-- ============================================================
INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '201/190', '파오리 ex', 'Palafin ex', 'SAR', 6, 'from-cyan-400 via-blue-500 to-indigo-600'
FROM card_sets WHERE set_code = 'SV4a'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '233/190', '리자몽 ex (SAR)', 'Charizard ex SAR', 'SAR', 6, 'from-red-500 via-orange-600 to-amber-700'
FROM card_sets WHERE set_code = 'SV4a'
ON CONFLICT DO NOTHING;

INSERT INTO cards (set_id, card_number, name_kr, name_en, rarity, rarity_rank, image_color)
SELECT id, '237/190', '뮤 ex (UR)', 'Mew ex UR', 'UR', 7, 'from-fuchsia-400 via-pink-500 to-rose-600'
FROM card_sets WHERE set_code = 'SV4a'
ON CONFLICT DO NOTHING;

SELECT COUNT(*) AS total_cards FROM cards;
