import re, httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}

for rare in ["SAR", "SR", "AR", "MUR", "RR", None]:
    url = "https://yuyu-tei.jp/sell/poc/s/MG6" + (f"?rare={rare}" if rare else "")
    text = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20).text
    
    # h4 태그 카드명
    h4s = re.findall(r'<h4[^>]*class="[^"]*text-primary[^"]*"[^>]*>([^<]+)</h4>', text)
    # 또는 carousel 내 카드명
    names = re.findall(r'>\s*([\u3040-\u9fff\u30a0-\u30ff\w]+(?:ex|EX)?)\s+</', text)
    
    # card links
    links = re.findall(r'/sell/poc/card/m05/(\d+)"', text)
    imgs = re.findall(r'm05/(\d+)\.jpg', text)
    
    # title in page for SAR section
    sar_section = ""
    if "SAR" in text:
        idx = text.find("SAR")
        sar_section = text[idx:idx+8000]
        sar_names = re.findall(r'>([^<]{2,30}ex)</', sar_section)
        sar_links = re.findall(r'/sell/poc/card/m05/(\d+)', sar_section)
        sar_imgs = list(dict.fromkeys(re.findall(r'm05/(\d+)\.jpg', sar_section)))
    
    print(f"\n=== {rare or 'ALL'} ===")
    print(f"  h4: {h4s[:8]}")
    print(f"  links: {len(set(links))}, imgs: {len(set(imgs))}")
    
    if rare == "SAR":
        print(f"  SAR names: {sar_names[:10]}")
        print(f"  SAR links: {sar_links[:10]}")
        print(f"  SAR imgs: {sar_imgs[:10]}")

# MG6 페이지에서 카드 블록 구조 덤프
text = httpx.get("https://yuyu-tei.jp/sell/poc/s/MG6?rare=SAR", headers=HEADERS).text
# find all occurrences of メガ with surrounding link
for m in re.finditer(r'メガ[\u30a0-\u30ff]+ex', text):
    start = max(0, m.start()-200)
    end = min(len(text), m.end()+200)
    chunk = text[start:end]
    link = re.search(r'/sell/poc/card/m05/(\d+)', chunk)
    img = re.search(r'm05/(\d+)\.jpg', chunk)
    price = re.search(r'([\d,]+)\s*円', chunk)
    print(f"\n{m.group()}: id={link.group(1) if link else '?'} img={img.group(1) if img else '?'} price={price.group(1) if price else '?'}")
