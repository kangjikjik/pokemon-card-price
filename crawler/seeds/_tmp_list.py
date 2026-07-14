from kr_sets import KR_SETS

for s in KR_SETS[:5]:
    print(f"{s.code:6} {s.name_kr:20} {s.box_image_kr.split('/')[-1]}")
print("---")
for code in [
    "SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM7a", "SM12",
    "S2", "S1W", "S1H", "SM2+", "SM1M", "SM1C", "XY8a",
    "SM6a", "SM10", "SM9a", "SM12a", "CP6",
]:
    s = next(x for x in KR_SETS if x.code == code)
    print(f"{s.code:6} p{s.pokemoncard_page:3} {s.name_kr:25} {s.box_image_kr.split('/')[-1]}")
