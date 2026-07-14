const POST_TOKENS_KEY = 'community_post_tokens';
const VOTER_KEY = 'community_voter_key';
const ADMIN_TOKEN_KEY = 'community_admin_token';

type TokenMap = Record<string, string>;

function readTokens(): TokenMap {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(POST_TOKENS_KEY);
    return raw ? (JSON.parse(raw) as TokenMap) : {};
  } catch {
    return {};
  }
}

export function savePostEditToken(postId: number, editToken: string) {
  const map = readTokens();
  map[String(postId)] = editToken;
  localStorage.setItem(POST_TOKENS_KEY, JSON.stringify(map));
}

export function getPostEditToken(postId: number): string | null {
  return readTokens()[String(postId)] ?? null;
}

export function removePostEditToken(postId: number) {
  const map = readTokens();
  delete map[String(postId)];
  localStorage.setItem(POST_TOKENS_KEY, JSON.stringify(map));
}

export function getVoterKey(): string {
  if (typeof window === 'undefined') return '';
  let key = localStorage.getItem(VOTER_KEY);
  if (!key) {
    key = crypto.randomUUID();
    localStorage.setItem(VOTER_KEY, key);
  }
  return key;
}

const LIKED_POSTS_KEY = 'community_liked_posts';

export function getLikedPostIds(): Set<number> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(LIKED_POSTS_KEY);
    const ids = raw ? (JSON.parse(raw) as number[]) : [];
    return new Set(ids);
  } catch {
    return new Set();
  }
}

export function markPostLiked(postId: number) {
  const liked = getLikedPostIds();
  liked.add(postId);
  localStorage.setItem(LIKED_POSTS_KEY, JSON.stringify([...liked]));
}

export function getCommunityAdminToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function saveCommunityAdminToken(token: string) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token.trim());
}

export function clearCommunityAdminToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}
