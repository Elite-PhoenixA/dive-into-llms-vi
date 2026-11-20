"""Áp bảng thuật ngữ Anh hoá (giống bản PDF) lên các README.md tiếng Việt.

Bỏ qua khối ```code``` và `inline code`; giữ viết hoa đầu câu/ô bảng.
Dùng: python apply_terms_md.py [--apply]
"""
import glob
import re
import sys

# (mẫu, thay thế) — mẫu dài/đặc thù phải đứng trước mẫu ngắn
RULES = [
    (r"học gợi ý\s*\(\s*[Pp]rompting\s*\)", "prompt learning"),
    (r"chuỗi tư duy\s*\(\s*CoT\s*\)", "Chain-of-Thought (CoT)"),
    (r"được tinh chỉnh", "được fine-tune"),
    (r"tinh chỉnh(?=\s+(?:nó|thêm|lại|trên|để))", "fine-tune"),
    (r"được căn chỉnh", "được align"),
    (r"chuỗi tư duy", "Chain-of-Thought (CoT)"),
    (r"mô hình ngôn ngữ tiền huấn luyện", "pre-trained language model"),
    (r"mô hình tiền huấn luyện", "pre-trained model"),
    (r"mô hình ngôn ngữ lớn", "LLM"),
    (r"mô hình lớn", "LLM"),
    (r"sau huấn luyện", "post-training"),
    (r"tiền huấn luyện", "pre-training"),
    (r"thủy vân", "watermark"),
    (r"học gợi ý", "prompt learning"),
    (r"kỹ thuật gợi ý", "prompting"),
    (r"chỉnh sửa tri thức", "knowledge editing"),
    (r"thuật giấu tin", "steganography"),
    (r"bộ mã hóa", "encoder"),
    (r"bộ giải mã", "decoder"),
    (r"tinh chỉnh", "fine-tuning"),
    (r"đa phương thức", "multimodal"),
    (r"căn chỉnh", "alignment"),
    (r"chưng cất", "distillation"),
    (r"bộ dữ liệu", "dataset"),
    (r"tác tử", "agent"),
]

# ký tự kết thúc câu trước đó → viết hoa chữ đầu của cụm thay thế
SENT_END = set(" \n\t|#>-*>(:;")


def fix_case(text, start, rep):
    i = start - 1
    while i >= 0 and text[i] in " \t":
        i -= 1
    if i < 0 or text[i] in "\n|#>-*>(:;.!":
        return rep[:1].upper() + rep[1:]
    return rep


def convert_segment(seg):
    for pat, rep in RULES:
        out = []
        pos = 0
        for m in re.finditer(r"(?i)(?<![\w-])" + pat + r"(?![\w-])", seg):
            out.append(seg[pos:m.start()])
            out.append(fix_case(seg, m.start(), rep) if "$" not in rep else m.expand(rep))
            pos = m.end()
        out.append(seg[pos:])
        seg = "".join(out)
    return seg


def convert(text):
    """Tách theo khối ``` và `inline code`, chỉ sửa phần văn xuôi."""
    parts = re.split(r"(```.*?```)", text, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue
        chunks = re.split(r"(`[^`\n]*`)", part)
        for j, ch in enumerate(chunks):
            if ch.startswith("`") and ch.endswith("`") and len(ch) > 1:
                continue
            chunks[j] = convert_segment(ch)
        parts[i] = "".join(chunks)
    return "".join(parts)


def main():
    apply = "--apply" in sys.argv
    files = ["README.md"] + sorted(glob.glob("documents/chapter*/README.md"))
    total = 0
    for f in files:
        old = open(f, encoding="utf-8").read()
        new = convert(old)
        if new == old:
            continue
        changed = sum(1 for a, b in zip(old.splitlines(), new.splitlines()) if a != b)
        total += changed
        print(f"{f}: {changed} dòng thay đổi")
        if not apply:
            for a, b in zip(old.splitlines(), new.splitlines()):
                if a != b:
                    print("  -", a.strip()[:110])
                    print("  +", b.strip()[:110])
                    break
        else:
            open(f, "w", encoding="utf-8", newline="\n").write(new)
    print(("ĐÃ ÁP DỤNG" if apply else "CHẠY THỬ") + f" — tổng {total} dòng")


if __name__ == "__main__":
    main()
