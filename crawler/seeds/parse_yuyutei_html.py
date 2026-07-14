import re, httpx

r = httpx.get("https://yuyu-tei.jp/sell/poc/s/MG6", headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=20)
text = r.text

# m05 폴더 이미지
m05 = re.findall(r'https://card\.yuyu-tei\.jp/poc/100_140/m05/\d+\.jpg', text)
print(f"m05 images: {len(m05)}")
for u in sorted(set(m05))[:20]:
    print(u)

# 카드 링크 + 이름 패턴
blocks = re.findall(
    r'href="(/sell/poc/card/[^"]+)"[^>]*>.*?<h4[^>]*>([^<]+)</h4>.*?([\d,]+)\s*円',
    text, re.DOTALL
)
print(f"\nblocks: {len(blocks)}")
for href, name, price in blocks[:25]:
    print(name, price, href)

# SAR 섹션
for m in re.finditer(r'(SAR|SR|AR|MUR|RR).*?Card List', text):
    start = m.start()
    chunk = text[start:start+5000]
    names = re.findall(r'<h4[^>]*>([^<]+)</h4>', chunk)
    imgs = re.findall(r'm05/\d+\.jpg', chunk)
    print(f"\n=== {m.group(1)} section: {len(names)} names, {len(imgs)} imgs ===")
    for n, i in zip(names[:10], imgs[:10]):
        print(f"  {n} | {i}")
