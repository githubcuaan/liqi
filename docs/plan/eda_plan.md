# Kế hoạch EDA cho dataset AOG Spring 2026

## Mục tiêu

Mô tả quy mô và cấu trúc dữ liệu, đánh giá phân phối và chất lượng, phát hiện dữ liệu thiếu/bất thường, đồng thời xác định các điểm cần lưu ý trước khi tiền xử lý. EDA chỉ mô tả dữ liệu; không huấn luyện mô hình hoặc điều chỉnh quy trình dựa trên kết quả test.

## Phạm vi dữ liệu

Dataset nằm tại `dataset/035ce761e53a47db/`. Các bảng chính:

- `csv/train.csv`, `csv/validation.csv`, `csv/test.csv`: dữ liệu dự đoán, mỗi dòng là một trận.
- `csv/games.csv`, `csv/series.csv`, `csv/teams.csv`, `csv/heroes.csv`: bảng tham chiếu/tra cứu.
- `csv/association_train.csv`: giao dịch train-only phục vụ phân tích luật kết hợp.
- Các bảng thống kê khác chỉ dùng cho mô tả; không dùng làm đặc trưng dự đoán.

Đầu vào baseline được quy định trong `feature_schema.json`: `team_a_heroes`, `team_b_heroes`, `team_a_side`, `patch_id`. Nhãn là `team_a_win`. ID và metadata chỉ phục vụ kiểm tra/ghép bảng, không phải đặc trưng.

## Các bước thực hiện

### 1. Khảo sát cấu trúc và quy mô

Với mỗi tập train, validation và test, thống kê:

- Số dòng, số cột, tên cột và kiểu dữ liệu.
- Số giá trị phân biệt, ví dụ giá trị và tỷ lệ thiếu theo cột.
- Số trận và số series duy nhất khi có định danh tương ứng.

Lập bảng mô tả thuộc tính gồm tên, ý nghĩa, kiểu dữ liệu, vai trò (đầu vào/nhãn/metadata) và cách biểu diễn. Đối chiếu các trường đầu vào và nhãn với `feature_schema.json`.

### 2. Kiểm tra tính toàn vẹn và bất thường

Kiểm tra riêng từng tập và toàn bộ dữ liệu:

- Dòng trùng hoàn toàn, trùng `game_id` hoặc định danh trận.
- Nhãn `team_a_win` có giá trị hợp lệ; `team_a_side` chỉ gồm `blue`/`red`.
- `patch_id` có mặt và đúng định dạng.
- Hai trường đội hình parse được như JSON, mỗi đội có đúng 5 tướng.
- Đội hình không có tướng lặp; kiểm tra tướng có bị trùng giữa hai đội trong cùng trận hay không.
- ID tướng có ánh xạ được tới danh mục tham chiếu hay không.

Thống kê số lượng theo từng loại lỗi. Không tự động loại bản ghi chỉ vì bất thường; ghi nhận để quyết định và giải thích ở bước tiền xử lý.

### 3. Phân tích dữ liệu thiếu

Với mỗi cột, tính số giá trị thiếu và tỷ lệ phần trăm. Đếm thêm số dòng thiếu ít nhất một trường đầu vào. Với đội hình, kiểm tra riêng chuỗi rỗng, JSON lỗi, mảng thiếu/thừa tướng và ID không ánh xạ được.

Phân biệt missing với danh mục chưa thấy trong train. Dataset ghi nhận một số tướng ở holdout chưa xuất hiện trong train và patch `aov:vn:2026-04-23` chỉ có ở test; đây là danh mục mới, không phải dữ liệu thiếu.

### 4. Phân tích phân phối nhãn và biến phân loại

Với `team_a_win`, thống kê số trận đội A thắng/thua và tỷ lệ theo từng tập. Đối chiếu kết quả tính từ CSV với `split_manifest.json`; manifest hiện ghi:

| Tập        | Số trận | Đội A thắng | Đội A thua |
| ---------- | ------: | ----------: | ---------: |
| Train      |     231 |         128 |        103 |
| Validation |      28 |          16 |         12 |
| Test       |      40 |          27 |         13 |

Với `team_a_side` và `patch_id`, tính tần suất và tỷ lệ; lập bảng chéo nhãn theo phe và patch. Nêu rõ patch có ít mẫu hoặc chỉ xuất hiện ở test. Không diễn giải thống kê mô tả thành quan hệ nhân quả.

### 5. Phân tích đội hình và tướng

Parse đội hình thành các lượt chọn tướng, sau đó thống kê:

- Tổng số tướng duy nhất trong dataset và trong train.
- Tần suất chọn từng tướng; nhóm tướng phổ biến và ít xuất hiện.
- Tần suất theo đội A/B, phe và patch khi số lượng mẫu cho phép.
- Tỷ lệ thắng quan sát được khi có từng tướng, luôn kèm số trận.

Tỷ lệ của tướng ít xuất hiện có độ bất định cao;
không kết luận sức mạnh tướng chỉ từ tỷ lệ thô. Nếu phân tích cặp tướng/association rules, chỉ fit trên `association_train.csv` hoặc dữ liệu train;
không fit trên toàn bộ `association_transactions.csv` rồi đánh giá trên cùng dữ liệu.

### 6. So sánh các tập dữ liệu

Lập bảng so sánh train, validation, test về số trận, tỷ lệ thắng, phân bố phe và patch, số tướng duy nhất, số danh mục mới so với train và tỷ lệ đội hình hợp lệ.
Chỉ dùng kết quả này để mô tả; không dùng test để điều chỉnh tiền xử lý hay mô hình.
Do các tập holdout nhỏ, ưu tiên nhận xét thận trọng, không khái quát quá mức.

### 7. Trực quan hóa trong EDA

Tạo các biểu đồ gọn, dễ đọc:

1. Bar chart số trận và tỷ lệ thắng/thua theo tập.
2. Bar chart phân bố phe xanh/đỏ.
3. Bar chart số trận theo patch.
4. Bar chart ngang top 10–15 tướng được chọn nhiều nhất.
5. Heatmap hoặc bảng màu tỷ lệ thắng theo phe/patch, kèm số mẫu.
6. Bar chart số bản ghi thiếu, JSON lỗi, đội hình sai số lượng tướng và trùng lặp.

Mỗi biểu đồ có tiêu đề, nhãn trục, đơn vị/tỷ lệ và chú thích mẫu nhỏ. Không đưa quá nhiều hạng mục vào một biểu đồ.

### 8. Tổng hợp kết quả EDA

Tóm tắt ngắn gọn:

- Quy mô, phạm vi và đơn vị quan sát.
- Các thuộc tính, nhãn và phân phối chính.
- Tình trạng thiếu, trùng và bất thường.
- Đặc điểm nổi bật của tướng, phe và patch.
- Khác biệt giữa các tập, đặc biệt danh mục mới ở holdout.
- Hạn chế: chỉ một giải đấu và 299 trận; chia thời gian dựa trên lịch series, chưa xác minh thời điểm thi đấu thực tế.
- Hệ quả đối với tiền xử lý và đánh giá mô hình.

## Sản phẩm đầu ra

- Notebook hoặc script tái lập được các thống kê.
- Bảng mô tả thuộc tính.
- Bảng kiểm tra chất lượng, missing và bất thường.
- 4–6 biểu đồ có chú thích/nhận xét.
- Phần kết luận EDA làm cơ sở cho kế hoạch tiền xử lý.
