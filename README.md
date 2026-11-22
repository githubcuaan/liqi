# Liqily

Data-mining project using the AoG Spring 2026 tournament dataset.

The raw dataset is downloaded separately from Drive; ask the project owner for
the link to the `liquipedia-final.zip` archive. Put it at
`dataset/liquipedia-final.zip` and extract it:

```sh
sha256sum dataset/liquipedia-final.zip
unzip -n dataset/liquipedia-final.zip -d dataset/
```

Expected archive SHA-256:
`ffdc93066709c99567f1845b68be885afea3973cd4000251a473943c3fd3473f`.
If the Drive download is an unpacked directory instead, copy it into
`dataset/035ce761e53a47db/`. Check the per-file hashes in
`dataset/035ce761e53a47db/release-manifest.json` and
`dataset/035ce761e53a47db/csv/manifest.json` before running experiments.
Do not mix snapshots from different versions. The expected dataset version is
`035ce761e53a47dbfd18ca1d9fabe7ceb0ec79115271bccac303bed2a6c0195c`.

See the [dataset notes](dataset/035ce761e53a47db/README.md) for scope and
limitations. Redistribution rights are not yet verified.

## Chạy web app Liqily

Ứng dụng gộp ba chức năng: khai phá luật kết hợp, gợi ý pick/ban và dự đoán
thắng/thua **sau khi đã chọn đủ hai đội hình**. Frontend được xây mới bằng
React/TypeScript; backend là FastAPI gọi trực tiếp các service Python.

Yêu cầu: Python 3.10+ (khuyến nghị 3.12), Node.js 20+ và npm. Trước tiên giải
nén dataset theo hướng dẫn ở trên; các CSV không được tải tự động từ mạng.
Gói pick/ban được đóng trong source, nhưng **artifact dự đoán không phân phối
qua git**; tạo cục bộ từ train như sau:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m liqily.prediction.serving
cd web
npm ci
npm run build
cd ..
.venv/bin/python -m uvicorn liqily.api.app:app --host 127.0.0.1 --port 8000
```

Mở <http://127.0.0.1:8000>. API docs: <http://127.0.0.1:8000/docs>.
Chạy frontend riêng lúc phát triển: `cd web && npm run dev`; Vite proxy các
request `/api` về cổng 8000. Nếu thay đổi phiên bản scikit-learn hoặc policy,
chạy lại lệnh tạo artifact; server từ chối artifact không khớp SHA-256,
dataset hoặc policy. Chỉ nạp file joblib được chính mình tạo, không nạp model
do người dùng tải lên.

Kiểm thử toàn bộ backend và build frontend:

```sh
.venv/bin/python -m pytest -q
cd web && npm ci && npm run build
```

Snapshot hiện tại: train 231 ván/60 series, validation 28 ván/7 series,
test 40 ván/8 series. Mining dùng 462 transaction đội từ train. Dự đoán
fit **chỉ train**, cấu hình được khóa ở `docs/report/model_selection.json`;
không dùng validation/test để fit, khai phá hoặc tạo thống kê cho web.

### Giới hạn khi diễn giải

- Mô hình dự đoán là **demo nghiên cứu**, không vượt baseline theo phe trên
  test (Brier 0.235367 so với 0.233249). Không dùng như bảo đảm chiến thắng.
- Điểm pick là cosine đồng đội; điểm ban là tần suất cấm trong train, **không
  phải xác suất thắng**. Gói này chưa đánh giá trên test độc lập V2 hoặc
  theo thứ tự draft live; không kiểm tra luật lượt/patch/role/global ban.
- Support/confidence/lift chỉ mô tả tương quan quan sát được, không chứng
  minh một combo gây ra chiến thắng.
- Manifest ghi `redistribution_license_verified=false`; chỉ vận hành nội bộ
  hoặc cục bộ trước khi xác minh quyền phát hành dữ liệu và artifact.

### Nguồn mã tích hợp

Xem danh sách file và commit nguồn cố định tại
[`docs/plan/tich_hop_web_app.md`](docs/plan/tich_hop_web_app.md).
Logic mining chuyển từ [Khaiphaagain](https://github.com/buivandai05/Khaiphaagain)
commit `0b106a25bf7491340fae14e3d559633b8255718e`, chỉnh import/cấu hình
để dùng chung snapshot. Gói `liqi_draft` giữ nguyên byte từ
[Data-Mining-by-ndt](https://github.com/ngduktrong/Data-Mining-by-ndt) commit
`7bfafe23daf15ffa69f58cdd53abc53750cac4ef` và tự kiểm tra manifest lúc
khởi động. Không nhập template/CSS/JS của hai repo này.
