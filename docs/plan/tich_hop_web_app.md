# Kế hoạch tích hợp ba phần thành Liqily Web App

## 1. Mục tiêu và phạm vi

Lấy **logic Python và artifact mô hình** từ hai repo của Đại và Trọng, kết hợp với phần dự đoán thắng/thua trong repo hiện tại để tạo một web app thống nhất.
**Không nhập giao diện** (template, CSS, JavaScript) từ hai repo ngoài; xây frontend mới, hiện đại và responsive.

- Repo chính: dự án Liqily hiện tại.
- Nguồn khai phá luật: <https://github.com/buivandai05/Khaiphaagain>.
- Nguồn gợi ý pick/ban: <https://github.com/ngduktrong/Data-Mining-by-ndt>.
- Phần dự đoán hiện tại: `src/liqily/prediction/`.
- Chưa triển khai trong kế hoạch này: tài khoản, dữ liệu thời gian thực, luật cấm/chọn theo lượt thi đấu thực tế.

## 2. Danh mục nguồn cần tích hợp

| Nguồn    | Lấy                                                                                                                                                                                                       | Không lấy / lưu ý                                                                                                                                      |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Đại      | `src/data/{preprocessing,data_validator}.py`, `src/mining/{apriori_miner,fpgrowth_miner,comparison}.py`, `services/{mining_service,hero_mapping_service}.py`; tham khảo `tests/test_team_compositions.py` | Không lấy `templates/`, `static/` và các route dựng trang. Chuyển import và đường dẫn phụ thuộc `Config.py` sang package/cấu hình chung.               |
| Trọng    | **Một bản** `Liqi_Handoff/liqi_draft/`, gồm `service.py`, `opponent_pick.py`, `ban_baseline.py`, `models/*.json`, `release_manifest.json`; dùng `test_handoff.py` và các JSON ví dụ để đối chiếu          | Không lấy `Liqi_Web_Demo/static/`. Không trộn gói handoff với các bản sao khác hoặc V1. Giữ nguyên byte file vì package kiểm tra SHA-256 lúc khởi tạo. |
| Hiện tại | Giữ `src/liqily/prediction/` và policy `docs/report/model_selection.json`                                                                                                                                 | Bổ sung artifact phục vụ web và hàm suy luận độc lập; hiện mới có mã huấn luyện/đánh giá.                                                              |

Chốt commit cụ thể của hai repo nguồn trước khi nhập mã. Dùng snapshot dữ liệu `035ce761e53a47dbfd18ca1d9fabe7ceb0ec79115271bccac303bed2a6c0195c`;
đối chiếu hash các file tương ứng trước khi dùng chung, không trộn snapshot.
`hero_id` là khóa chung; tên tướng chỉ phục vụ hiển thị.
Khai phá luật dùng `association_train.csv` (231 ván, 462 transaction đội), không lấy validation/test để làm dữ liệu huấn luyện khai phá.

## 3. Kiến trúc đích

```text
React + TypeScript
  dashboard | khai phá luật | gợi ý pick/ban | dự đoán | dữ liệu
                    │ HTTP/JSON
FastAPI (Python)
  ├─ mining service      → Apriori, FP-Growth, luật, combo
  ├─ draft service       → DraftRecommender + model JSON
  ├─ prediction service  → encoder + model đã fit
  └─ catalog/data service→ hero_id, tên tướng, patch, metadata
                    │
       snapshot dữ liệu cố định + artifact có phiên bản
```

FastAPI chỉ cung cấp API và kiểm tra request, không viết lại thuật toán. Giai đoạn đầu chạy trên một máy, không cần database. Cấu trúc dự kiến:

```text
src/liqily/
  mining/          # logic chuyển từ repo Đại
  draft/           # adapter cho gói handoff nguyên vẹn của Trọng
  prediction/      # logic hiện có + export_model.py + predict.py
  catalog/         # ID/tên tướng và metadata dùng chung
  api/             # FastAPI, schemas, endpoints, lỗi
web/               # frontend mới
artifacts/         # artifact dự đoán đã khóa phiên bản
tests/             # unit, contract, integration
```

## 4. Các giai đoạn triển khai

### Giai đoạn 1 — Khóa nguồn và hợp đồng dữ liệu

1. Ghi commit nguồn, phiên bản dataset và danh sách file được phép nhập; không ghi đè công việc hiện có.
2. Xác minh hash snapshot, model handoff và `release_manifest.json`; thống nhất `hero_id`, tên hiển thị và patch.
3. Chốt schema: mining nhận ngưỡng; draft nhận tướng đã chọn/cấm và `k`; prediction nhận đúng 5 tướng mỗi đội, phe đội A và patch.
4. Giữ dữ liệu gốc bất biến, không nhân bản CSV trùng lặp.

**Hoàn thành:** nguồn/phiên bản tái lập được; test xác nhận file và ID tương thích.

### Giai đoạn 2 — Tích hợp logic Python

- **Mining:**
  - chuyển class sang `liqily.mining`, thay đường dẫn cố định bằng cấu hình;
  - giữ kiểm tra hai đội/một đội thắng mỗi trận, cách tính support–confidence–lift và so sánh hai thuật toán.
  - Đặt giới hạn ngưỡng, kích thước kết quả và thời gian chạy; cache theo snapshot và tham số.
- **Pick/ban:**
  - đặt nguyên vẹn gói `liqi_draft` ở vị trí import được, khởi tạo `DraftRecommender` một lần khi backend chạy.
  - Adapter chuẩn hóa input/output và lỗi; không sửa model hay công thức.
  - Danh mục phải phân biệt tướng có tên với ứng viên hợp lệ qua `pick_candidate` và `ban_candidate`.
