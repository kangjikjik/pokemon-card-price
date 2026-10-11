/**
 * 구글 서치 콘솔은 Next 라우트가 만든 사이트맵(Vary: rsc)을 가져오지 못한다.
 * 루트의 정적 XML로 써서 Cloudflare 정적 파일로 제공한다.
 */
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createClient } from '@supabase/supabase-js';
import { CARDS_LIST_SET_CODES } from '../lib/constants.ts';
import { DISPLAY_RARITIES, RARITY_ALIASES } from '../lib/rarity.ts';

const BATCH = 800;
const base = (process.env.NEXT_PUBLIC_SITE_URL || 'https://cardory.cc').replace(/\/$/, '');
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_KEY;
if (!url || !key) {
  throw new Error('NEXT_PUBLIC_SUPABASE_URL 또는 SUPABASE_SERVICE_KEY 가 없습니다.');
}

const supabase = createClient(url, key);
const rarities = [...DISPLAY_RARITIES, ...Object.keys(RARITY_ALIASES)];
const publicDir = join(import.meta.dirname, '..', 'public');

function urlset(locs: string[]): string {
  const body = locs.map(loc => `  <url>\n    <loc>${loc}</loc>\n  </url>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
}

function indexXml(partCount: number): string {
  const body = Array.from({ length: partCount }, (_, id) => `  <sitemap>\n    <loc>${base}/sitemap-part-${id}.xml</loc>\n  </sitemap>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</sitemapindex>\n`;
}

async function loadSetIds(): Promise<number[]> {
  const { data, error } = await supabase
    .from('card_sets')
    .select('id')
    .in('set_code', [...CARDS_LIST_SET_CODES]);
  if (error) throw error;
  return (data ?? []).map(row => row.id as number);
}

async function countCards(setIds: number[]): Promise<number> {
  if (!setIds.length) return 0;
  const { count, error } = await supabase
    .from('cards')
    .select('id', { count: 'exact', head: true })
    .in('set_id', setIds)
    .in('rarity', rarities);
  if (error) throw error;
  return count ?? 0;
}

async function loadCardIds(setIds: number[], start: number): Promise<number[]> {
  const { data, error } = await supabase
    .from('cards')
    .select('id')
    .in('set_id', setIds)
    .in('rarity', rarities)
    .order('id', { ascending: true })
    .range(start, start + BATCH - 1);
  if (error) throw error;
  return (data ?? []).map(row => row.id as number);
}

async function main() {
  const setIds = await loadSetIds();
  const parts: string[][] = [
    [`${base}/`, `${base}/cards`, `${base}/sets`, `${base}/community`],
    setIds.map(id => `${base}/sets/${id}`),
  ];

  const total = await countCards(setIds);
  const batches = Math.ceil(total / BATCH);
  for (let i = 0; i < batches; i += 1) {
    const ids = await loadCardIds(setIds, i * BATCH);
    parts.push(ids.map(id => `${base}/cards/${id}`));
  }

  parts.forEach((locs, id) => {
    writeFileSync(join(publicDir, `sitemap-part-${id}.xml`), urlset(locs));
  });
  writeFileSync(join(publicDir, 'sitemap-index.xml'), indexXml(parts.length));
  console.log(`sitemap-index.xml parts=${parts.length} cards=${total}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
