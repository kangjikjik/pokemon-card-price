import { MetadataRoute } from 'next';
import { listSitemapIds, loadSitemapPart } from '@/lib/sitemap-data';

export const revalidate = 3600;

/** 0=정적, 1=세트, 2+=카드 배치 */
export async function generateSitemaps() {
  const ids = await listSitemapIds();
  return ids.map(id => ({ id }));
}

export default async function sitemap(props: {
  id: Promise<string>;
}): Promise<MetadataRoute.Sitemap> {
  const id = Number(await props.id);
  const now = new Date().toISOString();

  try {
    return await loadSitemapPart(id, now);
  } catch {
    if (id === 0) {
      const { staticSitemapPages } = await import('@/lib/sitemap-data');
      return staticSitemapPages(now);
    }
    return [];
  }
}
