-- 커뮤니티 v2: 꿀팁 게시판, 수정/삭제 토큰, 따봉
-- Supabase SQL Editor에서 실행하세요. (add_community.sql 실행 후)

-- 꿀팁(tips) 보드 허용
ALTER TABLE community_posts DROP CONSTRAINT IF EXISTS community_posts_board_check;
ALTER TABLE community_posts ADD CONSTRAINT community_posts_board_check
  CHECK (board IN ('free', 'question', 'request', 'tips'));

-- 수정/삭제용 토큰 (API에서 발급, 클라이언트 localStorage 보관)
ALTER TABLE community_posts
  ADD COLUMN IF NOT EXISTS edit_token UUID,
  ADD COLUMN IF NOT EXISTS like_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- 꿀팁 게시판 추천순 정렬용
CREATE INDEX IF NOT EXISTS idx_community_posts_tips_likes
  ON community_posts(board, like_count DESC, created_at DESC)
  WHERE board = 'tips';

-- 따봉 중복 방지 (브라우저 voter_key 기준)
CREATE TABLE IF NOT EXISTS community_post_likes (
  post_id   INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
  voter_key VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (post_id, voter_key)
);

ALTER TABLE community_post_likes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS community_post_likes_select ON community_post_likes;
CREATE POLICY community_post_likes_select ON community_post_likes
  FOR SELECT USING (true);
