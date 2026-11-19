# Cấu trúc thư mục dự kiến cho Liqily

Source Python chứa logic dùng chung; notebook phục vụ thực nghiệm, trực quan hóa và báo cáo.

```text
proj/
├── dataset/
│   └── 035ce761e53a47db/       # Dataset gốc, giữ nguyên
├── docs/
│   ├── gioi_thieu_bai_toan.md
│   ├── eda_plan.md
│   ├── du_doan_thang_thua_plan.md
│   └── folder_structure.md
├── notebook/
│   ├── ...                       # Giữ nguyên các notebook hiện có
│   ├── eda.ipynb                  # Dự kiến: EDA
│   └── win_prediction.ipynb       # Dự kiến: thí nghiệm và biểu đồ
├── src/
│   └── liqily/
│       └── prediction/
│           ├── data.py           # Đọc CSV, kiểm tra dữ liệu
│           ├── features.py       # Mã hóa đội hình, phe, patch
│           ├── train.py          # Huấn luyện và lưu mô hình
│           ├── evaluate.py       # Tính chỉ số, so sánh baseline
│           └── predict.py        # Hàm dự đoán dùng cho ứng dụng
├── tests/
│   └── prediction/
│       ├── test_data.py
│       ├── test_features.py
│       └── test_predict.py
├── artifacts/                    # Mô hình đã huấn luyện; tạo khi chạy
├── reports/                      # Bảng và biểu đồ kết quả; tạo khi chạy
├── pyproject.toml                 # Dependencies và cấu hình dự án
└── README.md                     # Hướng dẫn cài đặt, chạy thí nghiệm
```

Các tên notebook mới chỉ mang tính gợi ý. Không đổi tên, đánh số lại hoặc xóa notebook hiện có chỉ để khớp sơ đồ.

## Nguyên tắc tổ chức

- Logic nạp dữ liệu, tiền xử lý, huấn luyện, đánh giá và suy luận nằm trong `src/liqily/prediction/`; notebook gọi lại các hàm này, không duy trì một pipeline ML riêng.
- `tests/prediction/` kiểm tra dữ liệu đầu vào, tính bất biến theo thứ tự tướng và kết quả dự đoán.
- `dataset/035ce761e53a47db/` là snapshot gốc; không ghi đè khi chạy thực nghiệm.
- `artifacts/` và `reports/` là đầu ra được tạo lại khi chạy; quyết định có lưu vào hệ thống quản lý phiên bản hay không sau khi xác định kích thước và nhu cầu nộp bài.
- Chưa cần tạo `app/` ở giai đoạn đầu. Khi đã chốt mô hình, thêm giao diện/API vào `app/` và gọi `liqily.prediction.predict`, không viết lại logic ML.