- **Dự đoán:**
  - fit `forest_depth_3` chỉ trên train, xuất encoder/model/metadata gắn policy và version/hash.
  - Backend tải artifact khi khởi động, không train mỗi request.
  - Tạo input suy luận riêng thay vì dùng `Game` hiện yêu cầu nhãn `team_a_win`.

**Hoàn thành:** ba service gọi độc lập bằng Python; test gốc và test tích hợp đạt, chưa cần giao diện.

### Giai đoạn 3 — API thống nhất

| Endpoint dự kiến                         | Chức năng                                 |
| ---------------------------------------- | ----------------------------------------- |
| `GET /api/v1/catalog/heroes`, `/patches` | Danh mục ID/tên, khả năng sử dụng         |
| `GET /api/v1/overview`                   | Tổng quan và phiên bản dữ liệu            |
| `POST /api/v1/mining/run`                | Chạy Apriori hoặc FP-Growth               |
| `POST /api/v1/mining/compare`            | So sánh hai thuật toán cùng tham số       |
| `GET /api/v1/compositions`               | Combo quan sát được, số trận/thắng/thua   |
| `POST /api/v1/draft/recommend`           | Gợi ý pick/ban, top-K và bằng chứng       |
| `POST /api/v1/predictions/win`           | Xác suất đội A thắng, phiên bản, cảnh báo |
| `GET /api/v1/reports/...`                | Xuất CSV tương ứng tham số đã chạy        |

Tất cả endpoint có schema, giới hạn request và mã lỗi thống nhất.
Chặn ID lạ/trùng, input thiếu hoặc sai kiểu.
Không gửi traceback hay đường dẫn máy chủ ra frontend.
Chỉ đưa vào draft những gì đã biết tại lượt xét, không dùng trước thông tin đội hình cuối trận.

### Giai đoạn 4 — Giao diện mới hoàn toàn

Thiết kế dashboard responsive, bộ chọn tướng có tìm kiếm, bảng/biểu đồ có trạng thái loading, empty, error và hỗ trợ bàn phím.

1. **Tổng quan:** số trận, phạm vi dữ liệu, lối vào ba chức năng.
2. **Khám phá đội hình:**
   - lọc combo 2–5 tướng, số lần xuất hiện và tỷ lệ thắng _quan sát_ với cỡ mẫu;
   - xem luật và support/confidence/lift, so sánh Apriori/FP-Growth, tải CSV.
3. **Trợ lý cấm/chọn:**
   - đội mình, đối thủ, tướng đã cấm; nút Pick/Ban; gợi ý kèm bằng chứng.
   - Điểm gợi ý **không phải xác suất thắng** hoặc kết quả “khắc chế tối ưu”.
4. **Dự đoán sau chọn tướng:**
   - chỉ chạy khi đủ 10 tướng hợp lệ, có phe và patch;
   - hiển thị xác suất, phiên bản model, cảnh báo danh mục chưa thấy trong train và giới hạn sử dụng.
5. **Dữ liệu & phương pháp:**
   - nguồn, cách chia train/validation/test, cách tính điểm và hạn chế riêng của từng chức năng.

Không mô phỏng luật draft thật khi chưa xác minh thứ tự lượt, vai trò, patch và global ban; gói handoff hiện không kiểm tra các luật này.

### Giai đoạn 5 — Kiểm thử, đóng gói, nghiệm thu

- **Unit/contract:** giữ test gốc từ các nguồn; kiểm tra hash handoff, input sai/trùng, không còn ứng viên; kết quả API khớp hàm Python và JSON tham chiếu.
- **Data/ML:** bảo đảm fit và mining chỉ dùng train; request lặp cho kết quả như nhau; artifact/version khớp policy; tướng/patch mới có cảnh báo.
- **Web/E2E:** kiểm tra luồng chọn tướng → gợi ý → đủ hai đội → dự đoán, lọc luật, xuất CSV, màn hình mobile và thao tác bàn phím.
- **Triển khai:** khóa dependency Python/Node; hướng dẫn chạy; cấu hình môi trường; health check; build production; không dùng `debug=True` hay secret hard-code từ demo.

**Nghiệm thu:** ba chức năng hoạt động tại một URL; model và dữ liệu đúng phiên bản; kết quả API được đối chiếu với logic nguồn; test tự động đạt; tài liệu và giao diện nêu đúng giới hạn.

## 5. Giới hạn và rủi ro bắt buộc thể hiện

- **Dự đoán thắng/thua chưa vượt baseline trên test:** Brier của model `0.235367`, baseline theo phe `0.233249`; balanced accuracy model `0.4815`. Chỉ đưa lên web như **demo nghiên cứu**, kèm baseline/cảnh báo; không quảng bá là dự đoán đáng tin cậy.
- **Pick/ban không dự đoán thắng:** pick dựa trên cosine đồng đội, ban dựa trên tần suất ban trong train. V2 chưa có đánh giá test độc lập và chưa đo chất lượng trong draft live; điểm không phải xác suất thắng.
- **Quyền phân phối dữ liệu chưa được xác minh** trong manifest. Cần xác nhận trước khi công khai dataset/artifact; nếu chưa rõ chỉ demo nội bộ hoặc cục bộ.

**Thứ tự:** khóa dữ liệu → tích hợp Python/test → API → giao diện → E2E/triển khai. **Ước lượng sơ bộ:** 8–12 ngày làm việc cho demo hoàn chỉnh, chưa tính xử lý quyền dữ liệu hoặc luật draft thật.
