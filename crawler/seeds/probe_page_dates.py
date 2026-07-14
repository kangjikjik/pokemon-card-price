"""pokemoncard 페이지 HTML 발매일 스니펫 확인"""
import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGES = {
    785: "MG1b",
    796: "MG2a",
    859: "MG4a",
}


def main():
    for page, code in PAGES.items():
        r = httpx.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15, headers=HEADERS)
        r.encoding = "utf-8"
        h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", r.text)
        price = re.search(r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자", r.text)
        imgs = re.findall(
            r"https://data1\.pokemonkorea\.co\.kr/202[0-9]/[^\"'\s>]+\.(?:png|jpg)",
            r.text,
        )
        print(f"\n=== {code} page {page} ===")
        print("h3:", h3[0] if h3 else None)
        print("price:", price.groups() if price else None)
        for u in imgs[:3]:
            print("img:", u)
        # 발매일 관련
        for m in re.finditer(r".{0,30}발매.{0,80}", r.text):
            s = re.sub(r"\s+", " ", m.group(0))
            if "발매가" not in s and "1팩" not in s:
                print("ctx:", s[:100])


if __name__ == "__main__":
    main()
