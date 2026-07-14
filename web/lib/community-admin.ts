import type { NextRequest } from 'next/server';

export const ADMIN_TOKEN_HEADER = 'x-community-admin-token';

export function getCommunityAdminToken(): string {
  return process.env.COMMUNITY_ADMIN_TOKEN?.trim() || '';
}

export function verifyCommunityAdminToken(req: NextRequest): boolean {
  const expected = getCommunityAdminToken();
  if (!expected) return false;
  const got = req.headers.get(ADMIN_TOKEN_HEADER)?.trim() || '';
  return got.length > 0 && got === expected;
}

export function getCommunityAdminDisplayName(): string {
  return process.env.COMMUNITY_ADMIN_NAME?.trim() || '운영자';
}
