"""
일본판 팩/박스 희망소매가격 검증·반영.

출처 우선순위:
  1) www.pokemon-card.com 제품 페이지 — 팩 希望小売価格
  2) www.pokemoncenter-online.com BOX 상품 — 박스 税込 가격 + 1BOX=Nパック
  3) (2)로 확정된 동일 상품 규격이면 pack×N 으로 박스 산출 (공식 팩가 × 공식 팩수)

실행:
  python fill_jp_msrp_verified.py           # 스크랩·리포트
  python fill_jp_msrp_verified.py --apply   # set-msrp.ts 반영
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_SETS  # noqa: E402

APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parents[2]
OUT_TS = ROOT / "web" / "lib" / "set-msrp.ts"
OUT_JSON = Path(__file__).with_name("_audit_out") / "jp_msrp_sources.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; pokemon-card-price/1.0)"}

JP_PACK_RE = re.compile(r"希望小売価格[\]：:\s]*([\d,]+)\s*円")
JP_PACK_RE2 = re.compile(r"\[希望小売価格\]\s*([\d,]+)\s*円")
JP_PACK_RE3 = re.compile(r"希望小売価格[：:\s]*([\d,]+)\s*円\s*[＋+]\s*税")

# 제품 페이지에 팩가 없을 때 — 포켓몬 공식 PR
PRESS_FALLBACK: dict[str, str] = {
    "SM9": "https://prtimes.jp/main/html/rd/p/000000053.000026665.html",
    "SM9a": "https://prtimes.jp/main/html/rd/p/000000045.000026665.html",
}

# code -> (jp_name, official_product_url)
JP_URL: dict[str, tuple[str, str]] = {
    "MG6": ("アビスアイ", "https://www.pokemon-card.com/ex/m5/"),
    "MG5a": ("ニンジャスピナー", "https://www.pokemon-card.com/ex/m4/"),
    "MG5": ("ムニキスゼロ", "https://www.pokemon-card.com/ex/m3/"),
    "MG4a": ("MEGAドリームex", "https://www.pokemon-card.com/ex/m2a/"),
    "MG4": ("インフェルノX", "https://www.pokemon-card.com/ex/m2/"),
    "MG3a": ("メガシンフォニア", "https://www.pokemon-card.com/ex/m1/"),
    "MG3": ("メガブレイブ", "https://www.pokemon-card.com/ex/m1/"),
    "MG2a": ("ホワイトフレア", "https://www.pokemon-card.com/ex/sv11/"),
    "MG2": ("ブラックボルト", "https://www.pokemon-card.com/ex/sv11/"),
    "MG1b": ("ロケット団の栄光", "https://www.pokemon-card.com/ex/sv10/"),
    "MG1a": ("熱風のアリーナ", "https://www.pokemon-card.com/products/sv/sv9a.html"),
    "SV8a": ("バトルパートナーズ", "https://www.pokemon-card.com/ex/sv9/"),
    "SV8": ("テラスタルフェスex", "https://www.pokemon-card.com/ex/sv8a/"),
    "SV7": ("超電ブレイカー", "https://www.pokemon-card.com/ex/sv8/"),
    "SV6a": ("楽園ドラゴーナ", "https://www.pokemon-card.com/products/sv/sv7a.html"),
    "SV6": ("ステラミラクル", "https://www.pokemon-card.com/ex/sv7/"),
    "SV5a": ("ナイトワンダラー", "https://www.pokemon-card.com/products/sv/sv6a.html"),
    "SV5K": ("変幻の仮面", "https://www.pokemon-card.com/ex/sv6/"),
    "SV5M": ("クリムゾンヘイズ", "https://www.pokemon-card.com/ex/sv5/"),
    "SV4x": ("サイバージャッジ", "https://www.pokemon-card.com/ex/sv5/"),
    "SV4": ("ワイルドフォース", "https://www.pokemon-card.com/ex/sv5/"),
    "SV4a": ("シャイニートレジャーex", "https://www.pokemon-card.com/ex/sv4a/"),
    "SV4K": ("古代の咆哮", "https://www.pokemon-card.com/ex/sv4/"),
    "SV4M": ("未来の一閃", "https://www.pokemon-card.com/ex/sv4/"),
    "SV3a": ("レイジングサーフ", "https://www.pokemon-card.com/products/sv/sv3a.html"),
    "SV3": ("黒炎の支配者", "https://www.pokemon-card.com/ex/sv3/"),
    "SV2a": ("ポケモンカード151", "https://www.pokemon-card.com/ex/sv2a/"),
    "SV2D": ("クレイバースト", "https://www.pokemon-card.com/products/sv/sv2.html"),
    "SV2P": ("スノーハザード", "https://www.pokemon-card.com/products/sv/sv2.html"),
    "SV1a": ("トリプレットビート", "https://www.pokemon-card.com/products/sv/sv1a.html"),
    "SV1V": ("バイオレットex", "https://www.pokemon-card.com/ex/sv1/"),
    "SV1S": ("スカーレットex", "https://www.pokemon-card.com/ex/sv1/"),
    "S12a": ("VSTARユニバース", "https://www.pokemon-card.com/ex/s12a/"),
    "S12": ("パラダイムトリガー", "https://www.pokemon-card.com/ex/s12/"),
    "S11a": ("白熱のアルカナ", "https://www.pokemon-card.com/products/s/s11a.html"),
    "S11": ("ロストアビス", "https://www.pokemon-card.com/ex/s11/"),
    "S10b": ("ダークファンタズマ", "https://www.pokemon-card.com/ex/s10b/"),
    "S10a": ("Pokémon GO", "https://www.pokemon-card.com/ex/s10a/"),
    "S9a": ("タイムゲイザー", "https://www.pokemon-card.com/products/s/s9a.html"),
    "S9": ("スペースジャグラー", "https://www.pokemon-card.com/products/s/s9a.html"),
    "S8": ("バトルリージョン", "https://www.pokemon-card.com/products/s/s8.html"),
    "S8a": ("スターバース", "https://www.pokemon-card.com/ex/s9/"),
    "S8b": ("VMAXクライマックス", "https://www.pokemon-card.com/ex/s8b/"),
    "S7F": ("フュージョンアーツ", "https://www.pokemon-card.com/products/s/s8.html"),
    "CEL": ("25th ANNIVERSARY COLLECTION", "https://www.pokemon-card.com/ex/25th/products/"),
    "S7R": ("蒼空ストリーム", "https://www.pokemon-card.com/ex/rengeki/index.html"),
    "S7D": ("摩天パーフェクト", "https://www.pokemon-card.com/ex/rengeki/index.html"),
    "S6H": ("イーブイヒーローズ", "https://www.pokemon-card.com/products/s/s6a.html"),
    "S6G": ("白銀のランス", "https://www.pokemon-card.com/products/s/s6.html"),
    "S6L": ("漆黒のガイスト", "https://www.pokemon-card.com/products/s/s6.html"),
    "S5F": ("一撃マスター", "https://www.pokemon-card.com/products/s/s5.html"),
    "S5S": ("連撃マスター", "https://www.pokemon-card.com/products/s/s5.html"),
    "S5P": ("連撃マスター", "https://www.pokemon-card.com/products/s/s5.html"),
    "S4SV": ("シャイニースターV", "https://www.pokemon-card.com/ex/s4a/"),
    "S4B": ("仰天のボルテッカー", "https://www.pokemon-card.com/ex/s4/"),
    "S3H": ("伝説の鼓動", "https://www.pokemon-card.com/ex/s3/"),
    "S3Z": ("無限ゾーン", "https://www.pokemon-card.com/ex/s3/"),
    "S2R": ("反逆クラッシュ", "https://www.pokemon-card.com/ex/s2/"),
    "S2": ("反逆クラッシュ", "https://www.pokemon-card.com/ex/s2/"),
    "S1a": ("VMAXライジング", "https://www.pokemon-card.com/products/s/s1a.html"),
    "S1W": ("ソード", "https://www.pokemon-card.com/ex/s1/"),
    "S1H": ("シールド", "https://www.pokemon-card.com/ex/s1/"),
    "SM12a": ("タッグオールスターズ", "https://www.pokemon-card.com/ex/sm12a/"),
    "SM12": ("オルタージェネシス", "https://www.pokemon-card.com/ex/sm12/"),
    "SM11b": ("ドリームリーグ", "https://www.pokemon-card.com/ex/sm11b/"),
    "SM11a": ("ミラクルツイン", "https://www.pokemon-card.com/ex/sm11a/"),
    "SM10": ("ダブルブレイズ", "https://www.pokemon-card.com/products/sm/sm10.html"),
    "SM9": ("ナイトユニゾン", "https://www.pokemon-card.com/products/sm/sm9a.html"),
    "SM8b": ("GXウルトラシャイニー", "https://www.pokemon-card.com/ex/sm8b/"),
    "SM9a": ("タッグボルト", "https://www.pokemon-card.com/ex/sm9/index.html"),
    "SM8": ("超爆インパクト", "https://www.pokemon-card.com/products/sm/sm8.html"),
    "SM7": ("裂空のカリスマ", "https://www.pokemon-card.com/products/sm/sm7.html"),
    "SM6b": ("チャンピオンロード", "https://www.pokemon-card.com/products/sm/sm6b.html"),
    "SM6a": ("フェアリーライズ", "https://www.pokemon-card.com/products/sm/sm6a.html"),
    "SM6": ("禁断の光", "https://www.pokemon-card.com/products/sm/sm6.html"),
    "SM5+": ("禁断の光", "https://www.pokemon-card.com/products/sm/sm6.html"),
    "SM5": ("ウルトラフォース", "https://www.pokemon-card.com/products/sm/sm5.html"),
    "SM4+": ("ウルトラムーン", "https://www.pokemon-card.com/products/sm/sm4.html"),
    "SM4": ("ウルトラーサン", "https://www.pokemon-card.com/products/sm/sm4.html"),
}

# Pokemon Center Online BOX 검증 (税込 + 팩수) — 직접 확인한 URL
# box_yen, packs_per_box, source_url, note
PC_BOX: dict[str, tuple[int, int, str, str]] = {
    "MG3": (
        5400,
        30,
        "https://www.pokemoncenter-online.com/9900000006211.html",
        "メガブレイブ BOX 5,400円 / 1BOX=30パック",
    ),
    "MG5a": (
        5400,
        30,
        "https://www.pokemoncenter-online.com/9900000007898.html",
        "ニンジャスピナー BOX 5,400円 / 1BOX=30パック",
    ),
    "MG2": (
        5800,
        20,
        "https://www.pokemoncenter-online.com/9900000006082.html",
        "ブラックボルト BOX 5,800円 / 1BOX=20パック",
    ),
    "MG2a": (
        5800,
        20,
        "https://www.pokemoncenter-online.com/9900000006082.html",
        "ホワイトフレア도 동일 규격(290円×20) — 블랙볼트 PC BOX 페이지로 팩수·박스정가 검증",
    ),
}

# 하이클래스 등: 공식 팩가 + (PC/유통상) 확정 팩수 → 박스 = pack×N
# packs, note, secondary_source (박스정가 교차검증용 신뢰 매체)
HIGHCLASS_PACKS = 10
STANDARD_PACKS = 30

# 코드별 오버라이드 (스페셜 규격)
PACKS_OVERRIDE: dict[str, int] = {
    "CEL": 16,
    "MG2": 20,
    "MG2a": 20,
    "MG4a": 10,
    "SV4a": 10,
    "SV8": 10,
    "SV2a": 20,
    "S12a": 10,
    "S8b": 10,
    "S4SV": 10,
    "SM12a": 10,
    "SM8b": 10,
}


def ts_key(code: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", code):
        return code
    return f"'{code}'"


def scrape_cel_pack_yen(client: httpx.Client, url: str) -> tuple[int, str]:
    try:
        r = client.get(url, timeout=25)
    except Exception as e:
        return 0, f"fetch_err:{e}"
    if r.status_code != 200:
        return 0, f"http_{r.status_code}"
    text = r.text
    # 확장팩 블록(COLLECTION이 태그 줄바꿈으로 분리됨). 액세서리(792円 등)와 구분.
    m = re.search(
        r"拡張パック\s*25th\s*ANNIVERSARY[\s\S]{0,250}?<dt>希望小売価格[：:]</dt>\s*<dd>([\d,]+)円",
        text,
        re.I,
    )
    if m:
        y = int(m.group(1).replace(",", ""))
        if 100 <= y <= 600:
            return y, "ok_25th_pack"
    if "297円" in text and "キラカード5枚" in text:
        return 297, "ok_25th_unique"
    return 0, "no_cel_pack"


def scrape_pack_yen(client: httpx.Client, url: str) -> tuple[int, str]:
    try:
        r = client.get(url, timeout=25)
    except Exception as e:
        return 0, f"fetch_err:{e}"
    if r.status_code != 200:
        return 0, f"http_{r.status_code}"
    text = r.text
    found: list[int] = []
    found += [int(x.replace(",", "")) for x in JP_PACK_RE.findall(text)]
    found += [int(x.replace(",", "")) for x in JP_PACK_RE2.findall(text)]
    found += [int(x.replace(",", "")) for x in JP_PACK_RE3.findall(text)]
    found += [int(x.replace(",", "")) for x in re.findall(r"希望小売価格[^\d]{0,40}([\d,]+)\s*円", text)]
    # <dt>希望小売価格</dt><dd>550円（税込）</dd>
    found += [
        int(x.replace(",", ""))
        for x in re.findall(
            r"希望小売価格</[^>]+>\s*<[^>]+>([\d,]+)\s*円",
            text,
        )
    ]
    packs = [y for y in found if 100 <= y <= 600]
    seen: set[int] = set()
    packs = [y for y in packs if not (y in seen or seen.add(y))]
    if not packs:
        m = re.search(r"希望小売価格</t[dh]>\s*<t[dh][^>]*>\s*([\d,]+)\s*円", text, re.I)
        if m:
            y = int(m.group(1).replace(",", ""))
            if 100 <= y <= 600:
                return y, "ok_table"
        return 0, "no_pack_price"
    return packs[0], "ok"


def resolve_box(
    code: str, pack_yen: int
) -> tuple[int, int, str, str]:
    """returns box_yen, packs, source_url, note"""
    if code in PC_BOX:
        box, packs, url, note = PC_BOX[code]
        return box, packs, url, note

    packs = PACKS_OVERRIDE.get(code, STANDARD_PACKS)
    box = pack_yen * packs if pack_yen else 0

    if packs == 20 and pack_yen in (290,):
        src = (
            "https://www.pokemoncenter-online.com/9900000006082.html"
            if code in ("MG2", "MG2a")
            else JP_URL.get(code, ("", ""))[1]
        )
        note = (
            f"{pack_yen}円×{packs}パック={box}円"
            + (
                " (PC BOX 검증)"
                if code in ("MG2", "MG2a")
                else " (공식 팩가×20 — 151/동규격 강화확장)"
            )
        )
        return box, packs, src, note
    if packs == 10 and pack_yen in (500, 550):
        return (
            box,
            packs,
            JP_URL.get(code, ("", ""))[1],
            f"{pack_yen}円×{packs}팩={box}円 (하이클래스 1BOX=10팩)",
        )
    if packs == 30 and pack_yen == 200:
        return (
            box,
            packs,
            JP_URL.get(code, ("", ""))[1],
            f"{pack_yen}円×{packs}팩={box}円 (MEGA 신가격 200円 표준 30팩)",
        )
    if packs == 30 and pack_yen == 180:
        return (
            box,
            packs,
            "https://www.pokemoncenter-online.com/9900000006211.html",
            f"{pack_yen}円×{packs}팩={box}円 (표준 확장팩 — PC 메가브레이브 BOX: 5400円/30팩 규격)",
        )
    if packs == 16 and pack_yen == 297:
        return (
            box,
            packs,
            JP_URL.get(code, ("", ""))[1],
            f"{pack_yen}円×{packs}팩={box}円 (25th ANNIVERSARY COLLECTION 1BOX=16팩)",
        )
    if packs == 30 and pack_yen in (150, 160):
        return (
            box,
            packs,
            JP_URL.get(code, ("", ""))[1],
            f"{pack_yen}円×{packs}팩={box}円 (구세대 표준 30팩 BOX — 공식 팩가×30)",
        )
    return box, packs, JP_URL.get(code, ("", ""))[1], f"{pack_yen}×{packs}={box}"


def write_msrp(results: dict[str, dict]) -> None:
    blocks = [
        "/** 확장팩 공식 발매가 — pokemoncard.co.kr / pokemon-card.com / pokemoncenter-online 검증값 */",
        "",
        "export type SetMsrp = {",
        "  packKR: number;",
        "  boxKR: number;",
        "  packJP: number;",
        "  boxJP: number;",
        "  packLabelKR?: string;",
        "  boxLabelKR?: string;",
        "  sourceKR?: string;",
        "  sourceJP?: string;",
        "};",
        "",
        f"/** featured {len(KR_SETS)} — JP box는 공식·포켓몬센터 검증 */",
        "export const SET_MSRP: Record<string, SetMsrp> = {",
    ]
    for s in KR_SETS:
        if not s.msrp_pack_kr:
            continue
        j = results.get(s.code, {})
        pack_jp = int(j.get("packJP") or 0)
        box_jp = int(j.get("boxJP") or 0)
        src_kr = (
            f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}"
            if s.pokemoncard_page
            else ""
        )
        src_jp = j.get("sourceJP") or ""
        lines = [
            f"  {ts_key(s.code)}: {{",
            f"    packKR: {s.msrp_pack_kr},",
            f"    boxKR: {s.msrp_box_kr},",
            f"    packJP: {pack_jp},",
            f"    boxJP: {box_jp},",
        ]
        if src_kr:
            lines.append(f"    sourceKR: '{src_kr}',")
        if src_jp:
            lines.append(f"    sourceJP: '{src_jp}',")
        lines.append("  },")
        blocks.extend(lines)
    blocks.extend(
        [
            "};",
            "",
            "const DEFAULT_MSRP: SetMsrp = { packKR: 1000, boxKR: 30000, packJP: 180, boxJP: 5400 };",
            "",
            "export function getSetMsrp(code: string): SetMsrp {",
            "  return SET_MSRP[code] ?? DEFAULT_MSRP;",
            "}",
            "",
            "export function formatYen(amount: number): string {",
            "  return new Intl.NumberFormat('ja-JP').format(amount) + '円';",
            "}",
            "",
        ]
    )
    OUT_TS.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    client = httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30)
    results: dict[str, dict] = {}
    report = []

    for s in KR_SETS:
        entry = JP_URL.get(s.code)
        if not entry or not entry[1]:
            report.append({"code": s.code, "status": "NO_URL"})
            results[s.code] = {"packJP": 0, "boxJP": 0, "sourceJP": ""}
            continue
        jp_name, url = entry
        if s.code == "CEL":
            pack_yen, status = scrape_cel_pack_yen(client, url)
        else:
            pack_yen, status = scrape_pack_yen(client, url)
        if not pack_yen and s.code in PRESS_FALLBACK:
            press_url = PRESS_FALLBACK[s.code]
            pack_yen, status = scrape_pack_yen(client, press_url)
            if pack_yen:
                url = press_url
                status = f"ok_press({status})"
        box_yen, packs, box_src, note = resolve_box(s.code, pack_yen) if pack_yen else (0, 0, url, status)
        # sourceJP: 공식 제품 페이지 (팩가). 박스 교차검증 URL은 JSON에 별도 기록
        results[s.code] = {
            "packJP": pack_yen,
            "boxJP": box_yen if pack_yen else 0,
            "sourceJP": url if pack_yen else "",
            "packsPerBox": packs,
            "boxSource": box_src,
            "note": note,
            "jpName": jp_name,
            "scrapeStatus": status,
        }
        report.append(
            {
                "code": s.code,
                "name_kr": s.name_kr,
                "jpName": jp_name,
                "packJP": pack_yen,
                "boxJP": box_yen if pack_yen else 0,
                "packs": packs,
                "officialUrl": url,
                "boxVerifyUrl": box_src,
                "note": note,
                "status": status,
            }
        )
        flag = "OK" if pack_yen else "FAIL"
        print(f"{flag} {s.code:6} pack={pack_yen:4} box={box_yen:5} x{packs}  {status}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsources -> {OUT_JSON}")
    ok = sum(1 for r in report if r.get("packJP"))
    print(f"verified pack prices: {ok}/{len(report)}")

    if APPLY:
        write_msrp(results)
        print(f"wrote {OUT_TS}")
    else:
        print("드라이런 — 반영: python fill_jp_msrp_verified.py --apply")


if __name__ == "__main__":
    main()
