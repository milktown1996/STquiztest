# -*- coding: utf-8 -*-
"""
壓縮 images/ 資料夾內的圖片：最長邊縮到 1600px、統一轉成 .jpg（品質 80）。
只處理這個刷題網站專用的 images 資料夾（複製出來的副本），不觸碰 vault 原始圖片。
若原檔名不是小寫 .jpg（例如 .png / .PNG / .JPG），轉檔後會改名為小寫 .jpg，
並同步更新 questions.json 內對應的檔名參照。
"""
import json
from pathlib import Path
from PIL import Image

SITE_DIR = Path(__file__).parent
IMAGES_DIR = SITE_DIR / "images"
QUESTIONS_JSON = SITE_DIR / "questions.json"
MANIFEST = SITE_DIR / "compressed_manifest.json"
MAX_EDGE = 1600
QUALITY = 80

# 已壓縮過的檔案清單：避免每次重建都把全部圖片重新編碼一次
# （重複有損壓縮會累積畫質損失，也很花時間）
if MANIFEST.exists():
    done = set(json.loads(MANIFEST.read_text(encoding="utf-8")))
else:
    done = set()

total_before = 0
total_after = 0
count = 0
skipped = 0
rename_map = {}  # 原檔名 -> 新檔名

for img_path in sorted(IMAGES_DIR.iterdir()):
    if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        continue
    if img_path.name in done:
        skipped += 1
        continue
    before = img_path.stat().st_size
    total_before += before

    new_name = img_path.stem + ".jpg"
    new_path = IMAGES_DIR / new_name

    with Image.open(img_path) as im:
        im = im.convert("RGB") if im.mode in ("RGBA", "P", "LA") else im
        w, h = im.size
        if max(w, h) > MAX_EDGE:
            if w >= h:
                new_w = MAX_EDGE
                new_h = round(h * MAX_EDGE / w)
            else:
                new_h = MAX_EDGE
                new_w = round(w * MAX_EDGE / h)
            im = im.resize((new_w, new_h), Image.LANCZOS)
        im.save(new_path, "JPEG", quality=QUALITY, optimize=True)

    if new_path != img_path:
        img_path.unlink()
        rename_map[img_path.name] = new_name

    after = new_path.stat().st_size
    total_after += after
    count += 1
    done.add(new_path.name)

MANIFEST.write_text(json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8")

print(f"處理 {count} 張圖片（跳過 {skipped} 張先前已壓縮）")
print(f"壓縮前: {total_before / 1024 / 1024:.1f} MB")
print(f"壓縮後: {total_after / 1024 / 1024:.1f} MB")
print(f"改名 {len(rename_map)} 張（非標準小寫 .jpg 副檔名）")

if rename_map:
    data = json.loads(QUESTIONS_JSON.read_text(encoding="utf-8"))
    updated = 0
    for q in data:
        q["caseImages"] = [rename_map.get(n, n) for n in q["caseImages"]]
        new_answer = rename_map.get(q["answerImage"], q["answerImage"])
        if new_answer != q["answerImage"]:
            updated += 1
        q["answerImage"] = new_answer
    QUESTIONS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已同步更新 questions.json 內的檔名參照")
