import { listSitemapIds, SITEMAP_BASE } from '@/lib/sitemap-data';

export const revalidate = 3600;

function buildSitemapIndex(ids: number[], lastmod: string): string {
  const entries = ids
    .map(
      id => `  <sitemap>
    <loc>${SITEMAP_BASE}/sitemap/${id}.xml</loc>
    <lastmod>${lastmod}</lastmod>
  </sitemap>`,
    )
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries}
</sitemapindex>`;
}

export async function GET() {
  const lastmod = new Date().toISOString();
  const ids = await listSitemapIds();
  const body = buildSitemapIndex(ids, lastmod);

  return new Response(body, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, s-maxage=3600',
    },
  });
}
