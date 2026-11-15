import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { CardDetailView } from '@/components/card-detail-view';
import {
  buildCardDetailDescription,
  buildCardDetailJsonLd,
  buildCardDetailTitle,
  cardDetailCanonicalUrl,
  fetchCardDetailById,
} from '@/lib/card-detail';

export const dynamic = 'force-dynamic';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const card = await fetchCardDetailById(parseInt(id, 10));
  if (!card) {
    return { title: '카드를 찾을 수 없음' };
  }

  const title = buildCardDetailTitle(card);
  const description = buildCardDetailDescription(card);
  const url = cardDetailCanonicalUrl(card.id);

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
      locale: 'ko_KR',
      ...(card.imageUrl ? { images: [{ url: card.imageUrl, alt: card.name }] } : {}),
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      ...(card.imageUrl ? { images: [card.imageUrl] } : {}),
    },
  };
}

export default async function CardDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const card = await fetchCardDetailById(parseInt(id, 10));
  if (!card) notFound();

  const jsonLd = buildCardDetailJsonLd(card);

  return (
    <>
      {jsonLd && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      )}
      <CardDetailView card={card} />
    </>
  );
}
