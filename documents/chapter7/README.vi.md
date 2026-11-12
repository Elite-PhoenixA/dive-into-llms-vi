# Thuật giấu tin trong văn bản bằng LLM

Dự án này hiện thực thuật giấu tin trong văn bản dựa trên mô hình ngôn ngữ lớn (LLM), sử dụng mô hình GPT-2 để giấu thông tin trong văn bản được sinh ra. Dự án gồm hai phương pháp mã hóa: mã hóa Huffman (Huffman Coding) và mã hóa độ dài cố định (Fixed Length Coding, FLC).

## Đặc điểm chức năng

- Hiện thực thuật giấu tin trong quá trình sinh văn bản của GPT-2
- Hỗ trợ hai phương pháp mã hóa:
  - Mã hóa Huffman (Huffman Coding)
  - Mã hóa độ dài cố định (Fixed Length Coding, FLC)
- Đồng thời sinh văn bản giấu tin và văn bản thường để so sánh

## Yêu cầu môi trường

- Python 3.8+
- PyTorch
- Transformers
- CUDA (tùy chọn, dùng để tăng tốc bằng GPU)

## Các bước cài đặt

Cài đặt các gói phụ thuộc:

```bash
pip install torch # Nếu dùng GPU, lưu ý chỉ định torch là bản GPU
pip install transformers
pip install jupyter
```

## Cách sử dụng

1. Mở Jupyter notebook:
```bash
jupyter notebook llm_stega.ipynb
```

2. Notebook gồm ba phần chính:
   - Hiện thực mã hóa Huffman
   - Hiện thực mã hóa độ dài cố định (FLC)
   - Sinh văn bản và giấu tin

3. Sinh văn bản giấu tin:
   - Chọn phương pháp mã hóa (mã hóa Huffman hoặc FLC)
   - Thiết lập tham số (giá trị k của mã hóa)
   - Chạy hàm chính với prompt tùy chỉnh

Mã ví dụ:
```python
# Khởi tạo bộ xử lý giấu tin
k = 2
handle = Huffman(k=2**k, bits=bits)
# Hoặc sử dụng FLC
# handle = FLC(k=k, bits=bits)

# Sinh văn bản có giấu tin
prompt = "Hello，I'm"
stega_output, normal_output = generate_text_with_steganography(
    model, tokenizer, prompt, handle
)
```

## Tệp đầu ra

Chương trình sẽ sinh ra hai tệp văn bản:
- `outputs-gpt2-stega.txt`: văn bản có giấu tin
- `outputs-gpt2-normal.txt`: văn bản vốn được sinh bình thường khi không có ràng buộc giấu tin

## Lưu ý

- Mô hình GPT-2 sẽ tự động được tải xuống trong lần chạy đầu tiên, trong nước cũng có thể tải sẵn mô hình GPT-2 qua mirror https://hf-mirror.com, hoặc dùng mô hình lớn khác.
- Đảm bảo có đủ dung lượng ổ đĩa (mô hình khoảng 500MB)
- Khuyến nghị dùng GPU hỗ trợ CUDA để có hiệu năng tốt hơn
- Độ dài thông tin giấu sẽ ảnh hưởng đến độ dài văn bản được sinh ra

## Nguyên lý hoạt động

1. Quá trình giấu tin:
   - Chuyển thông tin mật thành chuỗi nhị phân
   - Dùng mô hình GPT-2 để sinh văn bản
   - Nhúng các bit thông tin vào văn bản được sinh ra thông qua phương pháp mã hóa

2. Quá trình giải mã:
   - Dùng cùng mô hình GPT-2 và ngữ cảnh
   - Trích xuất các bit thông tin ẩn từ văn bản thông qua phương pháp giải mã
   - Chuyển chuỗi nhị phân trở lại thông tin ban đầu
