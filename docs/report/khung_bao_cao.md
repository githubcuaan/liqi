# Khung báo cáo đồ án: Liqily

**Tên đề tài đề xuất:** Liqily — phân tích cặp tướng, dự đoán kết quả và gợi ý cấm/chọn trong Liên Quân Mobile từ dữ liệu Đấu Trường Danh Vọng mùa Xuân 2026.

> Báo cáo bao quát **ba chức năng ngang hàng** nêu trong `docs/gioi_thieu_bai_toan.md`: (1) dự đoán đội thắng theo lineup, (2) nhận biết cặp tướng phối hợp tốt bằng luật kết hợp, (3) gợi ý cấm/chọn. Đây là khung báo cáo, không phải khẳng định cả ba đã triển khai. Dự án hiện có notebook EDA, làm sạch và trực quan hóa; kết quả thực nghiệm còn thiếu phải được điền sau khi thực hiện.

## Tóm tắt

Khoảng 150–250 từ: nêu rõ cả ba chức năng, nguồn/quy mô dữ liệu, phương pháp tương ứng, kết quả thực nghiệm riêng của từng chức năng, hạn chế và đóng góp. Viết sau khi hoàn thành các chương.

## Chương 1. Giới thiệu đề tài và bộ dữ liệu

### 1.1. Bối cảnh, mục tiêu và phạm vi

- Giới thiệu Liqily và nhu cầu phân tích đội hình trong Liên Quân Mobile.
- **Chức năng 1 — Dự đoán:** nhập đủ hai đội hình, phe và patch; trả về xác suất đội A thắng một ván. Dự đoán sau chọn tướng, không phải dự đoán cả series.
- **Chức năng 2 — Cặp tướng:** khai phá luật kết hợp để tìm các tướng thường được chọn cùng đội; kiểm tra thêm bằng dữ liệu thắng/thua trước khi gọi là “phối hợp tốt”.
- **Chức năng 3 — Gợi ý cấm/chọn:** nhận trạng thái cấm/chọn hiện tại, xếp hạng lựa chọn hợp lệ và giải thích vì sao gợi ý; xác định rõ đầu vào, đầu ra, quy tắc và giới hạn khả năng đánh giá.
- Câu hỏi nghiên cứu tương ứng: (1) dự đoán có vượt baseline không? (2) cặp tướng nào có support/lift đáng chú ý và có bằng chứng hiệu quả? (3) gợi ý có hợp lệ, nhất quán và hữu ích hơn baseline đơn giản không?
- Phân biệt **mục tiêu sản phẩm** với **chức năng đã triển khai/đánh giá**. `docs/du_doan_thang_thua_plan.md` chỉ mô tả kế hoạch cho chức năng 1, không giới hạn phạm vi của toàn bộ Liqily.

### 1.2. Nguồn và cấu trúc dữ liệu

- Nguồn: bản dữ liệu Đấu Trường Danh Vọng mùa Xuân 2026, có thông tin nguồn Liquipedia; ghi phiên bản snapshot theo `dataset/035ce761e53a47db/README.md`.
- Phân biệt đơn vị quan sát: **một ván** cho dự đoán (299 ván thuộc 75 series); **một đội hình của một đội** cho luật kết hợp; **một trạng thái cấm/chọn** cho chức năng gợi ý (cần định nghĩa cách tạo và kiểm tra dữ liệu đánh giá riêng).
- Chỉ bốn trường đầu vào hợp lệ của baseline dự đoán: `team_a_heroes`, `team_b_heroes`, `team_a_side`, `patch_id`; nhãn: `team_a_win` (`feature_schema.json`). Với luật kết hợp, dùng các giao dịch đội hình train. Với gợi ý, xác định các trường sẵn có tại thời điểm ra quyết định và nguồn của chúng; không đồng nhất dữ liệu đội hình hoàn chỉnh với log lượt cấm/chọn.
- Lập bảng từ điển thuộc tính: tên trường, kiểu, ý nghĩa, ví dụ, vai trò (đầu vào/nhãn/metadata). Giải thích vì sao không dùng thông tin sau trận hoặc thống kê toàn giải làm đặc trưng.

| Tập        | Series | Ván | Đội A thắng | Đội A thua |
| ---------- | -----: | --: | ----------: | ---------: |
| Train      |     60 | 231 |         128 |        103 |
| Validation |      7 |  28 |          16 |         12 |
| Test       |      8 |  40 |          27 |         13 |

_Nguồn: `dataset/035ce761e53a47db/split_manifest.json`._

## Chương 2. Cơ sở lý thuyết và thuật toán cho ba chức năng

### 2.1. Bài toán phân loại nhị phân

