from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin, PdfImagePlugin


# Importing these modules registers Pillow's PDF and JPEG save handlers.
assert PdfImagePlugin is not None
assert JpegImagePlugin is not None


PAGE_WIDTH = 1654
PAGE_HEIGHT = 2339
MARGIN_X = 120
MARGIN_TOP = 110
MARGIN_BOTTOM = 110
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)
HEADER_HEIGHT = 48
FOOTER_HEIGHT = 56

TITLE_SIZE = 58
SUBTITLE_SIZE = 34
H1_SIZE = 40
H2_SIZE = 34
H3_SIZE = 30
BODY_SIZE = 25
SMALL_SIZE = 21
LINE_GAP = 10
PARAGRAPH_GAP = 18
SECTION_GAP = 26
IMAGE_MAX_HEIGHT = 620

OUTPUT_PATH = Path("docs/generated/XMeta_Console_GUI_User_Manual.pdf")
MANUAL_PATH = Path("docs/user_manual.md")


@dataclass
class Block:
    kind: str
    text: str = ""
    rows: list[list[str]] | None = None


@dataclass
class ManualMeta:
    title: str
    version: str
    updated: str
    headings: list[tuple[int, str]]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates: list[str] = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = load_font(TITLE_SIZE, bold=True)
FONT_SUBTITLE = load_font(SUBTITLE_SIZE)
FONT_H1 = load_font(H1_SIZE, bold=True)
FONT_H2 = load_font(H2_SIZE, bold=True)
FONT_H3 = load_font(H3_SIZE, bold=True)
FONT_BODY = load_font(BODY_SIZE)
FONT_BODY_BOLD = load_font(BODY_SIZE, bold=True)
FONT_SMALL = load_font(SMALL_SIZE)
FONT_SMALL_BOLD = load_font(SMALL_SIZE, bold=True)


def strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text


def parse_markdown(path: Path) -> tuple[ManualMeta, list[Block]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[Block] = []
    headings: list[tuple[int, str]] = []
    title = "XMeta Console GUI User Manual"
    version = ""
    updated = ""
    index = 0

    while index < len(lines):
        raw = lines[index].rstrip()
        line = raw.strip()
        if not line:
            blocks.append(Block("blank"))
            index += 1
            continue
        if line.startswith("> Version:"):
            version = line.split(":", 1)[1].strip()
            blocks.append(Block("meta", f"Version: {version}"))
            index += 1
            continue
        if line.startswith("> Last Updated:"):
            updated = line.split(":", 1)[1].strip()
            blocks.append(Block("meta", f"Last Updated: {updated}"))
            index += 1
            continue
        if line.startswith("# "):
            title = strip_markdown(line[2:].strip())
            blocks.append(Block("title", title))
            index += 1
            continue
        if line.startswith("## "):
            heading = strip_markdown(line[3:].strip())
            headings.append((2, heading))
            blocks.append(Block("h1", heading))
            index += 1
            continue
        if line.startswith("### "):
            heading = strip_markdown(line[4:].strip())
            headings.append((3, heading))
            blocks.append(Block("h2", heading))
            index += 1
            continue
        if line.startswith("#### "):
            heading = strip_markdown(line[5:].strip())
            blocks.append(Block("h3", heading))
            index += 1
            continue
        if line.startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index].rstrip())
                index += 1
            blocks.append(Block("code", "\n".join(code_lines)))
            index += 1
            continue
        if line.startswith("!["):
            target = line.split("(", 1)[1].rsplit(")", 1)[0]
            caption = line.split("]", 1)[0][2:].strip()
            blocks.append(Block("image", target))
            if caption:
                blocks.append(Block("caption", caption))
            index += 1
            continue
        if line.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = parse_table(table_lines)
            if rows:
                blocks.append(Block("table", rows=rows))
            continue
        if line.startswith("- "):
            blocks.append(Block("bullet", strip_markdown(line[2:].strip())))
            index += 1
            continue
        if re.match(r"^\d+\.\s+", line):
            blocks.append(Block("number", strip_markdown(line)))
            index += 1
            continue
        blocks.append(Block("p", strip_markdown(line)))
        index += 1

    meta = ManualMeta(title=title, version=version, updated=updated, headings=headings)
    return meta, blocks


