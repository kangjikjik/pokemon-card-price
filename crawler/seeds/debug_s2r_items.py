import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crawl_box_prices import fetch_bunjang
from lib.box_price_search import build_box_search_queries, filter_bunjang_kr_box_quotes, _box_unit_price
from kr_sets import KR_BY_CODE

def debug_set(code):
    meta = KR_BY_CODE.get(code)
    if not meta:
        print("Unknown code", code)
        return
    name = meta.name_kr
    print("\n=== DEBUG", code, name, "===\n")
    queries = build_box_search_queries(name, code)[:8]
    for q in queries:
        print("-- query:", q)
        items = fetch_bunjang(q)
        print(" fetched items:", len(items))
        sold, listings = filter_bunjang_kr_box_quotes(items, name, code, meta.msrp_box_kr, meta.msrp_pack_kr, verifier=None)
        print(" matched sold:", len(sold), " matched listings:", len(listings))
        if sold:
            print(" SOLD items:")
            for s in sold:
                print("  pid=", s.pid, " unit_price=", s.price, " updated_at=", s.updated_at)
        if listings:
            print(" LISTING items:")
            for l in listings:
                print("  pid=", l.pid, " unit_price=", l.price, " updated_at=", l.updated_at)
        raw_sold = [it for it in items if str(it.get('status','')) in {'3','3'}]
        if raw_sold:
            print(" raw sold entries count:", len(raw_sold))
            for it in raw_sold[:10]:
                pid = it.get('pid')
                title = it.get('name')
                price = it.get('price')
                updated = it.get('update_time') or it.get('updated_at')
                unit = _box_unit_price(int(price or 0), str(title)) if price else None
                print('  raw pid=', pid, ' price=', price, ' unit=', unit, ' updated=', updated, ' title=', (title or '')[:200])

if __name__ == '__main__':
    debug_set('S2R')