Phát biểu đầu vào, nhãn và xác suất `P(team_a_win)`. Giải thích baseline đoán lớp đa số/tỷ lệ thắng train; định nghĩa accuracy, balanced accuracy, ma trận nhầm lẫn và chỉ số đánh giá xác suất **Brier score hoặc log loss**. Có thể bổ sung precision, recall, F1, ROC-AUC nếu đã tính và diễn giải phù hợp với cỡ mẫu.

### 2.2. Biểu diễn đội hình

- Mô tả cách mã hóa đang có trong `notebook/02_CleaningData.ipynb`: mỗi tướng từ train có một cột, giá trị +1 khi ở đội A, −1 khi ở đội B, 0 khi không có hoặc bị hai phía triệt tiêu; phe và patch dùng one-hot encoding.
- Nêu ưu điểm của biểu diễn tập không thứ tự và hạn chế: khó biểu diễn tương tác giữa tướng; giá trị 0 không luôn có nghĩa là không xuất hiện.
- Nếu thử biểu diễn **hai cột nhị phân riêng cho đội A/B** theo kế hoạch dự đoán, trình bày như một phương án thực nghiệm khác; không ghi là cách mã hóa hiện tại.

### 2.3. Mô hình dự đoán cần thực nghiệm

Giải thích nguyên lý, ưu/nhược điểm, siêu tham số và lý do chọn cho từng phương pháp thực sự chạy:

1. Baseline đơn giản: lớp đa số hoặc xác suất thắng quan sát trong train.
2. Logistic Regression có regularization: mốc tuyến tính dễ giải thích.
3. Random Forest giới hạn độ sâu **hoặc** mô hình cây tăng cường có kiểm soát độ phức tạp: kiểm tra lợi ích của quan hệ phi tuyến.

Ít nhất hai phương pháp được so sánh theo yêu cầu đồ án. Các mục trên là **đề xuất thực nghiệm**, chưa phải kết quả đã triển khai.

### 2.4. Khai phá luật kết hợp và đánh giá cặp tướng

Xem một đội hình của một đội là một giao dịch; chỉ dùng `csv/association_train.csv` để khai phá. Trình bày Apriori hoặc FP-Growth, định nghĩa support, confidence, lift và ý nghĩa của từng ngưỡng. So sánh với cách xếp cặp theo đồng xuất hiện đơn thuần; nếu muốn nói “cặp mạnh”, báo thêm số đội hình chứa cặp, tỷ lệ thắng quan sát và độ bất định, đối chiếu trên dữ liệu không dùng để chọn luật khi có thể. **Cùng xuất hiện ≠ gây ra chiến thắng**: lựa chọn tướng chịu ảnh hưởng đội tuyển, patch và đối thủ.

### 2.5. Phương pháp gợi ý cấm/chọn

- Định nghĩa bài toán **chọn**: với các tướng đã chọn của ta/đối thủ và danh sách tướng còn hợp lệ, trả về top-k tướng gợi ý. Bài toán **cấm** cần định nghĩa riêng: tướng nào nên loại khỏi lựa chọn của đối thủ và vì sao. Mô tả luật hợp lệ: không gợi ý tướng đã chọn, đã cấm hoặc trùng; xét patch và khả năng xuất hiện của tướng.
- Đề xuất một **baseline** (tướng phổ biến theo train), và một cách xếp hạng dựa trên luật kết hợp, ví dụ ưu tiên synergy với tướng ta, hạn chế synergy của đối thủ; nếu dùng thêm mô hình dự đoán, chỉ chấm **đội hình hoàn chỉnh có điều kiện** hoặc nêu rõ cách ước lượng khi thiếu tướng. Trình bày công thức điểm, trọng số, ngưỡng hỗ trợ và cách giải thích từng gợi ý **sau khi chọn phương án triển khai**.
- Không nhập đội hình thiếu vào mô hình chỉ được huấn luyện cho 10 tướng rồi gọi xác suất đó là dự đoán hợp lệ. Dữ liệu hiện không xác minh thứ tự draft hoặc lượt cấm; nếu thiếu log draft đáng tin cậy, chức năng cấm/chọn chỉ nên được trình bày là **gợi ý heuristic/ứng dụng thử nghiệm**, không khẳng định tối ưu chiến thuật.

## Chương 3. Tiền xử lý và quy trình thực nghiệm

### 3.1. Khảo sát, kiểm tra chất lượng

Từ `notebook/01_EDA.ipynb` và `notebook/03_DataVisualization.ipynb`, lập bảng phân bố nhãn, phe, patch, tướng phổ biến; báo cáo dữ liệu thiếu, trùng `game_id`, JSON lỗi, đội hình sai số lượng tướng, ID lạ hoặc tướng trùng. Nêu số bản ghi bị ảnh hưởng theo từng tập thay vì tự điền số chưa kiểm tra.

### 3.2. Tiền xử lý theo từng chức năng

