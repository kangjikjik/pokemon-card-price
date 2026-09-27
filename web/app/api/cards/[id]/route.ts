import { NextRequest, NextResponse } from 'next/server';
import { fetchCardDetailById } from '@/lib/card-detail';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const card = await fetchCardDetailById(parseInt(id, 10));
  if (!card) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  return NextResponse.json({ data: card, source: 'db' });
}
