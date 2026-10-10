"""One-off: convert referenced images to WebP (keep originals), print size report."""
import os
import json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "images")

# Only convert images actually referenced by the site
REFERENCED = [
    "icpc1.jpg", "icpc2.jpg", "icpc3.jpg", "icpc4.jpg",
    "ccpc1.jpg", "ccpc2.jpg", "ccpc3.jpg", "ccpc4.jpg",
    "logo.jpg",
    "prize/fuzhou.jpg", "prize/ccpc_nanchang.png", "prize/nanchang.png",
    "prize/xian.png", "prize/wuhan2026.jpg", "prize/shanghai.jpg",
    "prize/harbin.jpg", "prize/ccpc_shanghai2025.jpg", "prize/kunming.jpg",
    "prize/icpc_xian2024.jpg", "prize/icpc_kunming2024.jpg",
    "prize/ccpc_shanghai2024.jpg", "prize/caoxiaolin.jpg", "prize/j2017lbh.png",
    "prize/doroshi.jpg", "prize/cupper.jpg", "prize/alfredgit.jpg",
    "prize/liujunwei.jpg", "prize/moskaunia.jpg", "prize/zhangzb.jpg",
    "prize/sxkane.jpg", "prize/swdjb.jpg",
    "contest/icpc.png", "contest/ccpc.png", "contest/gplt.png",
    "contest/lanqiao.png", "contest/baidu.png", "contest/raicom.png",
    "contest/chuanzhi.png", "contest/mati.png",
]

report = []
total_before = total_after = 0

for rel in REFERENCED:
    src = os.path.join(IMG_DIR, rel)
    if not os.path.exists(src):
        print(f"MISSING: {rel}")
        continue
    dst = os.path.splitext(src)[0] + ".webp"
    with Image.open(src) as im:
        w, h = im.size
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode or "transparency" in im.info else "RGB")
        im.save(dst, "WEBP", quality=82, method=6)
    b, a = os.path.getsize(src), os.path.getsize(dst)
    total_before += b
    total_after += a
    report.append({"file": rel, "w": w, "h": h, "before": b, "after": a})
    print(f"{rel}: {b//1024}KB -> {a//1024}KB ({w}x{h})")

print(f"\nTOTAL: {total_before//1024}KB -> {total_after//1024}KB "
      f"(-{100 - total_after * 100 // total_before}%)")

with open(os.path.join(ROOT, "tools", "webp_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
