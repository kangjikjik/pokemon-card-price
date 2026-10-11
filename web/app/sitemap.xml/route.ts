import { sitemapIndexResponse } from '@/lib/sitemap-data';

export const revalidate = 3600;

export async function GET() {
  return sitemapIndexResponse();
}
