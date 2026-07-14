import { NextRequest, NextResponse } from 'next/server';
import { verifyCommunityAdminToken } from '@/lib/community-admin';

export async function POST(req: NextRequest) {
  if (verifyCommunityAdminToken(req)) {
    return NextResponse.json({ ok: true });
  }
  return NextResponse.json({ error: '관리자 토큰이 올바르지 않습니다.' }, { status: 403 });
}
