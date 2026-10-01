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
TOPIC_DIR = VAULT / "外" / "專科考試 l 季考閱片" / "季考閱片_題目整理"
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

# 建立「題號 -> 診斷名稱」對照表：掃描 季考閱片_題目整理 資料夾內每個 ST_疾病.md，
# 其 frontmatter Disease 欄位即診斷名稱，內文 ![[STyyyymmddNN]] 即對應的題號
diagnosis_index = {}
id_embed_re = re.compile(r"!\[\[(ST\d{8,10})\]\]")
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

OUT_IMAGES.mkdir(parents=True, exist_ok=True)

questions = []
missing = []
subject_counts = {}

for f in sorted(ORDER_DIR.glob("*.md")):
    try:
        text = f.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    fm, body = parse_frontmatter(text)
    subject = fm.get("科目", "").strip()
    is_exchange = "交換" in f.stem

    # 部分檔案（尤其交換題）內文把同一組 embed 重複貼了兩次（複製貼上失誤），
    # 依序去除重複檔名，保留原始出現順序
    raw_embeds = [e.strip() for e in embed_re.findall(body)]
    embeds = list(dict.fromkeys(raw_embeds))
    if not embeds:
        continue

    st_key = f.stem

    resolved = []
    resolved_paths = []
    for e in embeds:
        src = filename_index.get(e)
        if src is None:
            missing.append(f"{f.name}: {e}")
            continue
        # 增量處理：compress_images.py 會把圖片統一壓縮並改名為小寫 .jpg，
        # 若該版本已存在就直接沿用，不重新從 vault 複製原始大圖
        compressed = OUT_IMAGES / (Path(src.name).stem + ".jpg")
        dest = OUT_IMAGES / src.name
        if compressed.exists():
            resolved.append(compressed.name)
        elif dest.exists():
            resolved.append(dest.name)
        else:
            dest.write_bytes(src.read_bytes())
            resolved.append(dest.name)
        resolved_paths.append(src)

    if len(resolved) < 2:
        if resolved:
            missing.append(f"{f.name}: 圖片數量不足 ({len(resolved)})")
        continue

    year = fm.get("年份", "")
    hospital = fm.get("醫院", "")

    if not subject:
        if is_exchange:
            subject = "交換"
        else:
            # 無 frontmatter 的題目（如 2026 年新增一批）：從圖片所在資料夾
            # 名稱「YYYYMM 醫院」反推年份/院區，科目標記為「未分類」待日後人工補標
            subject = "未分類"
            hosp_dir_name = resolved_paths[0].parent.parent.name  # .../<YYYYMM 醫院>/<STkey>/img
            m = re.match(r"(\d{6})\s*(.+)", hosp_dir_name)
            if m:
                year = year or m.group(1)
                hospital = hospital or m.group(2)

    case_images = resolved[:-1]
    answer_image = resolved[-1]

    questions.append({
        "id": st_key,
        "subject": subject,
        "section": fm.get("Section", ""),
        "year": year,
        "hospital": hospital,
        "disputed": fm.get("答案疑慮", "false") == "true",
        "isExchange": is_exchange,
        "diagnosis": diagnosis_index.get(st_key, ""),
        "caseImages": case_images,
        "answerImage": answer_image,
    })
    subject_counts[subject] = subject_counts.get(subject, 0) + 1

OUT_JSON.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

matched_dx = sum(1 for q in questions if q["diagnosis"])
print(f"共輸出 {len(questions)} 題（其中 {matched_dx} 題有對照到診斷名稱）")
for s, c in sorted(subject_counts.items()):
    print(f"  {s}: {c} 題")
print(f"複製圖片 {len(list(OUT_IMAGES.iterdir()))} 張")
print(f"缺漏/異常 {len(missing)} 筆")
if missing:
    (SITE_DIR / "missing_images.txt").write_text("\n".join(missing), encoding="utf-8")
if duplicate_filenames:
    print(f"⚠ 發現 {len(duplicate_filenames)} 個重複檔名（全庫不同資料夾出現同名圖片，已採用後遍歷到的版本，需人工確認）")
    (SITE_DIR / "duplicate_filenames.txt").write_text("\n".join(sorted(duplicate_filenames)), encoding="utf-8")
