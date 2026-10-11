'use client';

import { useEffect } from 'react';

/** 세트 상세가 열리면 조회 1회를 남긴다. */
export function RecordSetView({ setId }: { setId: string }) {
  useEffect(() => {
    if (!/^\d+$/.test(setId)) return;
    fetch(`/api/sets/${setId}/view`, { method: 'POST' }).catch(() => {});
  }, [setId]);
  return null;
}
