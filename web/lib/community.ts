import { HelpCircle, Lightbulb, Megaphone, MessageSquare, Sparkles, type LucideIcon } from 'lucide-react';

export const BOARD_SLUGS = ['notice', 'free', 'question', 'request', 'tips'] as const;
export type BoardSlug = (typeof BOARD_SLUGS)[number];

export type CommunityPost = {
  id: number;
  board: BoardSlug;
  title: string;
  content: string;
  author_name: string;
  view_count: number;
  like_count: number;
  created_at: string;
  updated_at?: string | null;
};

export type BoardMeta = {
  slug: BoardSlug;
  label: string;
  description: string;
  icon: LucideIcon;
  accent: string;
};

export const BOARDS: Record<BoardSlug, BoardMeta> = {
  notice: {
    slug: 'notice',
    label: '공지',
    description: '서비스 공지와 업데이트 소식을 확인하세요.',
    icon: Megaphone,
    accent: 'from-rose-500 to-red-600',
  },
  free: {
    slug: 'free',
    label: '자유게시판',
    description: '카드 수집·거래 이야기 등 자유롭게 나눠 보세요.',
    icon: MessageSquare,
    accent: 'from-blue-500 to-indigo-600',
  },
  question: {
    slug: 'question',
    label: '질문게시판',
    description: '시세·카드·세트에 대한 궁금한 점을 물어보세요.',
    icon: HelpCircle,
    accent: 'from-emerald-500 to-teal-600',
  },
  request: {
    slug: 'request',
    label: '추가 요청게시판',
    description: '세트·기능·데이터 추가 요청을 남겨 주세요.',
    icon: Lightbulb,
    accent: 'from-amber-500 to-orange-600',
  },
  tips: {
    slug: 'tips',
    label: '꿀팁 게시판',
    description: '수집·시세·거래 꿀팁을 공유하고 따봉으로 추천해 보세요.',
    icon: Sparkles,
    accent: 'from-violet-500 to-purple-600',
  },
};

export function isBoardSlug(value: string): value is BoardSlug {
  return (BOARD_SLUGS as readonly string[]).includes(value);
}

export function formatPostDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const POST_SELECT_FIELDS =
  'id, board, title, content, author_name, view_count, like_count, created_at, updated_at';
