from pathlib import Path

p = Path(__file__).resolve().parent.parent / "lib" / "price_search.py"
lines = p.read_text(encoding="utf-8").splitlines()
extras = [
    "스톰에메랄드",
    "스톰 에메랄드",
    "스토에메랄da",
    "스토 에메랄da",
    "에메랄da",
]
for i, line in enumerate(lines):
    if '"MG7":' not in line:
        continue
    if not line.strip().endswith("],"):
        continue
    if "스톰에메랄드" in line:
        continue
    inner = line.split("[", 1)[1].rsplit("],", 1)[0]
    parts = [x.strip().strip('"') for x in inner.split(",")]
    for e in extras:
        if e not in parts:
            parts.append(e)
    indent = line[: line.index('"MG7"')]
    lines[i] = indent + '"MG7": [' + ", ".join(f'"{x}"' for x in parts) + "],"
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("ok")
