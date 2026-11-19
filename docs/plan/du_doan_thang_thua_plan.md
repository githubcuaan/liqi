# Kế hoạch thực hiện chức năng dự đoán thắng/thua cho Liqily

## 1. Mục tiêu và phạm vi

Dự đoán xác suất **đội A thắng một ván** sau khi đã biết đầy đủ đội hình hai bên.
Đây là bài toán dự đoán _sau chọn tướng_, không phải dự đoán trong lúc cấm/chọn hoặc dự đoán đội thắng cả loạt trận.

- Đầu vào: 5 tướng đội A, 5 tướng đội B, phe của đội A (`blue`/`red`) và `patch_id`.
- Đầu ra: `P(team_a_win)`, đội được dự đoán thắng và phiên bản mô hình.
- Ngoài phạm vi giai đoạn này: luật kết hợp, gợi ý cấm/chọn, dự đoán từ đội hình chưa đủ 10 tướng.
- Xác suất là ước lượng từ dữ liệu giải đấu, không phải tỷ lệ thắng được bảo đảm cho người chơi phổ thông.

Hợp đồng dữ liệu được quy định tại `dataset/035ce761e53a47db/feature_schema.json`.

## 2. Dữ liệu và nguyên tắc đánh giá

Sử dụng đúng snapshot `dataset/035ce761e53a47db/`. Mỗi dòng trong các tập dự đoán là một ván:

| Tập        | Series | Ván | Đội A thắng |
| ---------- | -----: | --: | ----------: |
| Train      |     60 | 231 |         128 |
| Validation |      7 |  28 |          16 |
| Test       |      8 |  40 |          27 |

Các tập đã chia theo lịch series và giữ toàn bộ ván của một series trong cùng tập; không chia ngẫu nhiên lại.
Lịch series chỉ là đại diện cho thời gian thi đấu, chưa xác minh thời điểm diễn ra từng ván.

Quy tắc chống rò rỉ dữ liệu:

1. Chỉ dùng `team_a_heroes`, `team_b_heroes`, `team_a_side`, `patch_id` làm đặc trưng; nhãn là `team_a_win`.
2. `game_id`, `series_id`, thời gian và cột nguồn chỉ dùng để kiểm tra/đối chiếu.
   Không đưa thống kê tướng toàn giải, vàng, mạng hạ gục hay kết quả sau trận vào mô hình.
3. Chỉ fit bộ mã hóa, tiền xử lý và mô hình trên **train**. Dùng **validation** để chọn phương án; chỉ đánh giá **test một lần** sau khi chốt.
4. Xử lý được tướng/patch chưa từng xuất hiện trong train mà không fit lại trên holdout.
   Theo `split_manifest.json`, validation/test có tướng mới và patch `aov:vn:2026-04-23` chỉ xuất hiện ở test.

## 3. Các giai đoạn triển khai

### A. Nạp và kiểm tra dữ liệu

- Đọc `csv/train.csv`, `csv/validation.csv`, `csv/test.csv`; đối chiếu số dòng, nhãn và series với `split_manifest.json`.
- Parse hai cột đội hình bằng `json.loads`.
  Kiểm tra mỗi bên đúng 5 ID tướng khác nhau, không trùng tướng giữa hai đội; kiểm tra phe, patch và nhãn boolean `true`/`false` một cách tường minh.
- Kiểm tra `game_id` không trùng và `series_id` không nằm ở nhiều tập. Ghi báo cáo lỗi thay vì âm thầm bỏ dòng.
- Dùng `csv/heroes.csv` để đổi ID sang tên **chỉ cho giao diện/hiển thị**.

**Tiêu chí hoàn thành:** Có script kiểm tra tái lập được; số lượng hợp lệ khớp manifest hoặc mọi sai khác được giải thích.

### B. Biểu diễn đội hình và baseline

**Đầu vào:** `games_by_split` từ `audit_dataset()` ở phần A; chỉ tiếp tục khi `issues` rỗng. Mỗi `Game` đã có đội hình dưới dạng `frozenset`, phe, patch và nhãn boolean.

1. Tạo `src/liqily/prediction/features.py` với một encoder có phương thức `fit(train_games)` và `transform(games)`. `fit` thu thập ID tướng và patch **chỉ từ train**, sắp xếp để thứ tự cột cố định; lưu danh sách và tên cột cùng encoder. Không gọi `fit` trên validation/test hoặc trên cả ba tập gộp lại.
2. Biểu diễn hai đội hình tách biệt: một cột nhị phân cho mỗi tướng train ở đội A và một cột cho mỗi tướng train ở đội B. Đội hình là **tập không thứ tự**; không suy diễn vai trò hay thứ tự chọn từ vị trí trong JSON. Mã hóa phe bằng `team_a_is_blue` (blue = 1, red = 0) và patch bằng các cột nhị phân cho những patch có trong train.
3. Với tướng/patch không có trong danh mục train, giữ nguyên kích thước vector: các cột tương ứng với danh mục đã biết bằng 0; ghi nhận số tướng mới mỗi đội và cờ patch mới để cảnh báo khi dự đoán. Có thể thêm các giá trị này vào vector theo tên cột cố định, nhưng vì chúng luôn bằng 0 ở train, **không diễn giải trọng số của chúng là tác động đã được mô hình học**. Tướng có trong `heroes.csv` nhưng chưa có trong train là danh mục mới, không phải dữ liệu sai ở phần A.
4. Tạo riêng `X_train`, `X_validation`, `X_test` bằng **cùng một encoder** và `y_train`, `y_validation`, `y_test` từ `team_a_win`. Không đưa nhãn, `game_id`, `series_id`, `split` hoặc metadata vào ma trận `X`.
5. Xây hai baseline xác suất, chỉ tính tham số từ train: (a) tỷ lệ đội A thắng chung `128/231`; (b) tỷ lệ đội A thắng theo phe `blue`/`red`, kèm phương án dùng tỷ lệ chung nếu một phe không có mẫu train. Chỉ dùng nhãn validation để **đánh giá** baseline, không dùng để tính lại tỷ lệ. Việc so sánh chỉ số với mô hình được thực hiện ở phần C/D.
6. Thêm `tests/prediction/test_features.py`: kiểm tra thứ tự tướng không làm đổi vector; đổi nhãn không làm đổi `X`; tướng/patch mới không gây lỗi, không đổi danh sách cột và được ghi nhận; ba tập có cùng số cột; baseline chỉ phụ thuộc nhãn train. Dùng notebook để minh họa kích thước ma trận và vài tên cột, nhưng logic xử lý nằm trong `features.py`.