- **Dự đoán:** chuyển `true/false` sang `1/0`, chuẩn hóa chuỗi, parse JSON đội hình, xây từ vựng tướng từ train và mã hóa phe/patch. Notebook hiện ghi nhận **88 đặc trưng: 83 tướng và 5 đặc trưng phân loại**.
- **Cặp tướng:** chuyển `hero_ids` của từng giao dịch thành tập tướng; loại/ghi nhận giao dịch lỗi; tách giao dịch có nhãn thắng nếu phân tích hiệu quả. Không coi hai đội của cùng ván là hai quan sát độc lập khi ước lượng độ bất định.
- **Cấm/chọn:** xây danh mục tướng có thể chọn, trạng thái đã chọn/đã cấm và tập ứng viên hợp lệ; nêu cách xử lý patch mới, tướng mới, dữ liệu thiếu và trường hợp không có luật đủ support. Không suy diễn thứ tự cấm/chọn từ thứ tự ID trong mảng đội hình.

### 3.3. Chia tập và chống rò rỉ

- Giữ cách chia sẵn theo lịch series: 231 ván train, 28 validation, 40 test; mọi ván cùng series thuộc cùng một tập.
- Chỉ fit encoder, mô hình dự đoán, luật kết hợp, thống kê cặp và trọng số gợi ý trên train; chọn tham số/ngưỡng bằng validation; đánh giá test **một lần sau khi chốt**. Giữ series cùng tập cho cả ba luồng đánh giá.
- Không dùng `winner_team_id`, vàng, mạng hạ gục, thời lượng, thống kê tướng toàn giải, `series_id`, thời gian chia tập hoặc các thuộc tính sau trận làm đầu vào.
- Kiểm tra danh mục tướng mới ở holdout và patch `aov:vn:2026-04-23` chỉ có ở test mà không fit lại encoder trên holdout.

### 3.4. Ba quy trình thực nghiệm có thể tái lập

Ghi môi trường, thư viện/phiên bản, seed và phiên bản dữ liệu. Tách ba luồng:

1. **Dự đoán:** CSV → kiểm tra → mã hóa → baseline và mô hình → chọn trên validation → đánh giá test.
2. **Cặp tướng:** giao dịch train → khai phá luật → lọc theo support/confidence/lift → kiểm tra tần suất và thắng/thua trên holdout khi phù hợp; báo số mẫu và điều kiện lọc.
3. **Cấm/chọn:** trạng thái đầu vào → lọc ứng viên hợp lệ → chấm/xếp hạng → giải thích → đánh giá offline và minh họa tình huống; nêu rõ trạng thái đánh giá được tái tạo từ nguồn nào. Nếu không có log thứ tự draft/ban đáng tin cậy, không giả định dữ liệu đã có nhãn “lượt cấm/chọn tối ưu”.

## Chương 4. Kết quả, bảng so sánh, biểu đồ và nhận xét

### 4.1. EDA và trực quan hóa

Chọn biểu đồ từ các notebook: số ván và tỷ lệ nhãn theo tập; phe/patch; tướng được chọn nhiều; tỷ lệ thắng quan sát theo tướng **kèm số ván**; tần suất cặp tướng; ma trận đặc trưng. Mỗi hình có tên, trục, đơn vị, nguồn và nhận xét. Không suy ra tướng mạnh chỉ từ tỷ lệ thắng thô của mẫu nhỏ.

### 4.2. Kết quả mô hình dự đoán

| Phương pháp                          | Validation Brier/log loss | Test Brier/log loss | Test accuracy | Test balanced accuracy | Nhận xét  |
| ------------------------------------ | ------------------------: | ------------------: | ------------: | ---------------------: | --------- |
| Baseline                             |                         … |                   … |             … |                      … | Mốc cơ sở |
| Logistic Regression                  |                         … |                   … |             … |                      … | …         |
| Random Forest/mô hình cây tăng cường |                         … |                   … |             … |                      … | …         |

Chỉ điền **số thực đo** sau khi chạy. Bổ sung ma trận nhầm lẫn, đồ thị hiệu chỉnh xác suất/độ tin cậy nếu có, kết quả khi gặp tướng/patch mới và phân tích lỗi. Nêu rõ nếu mô hình không vượt baseline; test chỉ có 40 ván nên tránh kết luận quá mức.

### 4.3. Kết quả cặp tướng

| Cặp/luật tướng | Số giao dịch chứa luật | Support | Confidence | Lift | Nhận xét |
| -------------- | ---------------------: | ------: | ---------: | ---: | -------- |
| …              |                      … |       … |          … |    … | …        |

