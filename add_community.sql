-- 커뮤니티 게시판 (자유 / 질문 / 추가 요청)
-- Supabase SQL Editor에서 실행하세요.

CREATE TABLE IF NOT EXISTS community_posts (
  id          SERIAL PRIMARY KEY,
  board       VARCHAR(20) NOT NULL CHECK (board IN ('free', 'question', 'request')),
  title       VARCHAR(200) NOT NULL,
  content     TEXT NOT NULL,
  author_name VARCHAR(30) NOT NULL,
  view_count  INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_posts_board_created
  ON community_posts(board, created_at DESC);

-- API는 service role로 쓰기, 읽기는 공개
ALTER TABLE community_posts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS community_posts_select ON community_posts;
CREATE POLICY community_posts_select ON community_posts
  FOR SELECT USING (true);
