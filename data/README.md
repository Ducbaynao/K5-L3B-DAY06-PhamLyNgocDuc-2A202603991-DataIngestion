# Hướng dẫn dữ liệu (Corpus Data)

## 1. Lưu trữ tài liệu local và quy tắc Git

Tài liệu PDF gốc và dữ liệu trích xuất dạng thô/bán xử lý **chỉ được lưu trữ trên môi trường local**, tuyệt đối **không được commit** lên kho mã nguồn Git nhằm tuân thủ quy tắc bản quyền và bảo mật:

- Đường dẫn file PDF local: `data/raw/ptbv_report.pdf`
- Đường dẫn trích xuất trang local: `data/extracted/pages.jsonl`
- Quy tắc loại trừ trong `.gitignore`:
  ```gitignore
  /data/raw/
  /data/extracted/
  ```

File duy nhất được theo dõi trong Git tại thư mục `data/` là:
- `data/manifest.json` (metadata, thống kê số trang, số ký tự, checksum).
- `data/README.md` (hướng dẫn này).
- `data/format-example.json` (mẫu tham khảo của starter).

## 2. Thông tin tài liệu và tình trạng bản quyền

- **Tên đề tài**: *CÁC NHÂN TỐ ẢNH HƯỞNG TỚI HOẠT ĐỘNG CÔNG BỐ BÁO CÁO PHÁT TRIỂN BỀN VỮNG TẠI CÁC DOANH NGHIỆP NIÊM YẾT TRÊN SÀN CHỨNG KHOÁN VIỆT NAM*.
- **Phân loại**: Báo cáo tổng kết đề tài tham gia giải thưởng Nghiên cứu khoa học sinh viên năm 2024, Trường Đại học Kinh tế Quốc dân.
- **Nguồn lấy tài liệu**: Tải từ nền tảng chia sẻ tài liệu học tập Studocu (tên file tải về: `[studocu.com] - Báo cáo NCKH - Các Nhân Tố tác động đến Công Bố Báo Cáo PTBV 2024.pdf`). Do tài liệu được chia sẻ bởi người dùng trên nền tảng của bên thứ ba và không có canonical URL chính thức, dự án không tự dựng URL giả định.
- **Tình trạng giấy phép / quyền sử dụng (`license_or_permission`)**: **Chưa xác minh (Unverified)**. Tài liệu chưa có bằng chứng giấy phép mở (như Creative Commons) hoặc văn bản chấp thuận phân phối lại công khai. Tôi không khẳng định mục đích học tập tự chứng minh quyền xử lý hoặc tái phân phối. PDF được giữ local; tình trạng quyền sử dụng vẫn chưa xác minh.

## 3. Cách cung cấp tài liệu để tái lập

Để tái lập thí nghiệm trên máy khác, người dùng cần tự chuẩn bị file tài liệu:
1. Đặt file PDF vào đúng vị trí: `data/raw/ptbv_report.pdf`.
2. Xác minh tính toàn vẹn của file thông qua mã băm SHA-256:
   - **SHA-256 mong đợi**: `3382820c1edb8c2598bc3c033742e864bf7848f5e9485f6dd3ca1e8391014742`
   - Lệnh kiểm tra trên Windows PowerShell:
     ```powershell
     Get-FileHash data/raw/ptbv_report.pdf -Algorithm SHA256
     ```
   - Lệnh kiểm tra trên Linux / macOS:
     ```bash
     sha256sum data/raw/ptbv_report.pdf
     ```

## 4. Cách chạy lại bước chuẩn bị corpus

Từ thư mục gốc của repository, kích hoạt môi trường ảo `starter/.venv` và thực thi:

```powershell
# Kích hoạt virtual environment
.\starter\.venv\Scripts\Activate.ps1

# Chạy trích xuất và chuẩn hóa văn bản
python -m starter.src.ingestion
```

Quá trình này sẽ:
1. Đọc 84 trang nội dung từ trang PDF 18 đến 101.
2. Chuẩn hóa Unicode NFC, loại bỏ watermark của Studocu và các dòng thông tin người tải.
3. Giữ các dòng/khối text trích xuất được; không bảo đảm phục hồi đầy đủ bố cục bảng, sơ đồ hoặc ranh giới đoạn ngữ nghĩa.
4. Ghi kết quả vào `data/extracted/pages.jsonl`.
5. Ghi text và số ký tự; chạy verifier riêng để xác nhận bản corpus hiện tại có 84 trang không rỗng, tổng 153.080 ký tự.