**Quy ước triển khai:** Comment, docstring, warning và CLI/log output trong code viết bằng **tiếng Anh**; phần giải thích báo cáo vẫn có thể viết bằng tiếng Việt.

**Tiêu chí hoàn thành:** Chạy được các test của phần A và B; `X` có lần lượt 231/28/40 dòng với cùng số cột; không fit lại trên holdout; baseline tính đúng từ train; vector không thay đổi khi hoán vị thứ tự tướng trong một đội.

### C. Huấn luyện và so sánh

Thử ít nhất hai phương pháp, phù hợp yêu cầu tại `docs/yeu_cau_do_an.md`:

1. **Logistic Regression có regularization:** mốc chính, dễ giải thích, phù hợp dữ liệu ít và nhiều cột nhị phân.
2. **Random Forest giới hạn độ sâu** hoặc mô hình cây tăng cường được khống chế độ phức tạp:
   kiểm tra liệu tương tác phi tuyến có ích không.

Giới hạn trước một lưới tham số nhỏ vì validation chỉ có 28 ván.
Có thể thử biểu diễn `A − B` như một thí nghiệm riêng, không mặc định tốt hơn biểu diễn hai phía.
Lưu seed, tham số, phiên bản thư viện và phiên bản dataset cho từng lần chạy.

**Tiêu chí hoàn thành:** Có bảng so sánh baseline và hai mô hình trên validation, kèm cấu hình đủ để chạy lại.

### D. Đánh giá và chốt mô hình

- Dùng **Brier score hoặc log loss** làm chỉ số chính đánh giá xác suất. Báo cáo thêm accuracy, balanced accuracy, ma trận nhầm lẫn và số mẫu.
- Kiểm tra tính nhất quán khi đổi tên đội A/B: đổi hai đội hình, đảo phe và kỳ vọng xác suất mới xấp xỉ `1 − p` cũ. Nếu cần đối xứng hóa xác suất, quyết định dựa trên validation trước khi xem test.
- Phân tích riêng trường hợp có tướng/patch chưa thấy trong train, nhưng không điều chỉnh pipeline dựa trên nhãn test.
- Chốt mô hình và ngưỡng dự đoán từ validation, sau đó chạy test **một lần** và so sánh với baseline. Không cam kết trước accuracy: test chỉ có 40 ván, trong đó đội A thắng 27 ván.

**Tiêu chí hoàn thành:** Báo cáo kết quả test cuối cùng, phân tích sai số và nêu rõ nếu mô hình không vượt baseline; không quảng bá bản thử nghiệm là dự đoán đáng tin cậy khi chưa đủ bằng chứng.

### E. Đưa vào ứng dụng

- Lưu artifact gồm pipeline, mô hình, danh mục tướng, danh mục patch, phiên bản dataset và cấu hình đánh giá. Tải artifact khi ứng dụng khởi động, không huấn luyện lại cho mỗi lượt dự đoán.
- Làm giao diện tối thiểu: chọn 5 tướng mỗi bên, phe đội A, patch được hỗ trợ; chặn tướng trùng và đội hình thiếu.
- Tạo hàm/API `predict(team_a_heroes, team_b_heroes, team_a_side, patch_id)` trả về xác suất, đội dự đoán thắng và cảnh báo nếu có danh mục ngoài train.
- Hiển thị giới hạn sử dụng cạnh kết quả: mô hình học từ **299 ván của một giải chuyên nghiệp**, không bảo đảm áp dụng cho xếp hạng hoặc patch mới. Kiểm tra quyền sử dụng/ghi nguồn dữ liệu trước khi phát hành công khai.

**Tiêu chí hoàn thành:** Đội hình hợp lệ cho cùng kết quả ở notebook, hàm dự đoán và giao diện; đầu vào sai nhận lỗi rõ ràng.

## 4. Kiểm thử và sản phẩm bàn giao

Kiểm thử: JSON lỗi, thiếu/thừa tướng, tướng trùng trong/cross-team, phe sai, patch mới, tướng mới, bất biến theo thứ tự tướng, tính nhất quán khi đổi hai đội và không có series giao nhau giữa các tập.

Sản phẩm: script/notebook kiểm tra dữ liệu; pipeline huấn luyện và đánh giá; artifact mô hình; hàm/API cùng giao diện demo; bảng so sánh mô hình, biểu đồ đánh giá và hướng dẫn chạy. Tách mã dùng lại khỏi notebook để demo sử dụng đúng quy trình đã đánh giá.

**Ưu tiên:** Hoàn tất A–D và chứng minh kết quả tái lập được trước khi đầu tư vào giao diện. Nếu thời gian hạn chế, một form demo đơn giản là đủ; độ tin cậy của đánh giá quan trọng hơn giao diện phức tạp.
