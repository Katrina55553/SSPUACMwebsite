#!/usr/bin/env python3
"""检查静态站点资源、数据文件和 JavaScript，供本地及 GitHub Actions 使用。"""

import argparse
import json
import posixpath
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED_FILES = (
    "index.html", "about.html", "hall_of_fame.html", "news.html",
    "xcpc.html", "lanqiao.html", "css/style.css", "css/xcpc.css",
    "js/components.js", "js/main.js", "js/xcpc.js", "js/lanqiao.js",
    "images/logo.webp", "data/sspu-data.json", "data/lanqiao-sspu.json",
)


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value and name in ("href", "src", "poster"):
                self.references.append(value)


def check_site(root):
    errors = []
    # 用相对路径集合检查大小写，避免 Windows 上通过、Linux 上 404。
    paths = list(root.rglob("*"))
    files = {path.relative_to(root).as_posix(): path
             for path in paths if path.is_file()}
    for name in REQUIRED_FILES:
        if name not in files:
            errors.append(f"缺少必要文件: {name}")

    for path in paths:
        if path.is_symlink():
            name = path.relative_to(root).as_posix()
            errors.append(f"发布目录不能包含符号链接: {name}")

    def check_reference(source, reference, base=None):
        url = urlsplit(reference)
        if url.scheme or url.netloc or not url.path:
            return
        decoded = unquote(url.path)
        parent = posixpath.dirname(source) if base is None else base
        target = posixpath.normpath(
            decoded.lstrip("/") if decoded.startswith("/")
            else posixpath.join(parent, decoded)
        )
        if target == ".":
            target = "index.html"
        elif decoded.endswith("/"):
            target = posixpath.join(target, "index.html")
        if target not in files:
            errors.append(f"{source}: 找不到本地资源 {reference}（{target}）")

    for name, path in files.items():
        if name.endswith(".html"):
            parser = ResourceParser()
            parser.feed(path.read_text(encoding="utf-8-sig"))
            for reference in parser.references:
                check_reference(name, reference)
        elif name.endswith(".css"):
            text = path.read_text(encoding="utf-8-sig")
            for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", text):
                check_reference(name, match.group(2).strip())

    # 公共组件中的 HTML 相对路径由网站根目录下的页面解析。
    if "js/components.js" in files:
        parser = ResourceParser()
        parser.feed(files["js/components.js"].read_text(encoding="utf-8-sig"))
        for reference in parser.references:
            check_reference("js/components.js", reference, base="")

    for name, path in files.items():
        if name.endswith(".json"):
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except (ValueError, UnicodeError) as exc:
                errors.append(f"{name}: JSON 无效: {exc}")

    node = shutil.which("node")
    if not node:
        errors.append("找不到 Node.js，无法检查 JavaScript 语法")
    else:
        for name, path in files.items():
            if name.endswith(".js"):
                result = subprocess.run(
                    [node, "--check", str(path)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30,
                )
                if result.returncode:
                    errors.append(f"{name}: JavaScript 语法错误\n{result.stderr.strip()}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default=".", help="站点根目录")
    root = Path(parser.parse_args().directory).resolve()
    if not root.is_dir():
        parser.error(f"目录不存在: {root}")
    errors = check_site(root)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("站点检查通过：本地资源、JSON 和 JavaScript 均正常。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
