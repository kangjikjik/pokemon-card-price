const OFFICIAL_CARD_IMAGE_HOST = 'cards.image.pokemonkorea.co.kr';

/**
 * pokemoncard.co.kr serves card images through a resized endpoint.
 * Without the size query, the CDN can return 415 for direct image requests.
 */
export function normalizeCardImageUrl(imageUrl?: string): string | undefined {
  if (!imageUrl || !imageUrl.includes(OFFICIAL_CARD_IMAGE_HOST)) {
    return imageUrl;
  }

  try {
    const url = new URL(imageUrl);
    if (!url.searchParams.has('w')) {
      url.searchParams.set('w', '512');
    }
    return url.toString();
  } catch {
    return imageUrl;
  }
}
