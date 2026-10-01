"""
دليل الاستخدام: ملف لكل لغة في مجلد docs، يُعرض داخل البرنامج نصاً عادياً
(بدون رموز التنسيق مثل # و ** حتى لا ينطقها قارئ الشاشة).
"""
import os
import re

from core.paths import RESOURCE_DIR

DOCS_DIR = os.path.join(RESOURCE_DIR, "docs")


def guide_path(language):
    path = os.path.join(DOCS_DIR, f"guide_{language}.md")
    return path if os.path.isfile(path) else os.path.join(DOCS_DIR, "guide_ar.md")


def markdown_to_text(md):
    lines = []
    for line in md.splitlines():
        heading = re.match(r"^(#+)\s*(.*)$", line)
        if heading:
            # العناوين على سطر مستقل بعد سطر فارغ، فتسهل القراءة بالأسهم
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(heading.group(2).strip())
            continue
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)   # **غامق**
        line = line.replace("`", "")                   # `اختصار`
        line = re.sub(r"^\s*[-*]\s+", "• ", line)      # عناصر القوائم
        lines.append(line.rstrip())
    return "\n".join(lines).strip() + "\n"


def load_guide(language):
    try:
        with open(guide_path(language), encoding="utf-8") as f:
            return markdown_to_text(f.read())
    except OSError:
        return ""
