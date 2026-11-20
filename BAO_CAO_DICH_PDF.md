# Báo cáo dịch PDF Trung → Việt

Ngày: 2026-11-13 · Nguồn: `documents/chapter1..11/*.pdf` · Kết quả: `*.vi.pdf` (bản gốc giữ nguyên)

## 1. Danh sách file đã dịch

| # | File gốc | File dịch | Trang | Đoạn dịch |
|---|---|---|---|---|
| 1 | `dive-into-llm.pdf` | `dive-into-llm.vi.pdf` | 77 | 581 |
| 2 | `dive-into-prompting.pdf` | `dive-into-prompting.vi.pdf` | 76 | 505 |
| 3 | `dive_edit_0410.pdf` | `dive_edit_0410.vi.pdf` | 21 | 73 |
| 4 | `math.pdf` | `math.vi.pdf` | 17 | 100 |
| 5 | `watermark.pdf` | `watermark.vi.pdf` | 48 | 375 |
| 6 | `dive-Jailbreak.pdf` | `dive-Jailbreak.vi.pdf` | 44 | 448 |
| 7 | `stega.pdf` | `stega.vi.pdf` | 13 | 36 |
| 8 | `mllms.pdf` | `mllms.vi.pdf` | 81 | 556 |
| 9 | `GUIagent.pdf` | `GUIagent.vi.pdf` | 43 | 241 |
| 10 | `dive-into-safety.pdf` | `dive-into-safety.vi.pdf` | 51 | 515 |
| 11 | `RLHF.pdf` | `RLHF.vi.pdf` | 24 | 107 |
| | **Tổng** | | **495** | **3.537** |

Kiểm tra đầu vào (bước 1): cả 11 tệp đều là **PDF text** (trích xuất được text layer), không phải bản scan → không cần OCR.

## 2. Thuật ngữ chuyên ngành giữ nguyên tiếng Anh

Áp dụng trên toàn bộ 495 trang (số lần xuất hiện trong bản dịch):

`LLM` 671 · `token` 89 · `agent` 89 · `watermark` 88 · `fine-tuning` 81 · `alignment` 55 · `pre-training` 51 · `reinforcement learning` 44 · `Chain-of-Thought (CoT)` 41 · `steganography` 36 · `encoder` 36 · `decoder` 31 · `jailbreak` 11 · `prompt learning` 6 · `distillation` 5 · `in-context learning` 1

Ngoài ra giữ nguyên: `multimodal`, `RLHF`, `SFT`, `RAG`, `PPO`, `DPO`, `GPT`/`ChatGPT`, `Llama`, `Qwen`, `Kafka`… cùng tên sản phẩm, tên bài báo (`CogAgent-chat`, `SeeClick`, `arXiv:xxxx.xxxxx`), URL, email và mã code — các đoạn này không bị đưa qua máy dịch.

Cùng bảng thuật ngữ này đã được áp cho 12 tệp Markdown tiếng Việt (`README.md` ở thư mục gốc và 11 chương) để thống nhất với bản PDF: 174 dòng được sửa, không đụng tới khối code, inline code, URL hay số dòng bảng. Script: `tools/pdf_vi/apply_terms_md.py` (chạy không tham số để xem trước, `--apply` để ghi).

Tiêu đề các chương được dịch lại thủ công để đúng thuật ngữ:

| Chương | Gốc | Tiêu đề tiếng Việt |
|---|---|---|
| 1 | 大模型技术与发展 | Công nghệ và phát triển LLM |
| 2 | 提示学习与思维链 | Prompt learning và Chain-of-Thought |
| 4 | LLM 数学推理 | Suy luận toán học với LLM |
| 6 | 大模型内容安全与越狱攻击 | An toàn nội dung và tấn công jailbreak với LLM |
| 7 | 动手学大模型隐写 | Thực hành steganography với LLM |
| 9 | 图形用户界面自主智能体 | Agent tự chủ trên giao diện đồ hoạ (GUI agent) |
| 10 | 大模型智能体安全 | An toàn agent LLM |
| 11 | 动手学大模型对齐 | Thực hành alignment với LLM |

## 3. Kết quả kiểm tra hậu dịch (bước 3)