def parse_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [strip_markdown(cell.strip()) for cell in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def text_width(text: str, font: ImageFont.FreeTypeFont) -> float:
    dummy = Image.new("RGB", (10, 10), "white")
    draw = ImageDraw.Draw(dummy)
    return draw.textlength(text, font=font)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    if not text:
        return [""]
    output: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            output.append("")
            continue
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if text_width(trial, font) <= width:
                current = trial
                continue
            if current:
                output.append(current)
                current = word
            else:
                output.extend(split_long_word(word, font, width))
                current = ""
        if current:
            output.append(current)
    return output


def split_long_word(word: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for char in word:
        trial = current + char
        if text_width(trial, font) <= width:
            current = trial
        else:
            if current:
                parts.append(current)
            current = char
    if current:
        parts.append(current)
    return parts


def line_height(font: ImageFont.FreeTypeFont) -> int:
    bbox = font.getbbox("Ag")
    return bbox[3] - bbox[1] + LINE_GAP


class PdfRenderer:
    def __init__(self, meta: ManualMeta, source_path: Path, output_path: Path):
        self.meta = meta
        self.source_path = source_path
        self.output_path = output_path
        self.pages: list[Image.Image] = []
        self.page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.page)
        self.y = MARGIN_TOP
        self.page_number = 0

    def save(self) -> None:
        self.finish_page()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        rgb_pages = [page.convert("RGB") for page in self.pages]
        rgb_pages[0].save(self.output_path, save_all=True, append_images=rgb_pages[1:])

    def finish_page(self) -> None:
        if self.page is None:
            return
        self.draw_footer()
        self.pages.append(self.page)

    def new_page(self) -> None:
        self.finish_page()
        self.page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.page)
        self.y = MARGIN_TOP + HEADER_HEIGHT
        self.page_number += 1
        self.draw_header()

    def draw_header(self) -> None:
        self.draw.text((MARGIN_X, MARGIN_TOP - 42), self.meta.title, font=FONT_SMALL_BOLD, fill="#3A4658")
        self.draw.line(
            (MARGIN_X, MARGIN_TOP - 8, PAGE_WIDTH - MARGIN_X, MARGIN_TOP - 8),
            fill="#C9D2DF",
            width=2,
        )

    def draw_footer(self) -> None:
        footer_y = PAGE_HEIGHT - MARGIN_BOTTOM + 35
        self.draw.line((MARGIN_X, footer_y - 20, PAGE_WIDTH - MARGIN_X, footer_y - 20), fill="#D8DEE8", width=2)
        if self.page_number > 0:
            self.draw.text((MARGIN_X, footer_y), self.meta.version, font=FONT_SMALL, fill="#5F6B7A")
            page_text = f"Page {self.page_number}"
            self.draw.text(
                (PAGE_WIDTH - MARGIN_X - text_width(page_text, FONT_SMALL), footer_y),
                page_text,
                font=FONT_SMALL,
                fill="#5F6B7A",
            )

    def cover_page(self) -> None:
        self.page_number = 0
        self.page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "#F5F7FA")
        self.draw = ImageDraw.Draw(self.page)
        self.draw.rectangle((0, 0, PAGE_WIDTH, 210), fill="#233142")
        self.draw.rectangle((0, 210, PAGE_WIDTH, 230), fill="#4F8CC9")
        self.draw.text((MARGIN_X, 360), self.meta.title, font=FONT_TITLE, fill="#17212B")
        subtitle = "Operations manual for run monitoring, dependency tracing, file inspection, and target actions"
        for line in wrap_text(subtitle, FONT_SUBTITLE, CONTENT_WIDTH):
            self.draw.text((MARGIN_X, 455), line, font=FONT_SUBTITLE, fill="#364656")
            self.y = 455 + line_height(FONT_SUBTITLE)
        info_y = 660
        self.draw.text((MARGIN_X, info_y), self.meta.version, font=FONT_H2, fill="#233142")
        self.draw.text((MARGIN_X, info_y + 56), f"Last Updated: {self.meta.updated}", font=FONT_BODY, fill="#4F5D6E")
        self.draw.text((MARGIN_X, PAGE_HEIGHT - 260), "XMeta Console GUI", font=FONT_H2, fill="#233142")
        self.draw.text((MARGIN_X, PAGE_HEIGHT - 208), "PyQt5 desktop console for EDA execution runs", font=FONT_BODY, fill="#4F5D6E")
        self.pages.append(self.page)
        self.page_number = 0
        self.new_page()

    def table_of_contents(self) -> None:
        self.add_text("Table Of Contents", FONT_H1, "#17212B", gap=34)
        for level, heading in self.meta.headings:
            if level == 2:
                indent = 0
                font = FONT_BODY_BOLD
            else:
                indent = 34
                font = FONT_SMALL
            self.add_text(heading, font, "#303C4D", indent=indent, gap=10)
        self.new_page()

    def ensure_space(self, needed: int) -> None:
        if self.y + needed <= PAGE_HEIGHT - MARGIN_BOTTOM - FOOTER_HEIGHT:
            return
        self.new_page()

    def add_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: str = "#1F2933",
        indent: int = 0,
        gap: int = PARAGRAPH_GAP,
    ) -> None:
        lines = wrap_text(text, font, CONTENT_WIDTH - indent)
        height = len(lines) * line_height(font) + gap
        self.ensure_space(height)
        for line in lines:
            self.draw.text((MARGIN_X + indent, self.y), line, font=font, fill=fill)
            self.y += line_height(font)
        self.y += gap

    def add_code(self, text: str) -> None:
        lines = text.splitlines() or [""]
        font = FONT_SMALL
        height = len(lines) * line_height(font) + 32
        self.ensure_space(height)
        self.draw.rounded_rectangle(
            (MARGIN_X, self.y, PAGE_WIDTH - MARGIN_X, self.y + height),
            radius=12,
            fill="#F0F3F7",
            outline="#D5DEE9",
            width=2,
        )
        code_y = self.y + 16
        for line in lines:
            self.draw.text((MARGIN_X + 22, code_y), line, font=font, fill="#253241")
            code_y += line_height(font)
        self.y += height + PARAGRAPH_GAP

    def add_table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        columns = max(len(row) for row in rows)
        col_width = CONTENT_WIDTH // columns
        font = FONT_SMALL
        row_lines: list[list[list[str]]] = []
        row_heights: list[int] = []
        for row in rows:
            wrapped_cells: list[list[str]] = []
            max_lines = 1
            for cell in row:
                wrapped = wrap_text(cell, font, col_width - 24)
                wrapped_cells.append(wrapped)
                max_lines = max(max_lines, len(wrapped))
            row_lines.append(wrapped_cells)
            row_heights.append(max_lines * line_height(font) + 22)
        total_height = sum(row_heights)
        self.ensure_space(total_height + PARAGRAPH_GAP)
        y = self.y
        for row_index, wrapped_cells in enumerate(row_lines):
            row_height = row_heights[row_index]
            fill = "#E7EEF7" if row_index == 0 else ("#FFFFFF" if row_index % 2 else "#F8FAFC")
            self.draw.rectangle((MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y + row_height), fill=fill, outline="#CDD6E3")
            for col_index, lines in enumerate(wrapped_cells):
                x = MARGIN_X + col_index * col_width
                self.draw.line((x, y, x, y + row_height), fill="#CDD6E3", width=1)
                cell_font = FONT_SMALL_BOLD if row_index == 0 else font
                line_y = y + 11
                for line in lines:
                    self.draw.text((x + 12, line_y), line, font=cell_font, fill="#263241")
                    line_y += line_height(cell_font)
            self.draw.line((PAGE_WIDTH - MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y + row_height), fill="#CDD6E3", width=1)
            y += row_height
        self.y = y + PARAGRAPH_GAP

    def add_image(self, target: str) -> None:
        image_path = self.source_path.parent / target
        if not image_path.exists():
            self.add_text(f"Missing image: {target}", FONT_SMALL, "#9B2C2C")
            return
        image = Image.open(image_path).convert("RGB")
        ratio = min(CONTENT_WIDTH / image.width, IMAGE_MAX_HEIGHT / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.LANCZOS)
        needed = new_size[1] + 30
        self.ensure_space(needed)
        x = MARGIN_X + (CONTENT_WIDTH - new_size[0]) // 2
        self.draw.rectangle((x - 2, self.y - 2, x + new_size[0] + 2, self.y + new_size[1] + 2), outline="#CBD5E1", width=2)
        self.page.paste(image, (x, self.y))
        self.y += new_size[1] + 24

    def render_blocks(self, blocks: list[Block]) -> None:
        skip_kinds = {"title", "meta"}
        for block in blocks:
            if block.kind in skip_kinds:
                continue
            if block.kind == "blank":
                self.y += 6
            elif block.kind == "h1":
                self.ensure_space(90)
                self.y += 8
                self.add_text(block.text, FONT_H1, "#17212B", gap=SECTION_GAP)
            elif block.kind == "h2":
                self.add_text(block.text, FONT_H2, "#233142", gap=SECTION_GAP)
            elif block.kind == "h3":
                self.add_text(block.text, FONT_H3, "#2D3B4F", gap=PARAGRAPH_GAP)
            elif block.kind == "p":
                self.add_text(block.text, FONT_BODY)
            elif block.kind == "bullet":
                self.add_text(f"- {block.text}", FONT_BODY, indent=18, gap=10)
            elif block.kind == "number":
                self.add_text(block.text, FONT_BODY, indent=18, gap=10)
            elif block.kind == "code":
                self.add_code(block.text)
            elif block.kind == "table":
                self.add_table(block.rows or [])
            elif block.kind == "image":
                self.add_image(block.text)
            elif block.kind == "caption":
                self.add_text(block.text, FONT_SMALL, "#5F6B7A", indent=18, gap=SECTION_GAP)


def build_pdf(markdown_path: Path, output_path: Path) -> None:
    meta, blocks = parse_markdown(markdown_path)
    renderer = PdfRenderer(meta, markdown_path, output_path)
    renderer.cover_page()
    renderer.table_of_contents()
    renderer.render_blocks(blocks)
    renderer.save()


def main() -> int:
    markdown_path = Path(sys.argv[1]) if len(sys.argv) > 1 else MANUAL_PATH
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT_PATH
    build_pdf(markdown_path, output_path)
    print(f"Wrote PDF manual to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
