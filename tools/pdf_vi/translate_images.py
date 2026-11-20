"""Dịch chữ Hán nằm trong ảnh nhúng của các PDF đã dịch (``*.vi.pdf``).

Quy trình mỗi ảnh: OCR (RapidOCR) → chỉ giữ ô có chữ Hán → dịch bằng Google
(kèm bảng thuật ngữ của translate.py) → tô lại nền gốc → vẽ tiếng Việt vừa khung
→ thay ảnh trong PDF. Ảnh không có chữ Hán (logo, ảnh chụp, watermark) không bị đụng.

Dùng:
    python tools/pdf_vi/translate_images.py documents/chapter1/dive-into-llm.vi.pdf [--apply]
    python tools/pdf_vi/translate_images.py --all --apply
"""
import io
import json
import os
import re
import sys

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "images.json")
OCR_CACHE = os.path.join(HERE, "cache", "ocr.json")

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
FONTS = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
]
FONT_PATH = next((f for f in FONTS if os.path.exists(f)), None)

_ocr = None


def ocr_engine():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def _load(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, path)


def ocr_image(key, im):
    """Trả về list (bbox, text, score); có cache theo xref."""
    cache = _load(OCR_CACHE)
    if key in cache:
        return [tuple(b) for b in cache[key]]
    res, _ = ocr_engine()(np.array(im.convert("RGB")))
    out = []
    for box, text, score in res or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append(([int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))], text, float(score)))
    cache[key] = out
    _save(OCR_CACHE, cache)
    return out


def _ring_color(arr, box, pad=3):
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    ring = np.concatenate([
        arr[max(0, y0 - 2):y0 + 1, x0:x1].reshape(-1, 3),
        arr[y1:min(h, y1 + 3), x0:x1].reshape(-1, 3),
        arr[y0:y1, max(0, x0 - 2):x0 + 1].reshape(-1, 3),
        arr[y0:y1, x1:min(w, x1 + 3)].reshape(-1, 3),
    ])
    if not len(ring):
        return (255, 255, 255)
    return tuple(int(v) for v in np.median(ring, axis=0))


def _text_color(arr, box):
    x0, y0, x1, y1 = box
    crop = arr[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3)
    if not len(crop):
        return (0, 0, 0)
    lum = crop.mean(axis=1)
    dark = crop[lum <= np.percentile(lum, 25)]
    return tuple(int(v) for v in np.median(dark, axis=0)) if len(dark) else (0, 0, 0)


def _fit_font(draw, text, box_w, box_h, max_size=None):
    size = max_size or max(6, int(box_h * 1.05))
    size = min(size, int(box_w / max(1, len(text)) * 1.9) + 4)
    while size > 5:
        font = ImageFont.truetype(FONT_PATH, size)
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        if (r - l) <= box_w * 0.98 and (b - t) <= box_h * 1.25:
            return font
        size -= 1
    return ImageFont.truetype(FONT_PATH, 5)


def redraw(im, items):
    """items: [(box, text_vi)] — tô nền gốc rồi vẽ tiếng Việt."""
    im = im.convert("RGB")
    arr = np.array(im)
    draw = ImageDraw.Draw(im)
    for box, text in sorted(items, key=lambda it: (it[0][1], it[0][0])):
        x0, y0, x1, y1 = box
        bg = _ring_color(arr, box)
        fg = _text_color(arr, box)
        draw.rectangle([x0, y0, x1, y1], fill=bg)
        font = _fit_font(draw, text, max(1, x1 - x0), max(1, y1 - y0))
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        draw.text((x0 + (x1 - x0 - (r - l)) / 2 - l, y0 + (y1 - y0 - (b - t)) / 2 - t),
                  text, font=font, fill=fg)
    return im


def process_image(key, png_bytes):
    im = Image.open(io.BytesIO(png_bytes))
    if im.width < 120 or im.height < 60:
        return None, 0
    lines = ocr_image(key, im)
    todo = [ln for ln in lines if CJK_RE.search(ln[1]) and ln[2] >= 0.5]
    if not todo:
        return None, 0

    cache = _load(CACHE)
    items = []
    for box, text, _ in todo:
        ck = "zh|" + text.strip()
        if ck in cache:
            vi = cache[ck]
        else:
            raw = T.safe_translate(text.strip()) or ""
            vi = T.split_inference(text, T.polish(raw.strip())) if raw.strip() else ""
            if vi:
                cache[ck] = vi
                _save(CACHE, cache)
        if vi and not CJK_RE.search(vi):
            items.append((box, vi))
    if not items:
        return None, 0
    out = redraw(im, items)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue(), len(items)


def process_pdf(path, apply=False):
    doc = pymupdf.open(path)
    done = {}
    total = 0
    for pno in range(len(doc)):
        page = doc[pno]
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in done:
                continue
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            key = "%s|%d" % (os.path.basename(path), xref)
            new, n = process_image(key, info["image"])
            done[xref] = n
            if not new:
                continue
            total += n
            print("  p%d xref=%d: %d nhãn" % (pno + 1, xref, n))
            if apply:
                try:
                    page.replace_image(xref, stream=new)
                except Exception as e:
                    print("    ! thay ảnh lỗi:", e)
    print("%s: %d nhãn trong ảnh%s" % (path, total, "" if apply else " (chạy thử)"))
    if apply and total:
        tmp = path + ".tmp"
        doc.save(tmp, garbage=3, deflate=True)
        doc.close()
        os.replace(tmp, path)
    else:
        doc.close()
    return total


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if "--all" in sys.argv:
        files = sorted(p for p in __import__("glob").glob("documents/*/*.vi.pdf"))
    else:
        files = args
    grand = 0
    for f in files:
        grand += process_pdf(f, apply=apply)
    print("TỔNG:", grand, "nhãn")


if __name__ == "__main__":
    main()
