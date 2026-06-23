#!/usr/bin/env python3
"""교안 .src.md 의 assets/ 이미지 참조를 base64 data URI 로 인라인해 자기완결 .md 를 만든다.

사용: python3 inline_images.py <path/to/lesson.src.md>
출력: 같은 폴더에 <stem>.md (예: lesson.src.md -> lesson.md). 이미지 경로는 src 파일 기준 상대.
"""
import base64
import mimetypes
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("사용: python3 inline_images.py <lesson.src.md>", file=sys.stderr)
        return 1
    src = pathlib.Path(sys.argv[1]).resolve()
    if not src.exists():
        print(f"파일 없음: {src}", file=sys.stderr)
        return 1
    base = src.parent
    text = src.read_text(encoding="utf-8")

    def repl(m: re.Match) -> str:
        alt, rel = m.group(1), m.group(2)
        img = (base / rel).resolve()
        if not img.exists():
            raise SystemExit(f"이미지 없음: {img}")
        mime = mimetypes.guess_type(str(img))[0] or "image/jpeg"
        data = base64.b64encode(img.read_bytes()).decode()
        return f"![{alt}](data:{mime};base64,{data})"

    out = re.sub(r"!\[([^\]]*)\]\(((?!https?:|data:)[^)]+)\)", repl, text)
    # <stem>.src.md -> <stem>.md ; 그 외 *.md -> *.standalone.md
    stem = src.name[:-7] if src.name.endswith(".src.md") else src.stem
    dest = base / f"{stem}.md"
    if dest == src:
        dest = base / f"{stem}.standalone.md"
    dest.write_text(out, encoding="utf-8")
    inlined = out.count("base64,")
    print(f"생성: {dest} ({len(out.encode())} bytes, 이미지 {inlined}장 인라인)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
