/** 스페셜 · 기념 (확장팩 주기 밖 — 25주년 등) */

export const SPECIAL_SET_CODES = ['CEL', 'CEL25PK'] as const;



/** 노출 79개 — crawler/seeds/kr_sets.py 와 동기화 (한국 발매일 최신순) */

export const FEATURED_SET_CODES = [

  'MG6',

  'MG5a',

  'MG5',

  'MG4a',

  'MG4',

  'MG3a',

  'MG3',

  'MG2a',

  'MG2',

  'MG1b',

  'MG1a',

  'SV8a',

  'SV8',

  'SV7',

  'SV6a',

  'SV6',

  'SV5a',

  'SV5K',

  'SV5M',

  'SV4x',

  'SV4',

  'SV4a',

  'SV4K',

  'SV4M',

  'SV3a',

  'SV3',

  'SV2a',

  'SV2D',

  'SV2P',

  'SV1a',

  'SV1V',

  'SV1S',

  'S12a',

  'S12',

  'S11a',

  'S11',

  'S10b',

  'S10a',

  'S9a',

  'S9',

  'S8',

  'S8a',

  'S8b',

  'S7F',

  'CEL',

  'S7R',

  'S7D',

  'S6H',

  'S6G',

  'S6L',

  'S5F',

  'S5S',

  'S5P',

  'S4SV',

  'S4B',

  'S3H',

  'S3Z',

  'S2R',

  'S2',

  'S1a',

  'S1W',

  'S1H',

  'SM12a',

  'SM12',

  'SM11b',

  'SM11a',

  'SM10',

  'SM9',

  'SM8b',

  'SM9a',

  'SM8',

  'SM7',

  'SM6b',

  'SM6a',

  'SM6',

  'SM5+',

  'SM5',

  'SM4+',

  'SM4',

] as const;



/** A) 이벤트·증정 프로모 — 삭제됨 */
export const PROMO_EVENT_SET_CODES = [] as const;



/** 분류 애매한 단발 증정 */

export const PROMO_MISC_SET_CODE = 'PRM-MISC' as const;

/** 주간 핫카드 — 프로모 잉어킹 (040/M-P) */
export const WEEKLY_HOT_CARD = {
  setCode: PROMO_MISC_SET_CODE,
  cardNumber: '040/M-P',
  cardId: 9150,
} as const;



/** 세트 시세 — 프로모·이벤트 탭 */

export const PROMO_PAGE_SET_CODES = [

  ...PROMO_EVENT_SET_CODES,

  PROMO_MISC_SET_CODE,

] as const;



/** B) 스페셜·기념 (CEL25PK — CEL은 FEATURED에 포함) */

export const COMMEMORATIVE_SET_CODES = ['CEL25PK'] as const;



/** 세트 시세 페이지 조회 (featured + 기념 + 프로모) */

export const SETS_PAGE_EXTRA_CODES = [

  ...COMMEMORATIVE_SET_CODES,

  ...PROMO_PAGE_SET_CODES,

] as const;



/** 카드 목록·통계 — featured + 이벤트 프로모 + 기념 + 기타 */

export const CARDS_LIST_SET_CODES = [

  ...FEATURED_SET_CODES,

  ...PROMO_EVENT_SET_CODES,

  PROMO_MISC_SET_CODE,

  ...COMMEMORATIVE_SET_CODES,

] as const;



/** 상세 페이지·API 노출 허용 세트 */

export const VIEWABLE_SET_CODES = CARDS_LIST_SET_CODES;



/** @deprecated use PROMO_EVENT_SET_CODES + CEL25PK */

export const PROMO_SET_CODES = [...PROMO_EVENT_SET_CODES, 'CEL25PK'] as const;



export const EXPANSION_SET_CODES = (FEATURED_SET_CODES as readonly string[]).filter(

  (code) => !(SPECIAL_SET_CODES as readonly string[]).includes(code),

) as Exclude<FeaturedSetCode, (typeof SPECIAL_SET_CODES)[number]>[];



export const FEATURED_SET_LIMIT = 79;



export type FeaturedSetCode = (typeof FEATURED_SET_CODES)[number];

export type SpecialSetCode = (typeof SPECIAL_SET_CODES)[number];



export function isFeaturedSetCode(code: string): boolean {

  return (FEATURED_SET_CODES as readonly string[]).includes(code);

}



export function isViewableSetCode(code: string): boolean {

  return (VIEWABLE_SET_CODES as readonly string[]).includes(code);

}



export function isSpecialSetCode(code: string): boolean {

  return (SPECIAL_SET_CODES as readonly string[]).includes(code);

}



export function isPromoPageSetCode(code: string): boolean {

  return (PROMO_PAGE_SET_CODES as readonly string[]).includes(code);

}



export function isExpansionSetCode(code: string): boolean {

  return isFeaturedSetCode(code) && !isSpecialSetCode(code);

}


