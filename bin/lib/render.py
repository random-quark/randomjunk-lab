#!/usr/bin/env python3
"""Render template placeholders with escaping appropriate to each file type.

A single sed expression cannot do this safely: '/' breaks the expression, '&'
re-inserts the match, and HTML, JSON and Python each need different escaping.

    render.py <app-dir> NAME=tetris TITLE='R&D "Lab"' URL=https://...
"""
import html
import json
import pathlib
import re
import sys

BY_SUFFIX = {
    ".html": html.escape,
    ".json": lambda s: json.dumps(s)[1:-1],
    ".webmanifest": lambda s: json.dumps(s)[1:-1],
    ".py": lambda s: json.dumps(s)[1:-1],
    ".js": lambda s: json.dumps(s)[1:-1],
}
TEXT_SUFFIXES = {".html", ".js", ".json", ".webmanifest", ".py", ".md", ".txt",
                 ".toml", ".svg", ".css"}


def main() -> int:
    root = pathlib.Path(sys.argv[1])
    values = dict(arg.split("=", 1) for arg in sys.argv[2:])

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "{{" not in text:
            continue
        escape = BY_SUFFIX.get(path.suffix, lambda s: s)
        text = re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: escape(values[m[1]]) if m[1] in values else m[0], text)
        path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
