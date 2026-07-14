-- 커뮤니티 v3: 공지(notice) 게시판
-- Supabase SQL Editor에서 실행하세요.

ALTER TABLE community_posts DROP CONSTRAINT IF EXISTS community_posts_board_check;
ALTER TABLE community_posts ADD CONSTRAINT community_posts_board_check
  CHECK (board IN ('notice', 'free', 'question', 'request', 'tips'));

CREATE INDEX IF NOT EXISTS idx_community_posts_notice_created
  ON community_posts(board, created_at DESC)
  WHERE board = 'notice';
