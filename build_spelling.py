# -*- coding: utf-8 -*-
"""
掃描 季考閱片_題目整理 資料夾內 frontmatter 標記 `困難拼音: true` 的 ST_ 疾病檔，
取檔名去掉 ST_ 前綴後的疾病名稱，輸出 spelling.json 供網站拼音複習頁使用。
僅讀取，不修改任何原始 vault 檔案。
"""
import json
import re
from collections import Counter
from pathlib import Path

VAULT = Path(r"C:\Obsidian 資料庫\CYP")
TOPIC_DIR = VAULT / "外" / "專科考試 l 季考閱片" / "季考閱片_題目整理"
SITE_DIR = Path(__file__).parent
OUT_JSON = SITE_DIR / "spelling.json"

fm_re = re.compile(r"^---\n(.*?)\n---", re.S)


def parse_field(fm, key):
    """科目/Section 有兩種合法 YAML 寫法：單行 `科目: MS`，或陣列 `科目:` + `  - MS`，兩種都要支援"""
    m = re.search(r"^" + key + r":[ \t]*(.*)$", fm, re.M)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline:
        return [inline]
    values = []
    for line in fm[m.end():].splitlines():
        if re.match(r"^\s*-\s*\S", line):
            values.append(re.sub(r"^\s*-\s*", "", line).strip())
        elif line.strip():
            break
    return values


items = []
for f in sorted(TOPIC_DIR.glob("ST_*.md")):
    try:
        text = f.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        continue
    m = fm_re.match(text)
    if not m:
        continue
    fm = m.group(1)
    if not re.search(r"^困難拼音:\s*true\s*$", fm, re.M):
        continue

    name = f.stem[3:] if f.stem.startswith("ST_") else f.stem  # 去掉 ST_ 前綴
    body = text[m.end():]
    qids = re.findall(r"!\[\[(ST\d{8,10})\]\]", body)  # 該疾病引用的題號
    items.append({
        "name": name,
        "subjects": parse_field(fm, "科目"),
        "sections": parse_field(fm, "Section"),
        "questionIds": list(dict.fromkeys(qids)),
    })

items.sort(key=lambda x: x["name"].lower())
OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

linked = sum(1 for i in items if i["questionIds"])
print(f"共輸出 {len(items)} 個難拼字疾病名稱（其中 {linked} 個有對應題目影像）")
c = Counter(s for i in items for s in (i["subjects"] or ["(未填科目)"]))
for k, v in sorted(c.items()):
    print(f"  {k}: {v}")
