# -*- coding: utf-8 -*-
"""
不重跑整個 build_data.py（避免覆蓋掉已經壓縮/改名的 images），
只單純把「診斷名稱」欄位補進現有 questions.json。
"""
import json
import re
from pathlib import Path

VAULT = Path(r"C:\Obsidian 資料庫\CYP")
TOPIC_DIR = VAULT / "外" / "專科考試 l 季考閱片" / "季考閱片_題目整理"
SITE_DIR = Path(__file__).parent
OUT_JSON = SITE_DIR / "questions.json"

fm_re = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
id_embed_re = re.compile(r"!\[\[(ST\d{8,10})\]\]")


def parse_frontmatter(text):
    m = fm_re.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, body


diagnosis_index = {}
for f in TOPIC_DIR.glob("ST_*.md"):
    try:
        text = f.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    fm, body = parse_frontmatter(text)
    disease = fm.get("Disease", "").strip()
    if not disease:
        continue
    for st_id in id_embed_re.findall(body):
        diagnosis_index.setdefault(st_id, disease)

data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
matched = 0
for q in data:
    q["diagnosis"] = diagnosis_index.get(q["id"], "")
    if q["diagnosis"]:
        matched += 1

OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"共 {len(data)} 題，{matched} 題補上診斷名稱")
