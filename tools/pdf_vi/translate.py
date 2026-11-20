"""
Dịch PDF giữ nguyên bố cục: hình ảnh, công thức, bảng biểu, vị trí chữ.

Cách làm: đọc từng span văn bản kèm toạ độ/font/màu, dịch theo dòng (gộp các
dòng cùng đoạn), che vùng chữ gốc bằng màu nền lấy từ chính trang (redaction
chỉ xoá chữ, không xoá ảnh/line art), rồi chèn tiếng Việt vào đúng khung với
cỡ chữ tự co để không tràn.

Dùng:
  python translate.py FILE.pdf [--out X.pdf] [--pages 1-5] [--render 4]
  python translate.py FILE.pdf --dry-run
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request

import pymupdf

CJK = re.compile(r"[\u3400-\u9fff]")
MATH_FONT = re.compile(r"(CambriaMath|Symbol|MTExtra|MathType|STIX|LatinModernMath|Asana|Euclid)", re.I)
MONO_FONT = re.compile(r"(Consol|Courier|Mono|Menlo|Code|Inconsolata|Hack|Fixedsys)", re.I)
URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.I)
NUMBERISH = re.compile(r"^[\s\d\W_]+$")

FONT_REG = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
if not os.path.exists(FONT_REG):
    FONT_REG = "C:/Windows/Fonts/segoeui.ttf"
    FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "translations.json")
_lock = threading.Lock()
_cache = {}
_fonts = {}


def load_cache():
    global _cache
    if os.path.exists(CACHE_PATH):
        try:
            _cache = json.load(open(CACHE_PATH, encoding="utf-8"))
        except Exception:
            _cache = {}


def save_cache():
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with _lock:
        data = dict(_cache)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    os.replace(tmp, CACHE_PATH)


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _clients5(text, sl, tl):
    q = urllib.parse.quote(text)
    body = _fetch(f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={sl}&tl={tl}&q={q}")
    data = json.loads(body)
    if isinstance(data, list):
        if data and isinstance(data[0], str):
            return "".join(data)
        if data and isinstance(data[0], list):
            return "".join(seg[0] for seg in data[0] if seg)
    if isinstance(data, dict):
        if "sentences" in data:
            return "".join(s.get("trans", "") for s in data["sentences"])
        if "trans" in data:
            return data["trans"]
    raise ValueError("unexpected clients5 payload")


def _gtx(text, sl, tl):
    q = urllib.parse.quote(text)
    body = _fetch("https://translate.googleapis.com/translate_a/single"
                  f"?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}")
    data = json.loads(body)
    return "".join(seg[0] for seg in data[0] if seg and seg[0])


def _mymemory(text, sl, tl):
    if len(text.encode("utf-8")) > 480:
        raise ValueError("too long for mymemory")
    q = urllib.parse.quote(text)
    body = _fetch(f"https://api.mymemory.translated.net/get?q={q}&langpair={sl}|{tl}")
    data = json.loads(body)
    out = data["responseData"]["translatedText"]
    if not out or out.upper() == text.upper():
        raise ValueError("empty")
    return out


PROVIDERS = [_clients5, _gtx, _mymemory]


def _google(text, sl, tl="vi", attempts=3):
    last = None
    for i in range(attempts):
        for fn in PROVIDERS:
            try:
                out = fn(text, sl, tl)
                if out and out.strip():
                    return out
            except Exception as e:
                last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"translate failed: {last}")


# Bản dịch cố định cho tiêu đề và cụm thuật ngữ (máy dịch hay làm sai nghĩa).
OVERRIDES = {
    "大模型": "LLM",
    "大模型技术与发展": "Công nghệ và phát triển LLM",
    "提示学习与思维链": "Prompt learning và Chain-of-Thought",
    "大模型智能体安全": "An toàn agent LLM",
    "大模型内容安全与越狱攻击": "An toàn nội dung và tấn công jailbreak với LLM",
    "动手学大模型隐写": "Thực hành steganography với LLM",
    "动手学大模型对齐": "Thực hành alignment với LLM",
    "LLM 数学推理": "Suy luận toán học với LLM",
    "图形用户界面自主智能体": "Agent tự chủ trên giao diện đồ hoạ (GUI agent)",
    "大模型智能体": "LLM agent",
    "多模态大模型": "LLM multimodal",
    "垂域大模型": "LLM chuyên ngành",
    "领域数据": "domain data",
    "智能体": "agent",
}


def translate(text):
    key = text.strip()
    if not key:
        return ""
    if key in OVERRIDES:
        return OVERRIDES[key]
    sl = "zh-CN" if CJK.search(key) else "en"
    ck = f"{sl}|{key}"
    with _lock:
        hit = _cache.get(ck)
    if hit is not None:
        return hit
    out = _google(key, sl)
    time.sleep(0.12)
    with _lock:
        _cache[ck] = out
        n = len(_cache)
    if n % 50 == 0:
        save_cache()
    return out


# Giữ thuật ngữ chuyên ngành ở dạng tiếng Anh theo quy tắc dịch.
# (thứ tự quan trọng: cụm dài phải đứng trước cụm ngắn)
VI2EN = [
    (r"suy luận công thức", "dẫn xuất công thức"),
    (r"đại lý người mẫu lớn", "LLM agent"),
    (r"dữ liệu tên miền", "domain data"),
    (r"đại lý", "agent"),
    (r"chuỗi gợi ý tư duy", "Chain-of-Thought (CoT) prompting"),
    (r"chuỗi tư duy", "Chain-of-Thought (CoT)"),
    (r"mô hình ngôn ngữ lớn", "LLM"),
    (r"mô hình lớn", "LLM"),
    (r"mã thông báo", "token"),
    (r"hình mờ", "watermark"),
    (r"kỹ thuật giấu tin", "steganography"),
    (r"thuật giấu tin", "steganography"),
    (r"chỉnh sửa kiến thức", "knowledge editing"),
    (r"chỉnh sửa tri thức", "knowledge editing"),
    (r"lý luận toán học", "suy luận toán học"),
    (r"học gợi ý", "prompt learning"),
    (r"kỹ thuật gợi ý", "prompting"),
    (r"học theo ngữ cảnh", "in-context learning"),
    (r"học ít mẫu", "few-shot learning"),
    (r"học không mẫu", "zero-shot learning"),
    (r"mô hình mã hóa", "encoder model"),
    (r"mô hình giải mã", "decoder model"),
    (r"bộ mã hóa", "encoder"),
    (r"bộ giải mã", "decoder"),
    (r"tinh chỉnh", "fine-tuning"),
    (r"đào tạo trước", "pre-training"),
    (r"sau đào tạo", "post-training"),
    (r"đa phương thức", "multimodal"),
    (r"căn chỉnh", "alignment"),
    (r"học tăng cường", "reinforcement learning"),
    (r"chưng cất", "distillation"),
    (r"điểm chuẩn", "benchmark"),
    (r"bộ dữ liệu", "dataset"),
    (r"tác tử", "agent"),
]


def _repl(m, rep):
    return rep[:1].upper() + rep[1:] if m.start() == 0 else rep


# quy tắc regex (VI2EN ở trên là chuỗi literal, được escape)
REGEX_RULES = [
    (r"(?:lập luận\s+)?chuỗi (?:suy nghĩ|tư duy|lập luận|suy luận)", "Chain-of-Thought (CoT)"),
]


def polish(s):
    s = s.replace("\u00a0", " ").replace("\u2009", " ").replace("\u200b", "")
    s = re.sub(r"\s*\(\s*(?:thuật tin|thuật giấu tin|thủy vân)\s*\)", "", s)
    for pat, rep in REGEX_RULES:
        s = re.sub(r"(?i)(?<![\w-])" + pat + r"(?![\w-])", rep, s)
    for term, rep in VI2EN:
        s = re.sub(r"(?i)(?<![\w-])" + re.escape(term) + r"(?![\w-])", lambda m, r=rep: _repl(m, r), s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


# 推理 trong slide có hai nghĩa: inference (quá trình sinh token) và reasoning (suy luận logic).
INFER_CUES = (
    "推理过程", "推理时", "推理阶段", "推理速度", "推理成本", "推理延迟", "推理服务",
    "推理引擎", "推理开销", "推理效率", "模型推理", "推理加速", "推理框架", "推理部署",
    "推理次数", "推理吞吐", "推理显存", "推理优化", "生成式隐写",
)
REASON_CUES = (
    "数学推理", "逻辑推理", "推理能力", "多步推理", "推理链", "思维链", "推理基准",
    "推理任务", "推理路径", "推理步骤", "推理错误", "推理质量", "推理结果", "推理模型",
    "自然语言推理", "推理数据", "语言推理", "常识推理", "视觉推理", "代码推理",
    "因果推理", "空间推理", "符号推理", "推理性能提升",
)

def _sense(zh, bias):
    inf = sum(zh.count(c) for c in INFER_CUES)
    rea = sum(zh.count(c) for c in REASON_CUES)
    if rea > inf:
        return "reasoning"
    if inf > rea:
        return "inference"
    return bias or "inference"


# Tên bài báo / trích dẫn tiếng Anh: giữ nguyên, không dịch
CITE_RE = re.compile(r"\[(?:C|J|M|D|R)\]//|\bet al\b|\barXiv:\d{4}\.\d{4,5}|(?:19|20)\d{2}\[\d+\]")


def is_citation(text):
    return CJK.search(text) is None and CITE_RE.search(text) is not None


def split_inference(zh, vi, bias=None):
    """Đổi cách dịch 推理 sang inference/reasoning theo ngữ cảnh câu gốc."""
    if CJK.search(zh) is None:
        # nguồn tiếng Anh: bám theo từ gốc
        if re.search(r"(?i)\breasoning\b", zh):
            vi = re.sub(r"(?i)(?<![\w-])suy luận(?![\w-])", "reasoning", vi)
        elif re.search(r"(?i)\binference\b", zh):
            vi = re.sub(r"(?i)(?<![\w-])suy luận(?![\w-])", "inference", vi)
        return vi
    if "推理" not in zh and "推断" not in zh:
        return vi
    if "思维链" in zh:
        vi = re.sub(
            r"(?i)(?:lập luận\s+)?chuỗi (?:suy nghĩ|tư duy|lập luận|suy luận)",
            "Chain-of-Thought (CoT)", vi)
    term = _sense(zh, bias)
    for w in ("suy luận", "lý luận", "lập luận", "suy diễn"):
        vi = re.sub(
            r"(?i)(?<![\w-])" + re.escape(w) + r"(?![\w-])",
            lambda m: term.capitalize() if m.start() == 0 else term, vi)
    return vi


def safe_translate(text):
    try:
        return translate(text)
    except Exception:
        return None


def get_font(bold):
    path = FONT_BOLD if bold else FONT_REG
    if path not in _fonts:
        _fonts[path] = pymupdf.Font(fontfile=path)
    return _fonts[path]


def wrap(text, font, size, width):
    words = text.split()
    if not words:
        return []
    lines, cur = [], words[0]
    for w in words[1:]:
        cand = cur + " " + w
        if font.text_length(cand, size) <= width:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def bbox_union(rects):
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[2] for r in rects)
    y1 = max(r[3] for r in rects)
    return pymupdf.Rect(x0, y0, x1, y1)


def is_skippable(span):
    t = span["text"].strip()
    if not t:
        return True
    if span.get("flags", 0) & 1:  # chỉ số trên / footnote
        return True
    font = span["font"]
    if MATH_FONT.search(font) or MONO_FONT.search(font):
        return True
    if URL_RE.match(t):
        return True
    if NUMBERISH.match(t):
        return True
    # chuỗi ví dụ kiểu "HELLO"->"RIJVS": không dịch nội dung bên trong
    if not CJK.search(t) and not re.search(r"[a-z]", t) and re.search(r"[\u2192=:<>/]|\d", t) and len(t) > 4:
        return True
    # quá ngắn và không có chữ cái/Hán tự (khi đó là bullet, số, ký hiệu)
    if len(t) <= 2 and not re.search(r"[^\W\d_]", t):
        return True
    return False


def build_units(page):
    """Trả về list unit: {rect, text, size, bold, color, spans}"""
    d = page.get_text("dict")
    units = []
    for block in d["blocks"]:
        if block.get("type") != 0:
            continue
        lines = []
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            lines.append((line, spans))
        if not lines:
            continue
        # gộp các dòng liền nhau thành đoạn
        para = []
        prev = None
        def flush():
            nonlocal para
            if para:
                units.append(para)
                para = []
        for line, spans in lines:
            r = pymupdf.Rect(line["bbox"])
            if prev is not None:
                gap = r.y0 - prev.y1
                h = max(prev.height, r.height)
                overlap = min(r.x1, prev.x1) - max(r.x0, prev.x0) > 0
                if gap > 0.9 * h or not overlap:
                    flush()
            para.append((line, spans))
            prev = r
        flush()

    out = []
    for para in units:
        all_spans = [s for _, spans in para for s in spans]
        if all(is_skippable(sp) for sp in all_spans):
            continue
        special = any(MATH_FONT.search(s["font"]) or MONO_FONT.search(s["font"]) for s in all_spans)
        line_text = "".join(s["text"] for s in all_spans)
        if special:
            # dòng mã/đường dẫn không có chữ Hán: giữ nguyên
            if not CJK.search(line_text):
                continue
            all_spans = [s for s in all_spans if not is_skippable(s)]
            if not all_spans:
                continue
        # nối span: chèn dấu cách ở biên span/dòng nếu hai bên đều là chữ Latin
        parts = []
        prev_latin = False
        for s in all_spans:
            cur = s["text"]
            if prev_latin and cur[:1].isascii() and cur[:1].isalnum():
                parts.append(" ")
            parts.append(cur)
            prev_latin = bool(cur) and cur[-1:].isascii() and cur[-1:].isalnum()
        text = "".join(parts)
        text = re.sub(r"[•·ꞏ▪●○]\s*", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        size = max(s["size"] for s in all_spans)
        bold = sum(1 for s in all_spans if s["flags"] & 2 ** 4) * 2 >= len(all_spans)
        color = max(set(s["color"] for s in all_spans),
                    key=lambda c: sum(1 for s in all_spans if s["color"] == c))
        out.append({
            "rect": bbox_union([s["bbox"] for s in all_spans]),
            "text": text,
            "size": size,
            "bold": bold,
            "color": color,
            "spans": len(all_spans),
        })
    obstacles = [pymupdf.Rect(b["bbox"]) for b in d["blocks"] if b.get("type") == 1]
    return merge_units(out), obstacles


END_PUNCT = "，。、；：！？,.;:!?\u201d\u300d\u300f\uff09)】"


def join_text(a, b):
    if not a:
        return b
    if not b:
        return a
    if a[-1] in END_PUNCT or b[0] in "，。、；：！？,.;:!?\uff09)】":
        return a + b
    if CJK.search(a[-1]) and CJK.search(b[0]):
        return a + b
    return a + " " + b


def merge_units(units):
    """Gộp các đơn vị cùng đoạn bị tách sang hộp chữ khác để dịch trọn câu."""
    units = sorted(units, key=lambda u: (round(u["rect"].y0, 1), u["rect"].x0))
    merged = []
    for u in units:
        if merged:
            m = merged[-1]
            gap = u["rect"].y0 - m["rect"].y1
            line_h = min(m["size"], u["size"])
            overlap = min(m["rect"].x1, u["rect"].x1) - max(m["rect"].x0, u["rect"].x0)
            same_style = abs(m["size"] - u["size"]) < 1.6 and m["bold"] == u["bold"]
            grows_ok = (m["rect"].height + u["rect"].height) <= 8 * line_h
            if (-1 <= gap <= 0.7 * line_h and overlap > 0.35 * min(m["rect"].width, u["rect"].width)
                    and same_style and grows_ok):
                m["text"] = join_text(m["text"], u["text"])
                m["rect"] = bbox_union([m["rect"], u["rect"]])
                m["spans"] += u["spans"]
                continue
        merged.append(u)
    return merged


def dominant_color(pix):
    counts = {}
    for x in range(5, pix.width, 41):
        for y in range(5, pix.height, 41):
            c = pix.pixel(x, y)
            counts[c] = counts.get(c, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else (255, 255, 255)


def color_dist(a, b):
    return max(abs(int(a[i]) - int(b[i])) for i in range(3))


def sample_bg(pix, rect):
    """Màu nền: đa số điểm ngay ngoài viền khung chữ."""
    midx = (rect.x0 + rect.x1) / 2
    midy = (rect.y0 + rect.y1) / 2
    pts = []
    for dx in (-3, -2, 2, 3):
        for y in (rect.y0 + 1, midy, rect.y1 - 1):
            pts.append((rect.x0 + dx, y))
            pts.append((rect.x1 + dx, y))
    for dy in (-3, -2, 2, 3):
        for x in (rect.x0 + 1, midx, rect.x1 - 1):
            pts.append((x, rect.y0 + dy))
            pts.append((x, rect.y1 + dy))
    counts = {}
    for x, y in pts:
        ix = max(0, min(pix.width - 1, int(x)))
        iy = max(0, min(pix.height - 1, int(y)))
        c = pix.pixel(ix, iy)
        counts[c] = counts.get(c, 0) + 1
    if not counts:
        return (255, 255, 255)
    return max(counts.items(), key=lambda kv: kv[1])[0]


def contrast_color(bg, fg_int):
    r, g, b = (fg_int >> 16) & 255, (fg_int >> 8) & 255, fg_int & 255
    lum_fg = 0.299 * r + 0.587 * g + 0.114 * b
    lum_bg = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    if abs(lum_fg - lum_bg) > 45:
        return (r / 255, g / 255, b / 255)
    return (0, 0, 0) if lum_bg > 128 else (1, 1, 1)


def process(path, out_path, pages=None, render_page=None, dry=False, margin=6):
    doc = pymupdf.open(path)
    # thiên hướng mặc định khi câu gốc không có từ khoá phân biệt
    base = os.path.basename(path).lower()
    bias = "reasoning" if any(k in base for k in ("math", "prompt", "gui")) else "inference"
    idxs = range(len(doc)) if pages is None else pages
    stats = {"pages": 0, "units": 0, "translated": 0, "overflow": 0}
    for pno in idxs:
        page = doc[pno]
        stats["pages"] += 1
        units, obstacles = build_units(page)
        stats["units"] += len(units)
        targets = []
        texts = [u["text"] for u in units]
        if texts:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
                results = list(ex.map(safe_translate, texts))
        else:
            results = []
        for u, t in zip(units, results):
            if t is None:
                stats["failed"] = stats.get("failed", 0) + 1
                continue
            if not t or t.strip() == u["text"].strip():
                continue
            if is_citation(u["text"]):
                continue
            u["vi"] = split_inference(u["text"], polish(t.strip()), bias)
            targets.append(u)
        stats["translated"] += len(targets)
        if dry:
            print(f"--- page {pno+1}: {len(targets)} units")
            for u in targets:
                print("   ", [round(v) for v in u["rect"]], repr(u["text"][:40]), "->", repr(u["vi"][:60]))
            continue
        if not targets:
            continue

        pix = page.get_pixmap(dpi=72, colorspace=pymupdf.csRGB, alpha=False)
        page_bg = dominant_color(pix)

        for u in targets:
            u["bg"] = sample_bg(pix, u["rect"])

        # giới hạn khung theo các khối chữ lân cận (tránh tràn vào ảnh/bullet khác)
        rects = [u["rect"] for u in units] + obstacles
        for u in targets:
            r = u["rect"]
            right = page.rect.x1 - margin
            bottom = page.rect.y1 - margin
            for o in rects:
                if o is r:
                    continue
                if o.y1 > r.y0 + 1 and o.y0 < r.y1 - 1 and o.x0 > r.x1 - 1:
                    right = min(right, o.x0 - 3)
                if o.x1 > r.x0 + 1 and o.x0 < r.x1 - 1 and o.y0 > r.y1 - 1:
                    bottom = min(bottom, o.y0 - 2)
            # chữ nằm trong một ảnh/khối màu: không cho tràn ra ngoài khối đó
            holder = None
            for ob in obstacles:
                if ob.contains(r) and (holder is None or ob.get_area() < holder.get_area()):
                    holder = ob
            if holder is not None:
                right = min(right, holder.x1 - 2)
                bottom = min(bottom, holder.y1 - 2)
            if u["bg"] != page_bg and color_dist(u["bg"], page_bg) > 25:
                right = min(right, r.x1 + 2)
                bottom = min(bottom, r.y1 + 2)
            u["right"] = max(r.x1, right)
            u["bottom"] = max(r.y1, bottom)

        # 1) che chữ gốc
        for u in targets:
            r = pymupdf.Rect(u["rect"])
            r.x0 -= 0.8; r.y0 -= 0.8; r.x1 += 0.8; r.y1 += 0.8
            bg = tuple(v / 255 for v in u["bg"])
            page.add_redact_annot(r, fill=bg)
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )

        # 2) chèn tiếng Việt
        page.insert_font(fontname="viR", fontfile=FONT_REG)
        page.insert_font(fontname="viB", fontfile=FONT_BOLD)
        for u in targets:
            rect = pymupdf.Rect(u["rect"])
            font = get_font(u["bold"])
            # giới hạn phải: chừa lề trang, cho phép nới rộng nếu trống
            right = u["right"]
            bottom = u["bottom"]
            width = max(8, (right - rect.x0) * 0.98)
            h_limit = max(6, bottom - rect.y0)
            size = u["size"]
            min_size = 5.0
            while True:
                lines = wrap(u["vi"], font, size, width)
                total = len(lines) * size * 1.2
                if total <= h_limit or size <= min_size:
                    break
                size -= 0.4
            if total > h_limit + 0.5:
                stats["overflow"] += 1
            y0 = (rect.y0 + rect.y1) / 2 - total / 2
            y0 = max(rect.y0 - 2, min(y0, bottom - total))
            col = contrast_color(u["bg"], u["color"])
            fname = "viB" if u["bold"] else "viR"
            asc = font.ascender * size
            leading = size * 1.2
            for i, ln in enumerate(lines):
                page.insert_text(
                    (rect.x0, y0 + asc + i * leading), ln,
                    fontsize=size, fontname=fname, color=col,
                )
        if render_page is not None and pno + 1 == render_page:
            page.get_pixmap(dpi=110).save(os.path.splitext(out_path)[0] + f".p{pno+1}.png")
    if not dry:
        doc.save(out_path, garbage=3, deflate=True)
    return stats


def parse_pages(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a) - 1, int(b)))
        else:
            out.append(int(part) - 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out")
    ap.add_argument("--pages")
    ap.add_argument("--render", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    load_cache()
    out = a.out or re.sub(r"\.pdf$", ".vi.pdf", a.pdf, flags=re.I)
    t0 = time.time()
    st = process(a.pdf, out, parse_pages(a.pages) if a.pages else None,
                 render_page=a.render, dry=a.dry_run)
    save_cache()
    print(f"{a.pdf} -> {out} | {st} | {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
