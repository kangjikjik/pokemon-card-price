"""유유테이 MG6 상세 페이지에서 실제 카드 이미지 URL 추출 검증"""
import re
import time
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

# 시크릿 카드 yuyutei 페이지 ID (10082~10118)
SECRET_PAGE_IDS = list(range(10082, 10119))

def extract_card_image(html: str, page_id: str) -> dict:
    """상세 페이지 HTML에서 카드명·레어도·이미지 추출"""
    title = re.search(r"<title>([^<]+)</title>", html)
    title_text = title.group(1) if title else ""

    # title 예: "SAR メガダークライex 販売 | [M5] ..."
    m = re.match(r"([A-Z]+(?:\s+ACE)?)\s+(.+?)\s+販売", title_text)
    rarity, name = (m.group(1), m.group(2)) if m else ("?", "?")

    # 상세 페이지 메인 카드 이미지 (card.yuyu-tei.jp/poc/.../m05/XXXX.jpg)
    # og:image 또는 zoom 이미지 우선
    og = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    zoom = re.search(r'id="card_image"\s+[^>]*src="([^"]+)"', html)
    main_img = re.search(
        rf'https://card\.yuyu-tei\.jp/poc/[^"\']+/m05/(\d+)\.jpg',
        html,
    )
    # card_image 클래스/ id 패턴
    card_img = re.search(r'class="[^"]*card[^"]*img[^"]*"[^>]*src="([^"]+)"', html, re.I)
    card_img2 = re.search(r'<img[^>]+src="(https://card\.yuyu-tei\.jp/poc/[^"]+m05/\d+\.jpg)"', html)

    imgs = re.findall(r'https://card\.yuyu-tei\.jp/poc/[^"\']+/m05/(\d+)\.jpg', html)
    unique_imgs = list(dict.fromkeys(imgs))

    return {
        "page_id": page_id,
        "title": title_text[:60],
        "rarity": rarity.strip(),
        "name": name.strip(),
        "og_image": og.group(1) if og else None,
        "zoom": zoom.group(1) if zoom else None,
        "card_img": card_img.group(1) if card_img else None,
        "card_img2": card_img2.group(1) if card_img2 else None,
        "all_m05_ids": unique_imgs[:5],
    }


def main():
    results = []
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        for pid in SECRET_PAGE_IDS:
            url = f"https://yuyu-tei.jp/sell/poc/card/m05/{pid}"
            try:
                r = client.get(url)
                if r.status_code == 429:
                    print(f"  {pid}: RATE LIMITED, waiting...")
                    time.sleep(5)
                    r = client.get(url)
                if r.status_code != 200:
                    print(f"  {pid}: HTTP {r.status_code}")
                    continue
                info = extract_card_image(r.text, str(pid))
                results.append(info)
                img = info["og_image"] or info["zoom"] or info["card_img2"] or ""
                print(f"{pid} {info['rarity']:4} {info['name']:20} -> {img or info['all_m05_ids']}")
            except Exception as e:
                print(f"  {pid}: ERROR {e}")
            time.sleep(0.5)

    print(f"\nTotal: {len(results)}")


if __name__ == "__main__":
    main()
