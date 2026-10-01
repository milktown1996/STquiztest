# -*- coding: utf-8 -*-
"""
掃描 季考閱片_題目順序 資料夾內所有 ST_YYYYMMDDNN.md 檔案（全部科目），
每個檔案本身就是「一題獨立的閱片題」：內嵌影像依序為案例圖，
最後一張固定為答案投影片（含診斷/病史等資訊，須隱藏後才能看）。
輸出 questions.json 並把圖片複製到 site/images/。
僅讀取，不修改任何原始 vault 檔案。
"""
import json
import re
from pathlib import Path

VAULT = Path(r"C:\Obsidian 資料庫\CYP")
ORDER_DIR = VAULT / "外" / "專科考試 l 季考閱片" / "季考閱片_題目順序"
IMAGES_ROOT = VAULT / "外" / "專科考試 l 季考閱片" / "季考閱片_原始圖片"
SITE_DIR = Path(__file__).parent
OUT_IMAGES = SITE_DIR / "images"
OUT_JSON = SITE_DIR / "questions.json"

embed_re = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
fm_re = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


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


# 比照 Obsidian 的 ![[filename]] 解析邏輯：全庫依「檔名」比對，不限定同名資料夾
# （已知資料缺陷：部分圖片被錯放到隔壁題號的資料夾，例如 ST20201138.md 引用的
#  ST2020113801.jpg 實際被放在 ST20201139 資料夾內，Obsidian 仍能正確顯示）
filename_index = {}
duplicate_filenames = set()
for img_path in IMAGES_ROOT.rglob("*"):
    if img_path.is_file() and img_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        if img_path.name in filename_index and filename_index[img_path.name] != img_path:
            duplicate_filenames.add(img_path.name)
        filename_index[img_path.name] = img_path

OUT_IMAGES.mkdir(parents=True, exist_ok=True)

questions = []
missing = []
subject_counts = {}

for f in sorted(ORDER_DIR.glob("ST*.md")):
    try:
        text = f.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    fm, body = parse_frontmatter(text)
    subject = fm.get("科目", "").strip()
    if not subject:
        continue

    embeds = [e.strip() for e in embed_re.findall(body)]
    if not embeds:
        continue

    st_key = f.stem

    resolved = []
    for e in embeds:
        src = filename_index.get(e)
        if src is None:
            missing.append(f"{f.name}: {e}")
            continue
        dest = OUT_IMAGES / src.name
        if not dest.exists():
            dest.write_bytes(src.read_bytes())
        resolved.append(src.name)

    if len(resolved) < 2:
        if resolved:
            missing.append(f"{f.name}: 圖片數量不足 ({len(resolved)})")
        continue

    case_images = resolved[:-1]
    answer_image = resolved[-1]

    questions.append({
        "id": st_key,
        "subject": subject,
        "section": fm.get("Section", ""),
        "year": fm.get("年份", ""),
        "hospital": fm.get("醫院", ""),
        "disputed": fm.get("答案疑慮", "false") == "true",
        "caseImages": case_images,
        "answerImage": answer_image,
    })
    subject_counts[subject] = subject_counts.get(subject, 0) + 1

OUT_JSON.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"共輸出 {len(questions)} 題")
for s, c in sorted(subject_counts.items()):
    print(f"  {s}: {c} 題")
print(f"複製圖片 {len(list(OUT_IMAGES.iterdir()))} 張")
print(f"缺漏/異常 {len(missing)} 筆")
if missing:
    (SITE_DIR / "missing_images.txt").write_text("\n".join(missing), encoding="utf-8")
if duplicate_filenames:
    print(f"⚠ 發現 {len(duplicate_filenames)} 個重複檔名（全庫不同資料夾出現同名圖片，已採用後遍歷到的版本，需人工確認）")
    (SITE_DIR / "duplicate_filenames.txt").write_text("\n".join(sorted(duplicate_filenames)), encoding="utf-8")
