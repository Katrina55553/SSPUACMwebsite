"""One-off: point <img> refs at .webp files and add lazy/async loading attributes."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = ["index.html", "about.html", "hall_of_fame.html", "js/components.js"]

def add_attrs(tag: str, is_js: bool) -> str:
    if "images/" not in tag or "loading=" in tag:
        return tag
    if is_js:
        return tag  # header logo is above the fold on every page
    # First hero slide on the home page is the LCP element: load eagerly
    if 'alt="2026 CCPC 全国邀请赛（福州）"' in tag:
        return tag.replace("<img ", '<img fetchpriority="high" decoding="async" ', 1)
    return tag.replace("<img ", '<img loading="lazy" decoding="async" ', 1)

for rel in FILES:
    path = os.path.join(ROOT, rel)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r"(images/(?:prize/|contest/)?[^\"']+)\.(?:jpg|png)", r"\1.webp", content)
    content = re.sub(r"<img [^>]*>", lambda m: add_attrs(m.group(0), rel.endswith(".js")), content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"updated {rel}")
