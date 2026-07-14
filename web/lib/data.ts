export interface Card {
  id: string;
  name: string;
  enName: string;
  set: string;
  setCode: string;
  setId: string;
  number: string;
  rarity: string;
  rarityRank: number;
  imageUrl: string;
  imageColor: string;
  priceKR: number;
  priceJP: number;
  trendKR: number;
  trendJP: number;
  historyKR: { date: string; price: number }[];
  historyJP: { date: string; price: number }[];
}

export interface SetData {
  id: string;
  name: string;
  enName: string;
  code: string;
  releaseDate: string;
  imageColor: string;
  imageUrl?: string;
  boxPriceKR: number;
  boxPriceJP: number;
  msrpPackKR: number;
  msrpBoxKR: number;
  msrpPackJP: number;
  msrpBoxJP: number;
}

const generateHistory = (base: number) => {
  return Array.from({ length: 7 }).map((_, i) => ({
    date: `07-0${i + 1}`,
    price: Math.round(base * (1 + (Math.random() * 0.2 - 0.1))),
  }));
};

import { getSetMsrp } from './set-msrp';
import { roundDisplayPrice } from './price-round';

export const MOCK_CARDS: Card[] = [
  {
    id: "charizard-ex-sar-151",
    name: "리자몽 ex",
    enName: "Charizard ex",
    set: "포켓몬 카드 151",
    setCode: "SV2a",
    setId: "",
    number: "201/165",
    rarity: "SAR",
    rarityRank: 8,
    imageUrl: "",
    imageColor: "from-orange-500 via-red-600 to-rose-700",
    priceKR: 185000,
    priceJP: 240000,
    trendKR: 5.2,
    trendJP: -1.8,
    historyKR: generateHistory(185000),
    historyJP: generateHistory(240000),
  },
  {
    id: "mew-ex-ur-151",
    name: "뮤 ex",
    enName: "Mew ex",
    set: "포켓몬 카드 151",
    setCode: "SV2a",
    setId: "",
    number: "208/165",
    rarity: "UR",
    rarityRank: 7,
    imageUrl: "",
    imageColor: "from-fuchsia-500 via-purple-600 to-pink-500",
    priceKR: 45000,
    priceJP: 52000,
    trendKR: -2.1,
    trendJP: 0.5,
    historyKR: generateHistory(45000),
    historyJP: generateHistory(52000),
  },
  {
    id: "pikachu-ar-151",
    name: "피카츄",
    enName: "Pikachu",
    set: "포켓몬 카드 151",
    setCode: "SV2a",
    setId: "",
    number: "173/165",
    rarity: "AR",
    rarityRank: 4,
    imageUrl: "",
    imageColor: "from-yellow-300 via-yellow-400 to-amber-500",
    priceKR: 12000,
    priceJP: 28000,
    trendKR: 12.5,
    trendJP: 8.4,
    historyKR: generateHistory(12000),
    historyJP: generateHistory(28000),
  },
  {
    id: "ion-sar-clay",
    name: "모야모",
    enName: "Iono",
    set: "클레이버스트",
    setCode: "SV2D",
    setId: "",
    number: "096/071",
    rarity: "SAR",
    rarityRank: 8,
    imageUrl: "",
    imageColor: "from-lime-400 via-emerald-500 to-teal-600",
    priceKR: 320000,
    priceJP: 850000,
    trendKR: -5.0,
    trendJP: -12.5,
    historyKR: generateHistory(320000),
    historyJP: generateHistory(850000),
  },
  {
    id: "giratina-v-sa-lost",
    name: "기라티나 V",
    enName: "Giratina V",
    set: "로스트어비스",
    setCode: "S11",
    setId: "",
    number: "111/100",
    rarity: "SA",
    rarityRank: 6,
    imageUrl: "",
    imageColor: "from-slate-700 via-indigo-800 to-purple-900",
    priceKR: 280000,
    priceJP: 410000,
    trendKR: 2.1,
    trendJP: 4.5,
    historyKR: generateHistory(280000),
    historyJP: generateHistory(410000),
  },
  {
    id: "lugia-v-sa-paradigm",
    name: "루기아 V",
    enName: "Lugia V",
    set: "패러다임트리거",
    setCode: "S12",
    setId: "",
    number: "110/098",
    rarity: "SA",
    rarityRank: 6,
    imageUrl: "",
    imageColor: "from-blue-300 via-blue-500 to-indigo-600",
    priceKR: 210000,
    priceJP: 350000,
    trendKR: 1.5,
    trendJP: 0.8,
    historyKR: generateHistory(210000),
    historyJP: generateHistory(350000),
  },
];

export const MOCK_SETS: SetData[] = [
  {
    id: "set-151",
    name: "포켓몬 카드 151",
    enName: "Pokemon Card 151",
    code: "SV2a",
    releaseDate: "2023-07-28",
    imageColor: "from-green-500 to-emerald-700",
    boxPriceKR: 65000,
    boxPriceJP: 140000,
    ...(() => { const m = getSetMsrp('SV2a'); return { msrpPackKR: m.packKR, msrpBoxKR: m.boxKR, msrpPackJP: m.packJP, msrpBoxJP: m.boxJP }; })(),
  },
  {
    id: "set-clay",
    name: "클레이버스트",
    enName: "Clay Burst",
    code: "SV2D",
    releaseDate: "2023-04-14",
    imageColor: "from-purple-500 to-fuchsia-700",
    boxPriceKR: 45000,
    boxPriceJP: 85000,
    ...(() => { const m = getSetMsrp('SV2D'); return { msrpPackKR: m.packKR, msrpBoxKR: m.boxKR, msrpPackJP: m.packJP, msrpBoxJP: m.boxJP }; })(),
  },
  {
    id: "set-vstar",
    name: "VSTAR 유니버스",
    enName: "VSTAR Universe",
    code: "S12a",
    releaseDate: "2022-12-02",
    imageColor: "from-slate-800 to-slate-950",
    boxPriceKR: 85000,
    boxPriceJP: 110000,
    ...(() => { const m = getSetMsrp('S12a'); return { msrpPackKR: m.packKR, msrpBoxKR: m.boxKR, msrpPackJP: m.packJP, msrpBoxJP: m.boxJP }; })(),
  },
  {
    id: "set-shiny",
    name: "샤이니트레저 ex",
    enName: "Shiny Treasure ex",
    code: "SV4a",
    releaseDate: "2023-12-01",
    imageColor: "from-cyan-400 to-blue-600",
    boxPriceKR: 55000,
    boxPriceJP: 65000,
    ...(() => { const m = getSetMsrp('SV4a'); return { msrpPackKR: m.packKR, msrpBoxKR: m.boxKR, msrpPackJP: m.packJP, msrpBoxJP: m.boxJP }; })(),
  },
];

export const formatKRW = (price: number) => {
  const rounded = roundDisplayPrice(price);
  return new Intl.NumberFormat('ko-KR').format(rounded) + '원';
};

export const formatJPY = (price: number) => {
  return new Intl.NumberFormat('ja-JP').format(Math.round(price / 9.2)) + '円';
};