| Hạng mục | Kết quả |
|---|---|
| Số trang khớp bản gốc | 495/495 (100%) |
| Ký tự Hán còn trong text layer | 0 (gốc: 39.544) |
| Ảnh/hình vector bị xoá | 0 — chỉ che vùng chữ, `PDF_REDACT_IMAGE_NONE` + `PDF_REDACT_LINE_ART_NONE` |
| Trang nghi mất nội dung (so sánh độ phủ mực từng trang) | 0/495 |
| Dấu cách bị mất ở biên span/dòng | đã sửa và kiểm tra lại (còn lại chỉ là tên riêng như `CogAgent-chat`) |
| Thuật ngữ tiếng Việt hóa sai quy tắc | 0 |
| 推理 phân biệt theo ngữ cảnh | `inference` 29 chỗ (quá trình sinh token) · `reasoning` 106 chỗ (suy luận logic) · `Chain-of-Thought (CoT)` 67 chỗ — không còn chỗ nào để "suy luận" trần |

Kiểm tra trực quan (trích xuất ảnh trang và xem): ch1 tr.64 (3 khối sơ đồ), ch2 tr.1 (tiêu đề), ch5 tr.1, ch6 tr.1, ch7 tr.1, và trước đó là ch1 tr.5/40, ch2 tr.20, ch6 tr.15, ch8 tr.30, ch10 tr.8, ch11 tr.10 — bố cục, khối màu, logo, sơ đồ, ảnh chụp giữ nguyên; chữ Việt nằm đúng vị trí khung cũ.

## 4. Điểm cần lưu ý

1. **Chữ Hán nằm trong ảnh chụp chưa dịch.** Một số bảng/hình được nhúng dưới dạng ảnh raster (không có text layer): ch6 tr.15, ch10 tr.8, ch11 tr.10… Muốn dịch phải OCR rồi vẽ đè lên ảnh, sẽ làm biến dạng hình — trái yêu cầu "giữ nguyên hình ảnh", nên giữ nguyên.
2. **Trang quá dày chữ**: chương 5 (22 đoạn) và chương 10 (20 đoạn) được tự động thu nhỏ cỡ chữ (tối thiểu 5pt) để vừa khung; không đoạn nào bị bỏ.
3. **Text layer dùng NBSP và soft hyphen**: hiển thị và in bình thường, nhưng khi copy/paste có thể ra `fine-tuning` thành `finetuning`. Đây là đặc điểm font nhúng, không phải lỗi hiển thị.
4. **Chất lượng ngôn ngữ**: bản dịch do máy (Google Translate) + hậu xử lý thuật ngữ, đọc hiểu được nhưng câu chữ chưa trau chuốt bằng bản Markdown đã dịch tay (`README.md` từng chương).
5. Chương 3, 5, 8 vốn là slide tiếng Anh: phần lớn nội dung được giữ nguyên tiếng Anh, chỉ các đoạn tiếng Trung được dịch.

## 5. Thuật ngữ cần người dùng xác nhận

| Thuật ngữ | Đang dùng | Vấn đề |
|---|---|---|
| 推理 (tuỳ ngữ cảnh) | `inference` / `reasoning` | **Đã tách.** Quy tắc: từ khoá trong câu gốc quyết định — `推理过程/推理时/推理速度/推理开销/模型推理/推理优化…` → `inference`; `数学推理/逻辑推理/推理能力/推理链/思维链/常识推理…` → `reasoning`; không có từ khoá thì theo thiên hướng chương (ch2, ch4, ch9 → `reasoning`; còn lại → `inference`). Nguồn tiếng Anh bám theo `reasoning`/`inference` gốc. Nếu vẫn muốn khác thì sửa danh sách `INFER_CUES`/`REASON_CUES` trong `tools/pdf_vi/translate.py`. |
| 智能体 | `agent` | Đã thống nhất `agent`; nếu muốn dùng "tác tử" thì đổi 1 dòng trong bảng ánh xạ. |
| 对齐 | `alignment` | Giữ tiếng Anh theo quy tắc; bản Markdown trước đây dùng "căn chỉnh". |
| 提示 | `prompt` (trong `prompt learning`) | Các chỗ đứng riêng vẫn dịch là "gợi ý" cho câu tự nhiên. |
| 水印 | `watermark` | Thống nhất giữ tiếng Anh (bản Markdown dùng "thủy vân"). |

## 6. Cách chạy lại

```bash
.venv-pdf/Scripts/python.exe tools/pdf_vi/translate.py documents/chapter7/stega.pdf
```

Bảng thuật ngữ ở `VI2EN` và bản dịch cố định cho tiêu đề ở `OVERRIDES` trong `tools/pdf_vi/translate.py`; với Markdown dùng `tools/pdf_vi/apply_terms_md.py --apply`. Bản dịch đã lưu cache ở `tools/pdf_vi/cache/translations.json` nên chạy lại chỉ mất vài giây mỗi tệp.
