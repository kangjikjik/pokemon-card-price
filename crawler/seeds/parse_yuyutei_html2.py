import re, httpx

r = httpx.get("https://yuyu-tei.jp/sell/poc/s/MG6", headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=20)
text = r.text

# m05 이미지 주변 컨텍스트
for m in re.finditer(r'm05/100\d+\.jpg', text):
    start = max(0, m.start() - 300)
    end = min(len(text), m.end() + 300)
    chunk = text[start:end]
    if "メガ" in chunk or "SAR" in chunk or "ムク" in chunk:
        print("---")
        print(re.sub(r'<[^>]+>', ' ', chunk)[:400])
        print()

# rare 필터 URL
rares = re.findall(r'rare=[A-Z]+', text)
print("rare params:", sorted(set(rares)))

# data-card or product patterns
for pat in [r'data-name="([^"]+)"', r'card-name[^>]*>([^<]+)', r'alt="([^"]*メガ[^"]*)"']:
    found = re.findall(pat, text)
    if found:
        print(f"\n{pat}: {found[:10]}")