Kèm biểu đồ top cặp theo support/lift, tỷ lệ thắng quan sát và số mẫu; đối chiếu với baseline xếp theo đồng xuất hiện. Nếu đánh giá cặp tướng là “hiệu quả”, cần phân tích thêm nhãn thắng/thua trên dữ liệu phù hợp và tránh khẳng định khả năng tổng quát hóa từ chính tập đã dùng khai phá luật.

### 4.4. Kết quả gợi ý cấm/chọn

| Tình huống/trạng thái              | Baseline gợi ý | Phương pháp đề xuất | Hợp lệ? | Lý do gợi ý | Đánh giá |
| ---------------------------------- | -------------- | ------------------- | ------- | ----------- | -------- |
| Đội ta có …; đối thủ có …; patch … | …              | …                   | …       | …           | …        |
| Đội ta có …; tướng … đã cấm        | …              | …                   | …       | …           | …        |

Thống kê tỷ lệ gợi ý hợp lệ, độ bao phủ (bao nhiêu trạng thái có đủ dữ liệu để gợi ý), top-k theo tiêu chí được định nghĩa trước và ví dụ lỗi/không chắc chắn. Nếu có cách đánh giá offline hợp lệ, so sánh cùng các trạng thái với baseline, có thể báo hit@k đối với lựa chọn quan sát được; **hit@k đo mức giống lựa chọn trong dữ liệu, không đo chất lượng chiến thuật**. Không báo “tỷ lệ thắng nhờ gợi ý” khi chưa có đánh giá can thiệp.

### 4.5. Tích hợp và minh họa sản phẩm

Chèn sơ đồ luồng dữ liệu và ba màn hình/luồng **sau khi triển khai**: (1) nhập hai đội hình, phe, patch → dự đoán; (2) xem luật và bằng chứng của cặp tướng; (3) nhập trạng thái hiện tại → gợi ý cấm/chọn có giải thích. Ghi rõ từng chức năng là kế hoạch, nguyên mẫu hay đã được đánh giá định lượng.

## Chương 5. So sánh với phương pháp hiện đại

Trình bày theo **ba nhánh**, không chỉ nhánh dự đoán: (1) Logistic Regression so với mô hình phi tuyến/biểu diễn tương tác đội hình; (2) Apriori so với FP-Growth hoặc luật kết hợp so với cách tìm cặp bằng đồng xuất hiện; (3) heuristic gợi ý so với cách xếp hạng theo luật, mô hình học xếp hạng hoặc phương pháp hiện đại phù hợp nếu có dữ liệu. Chỉ so sánh định lượng khi cùng tập chia, cùng dữ liệu đầu vào và tiêu chí phù hợp **với từng chức năng**. Phương pháp chỉ đọc qua tài liệu thì trình bày trong phần thảo luận, không ghi thành kết quả đã chạy.

## Chương 6. Kết luận, hạn chế và hướng phát triển

- Kết luận **riêng từng chức năng**: mức độ dự đoán so với baseline; cặp tướng tìm được và mức độ tin cậy; khả năng áp dụng, tính hợp lệ và giới hạn của gợi ý cấm/chọn. Nêu mức độ hoàn thiện của toàn sản phẩm.
- Hạn chế: một giải đấu với 299 ván; validation/test nhỏ; mốc chia thời gian dùng **lịch series** chứ chưa xác minh thời gian thi đấu thực; tướng/patch mới; luật kết hợp chịu ảnh hưởng tần suất chọn và đội tuyển; chưa xác minh thứ tự cấm/chọn, vai trò, trang bị hoặc khả năng áp dụng cho người chơi xếp hạng.
- Hướng phát triển: mở rộng nhiều mùa giải/patch, đánh giá theo thời gian, thử biểu diễn tương tác đội hình, bổ sung log draft/ban đáng tin cậy, kiểm chứng chất lượng gợi ý bằng thử nghiệm phù hợp, rà soát quyền sử dụng dữ liệu trước khi phát hành công khai.

## Tài liệu tham khảo và phụ lục

- Nguồn giải đấu Liquipedia, URL trang nguồn và ngày truy cập; README, `feature_schema.json`, `split_manifest.json` của snapshot dữ liệu.
- Công trình gốc và tài liệu triển khai của **những thuật toán thực sự sử dụng**; tài liệu thư viện và phiên bản phần mềm.
- Phụ lục: sơ đồ pipeline, từ điển thuộc tính đầy đủ, cấu hình/seed, bảng kết quả mở rộng, hướng dẫn chạy notebook và mã nguồn.

**Thứ tự hoàn thiện:** Điền giới thiệu và EDA từ notebook hiện có → triển khai/đánh giá riêng cả ba chức năng → tổng hợp kết quả, so sánh và kết luận bằng số liệu thực đo. Không dùng kết quả của chức năng dự đoán thay cho bằng chứng hiệu quả của cặp tướng hay gợi ý cấm/chọn.
