# Kịch bản thuyết trình Liqily — 15 phút

**Chủ đề:** Khám phá dữ liệu và hỗ trợ phân tích cấm chọn Liên Quân Mobile  
**Gợi ý:** Mở sẵn web app, demo ba tính năng chính; dành khoảng 1 phút cuối cho câu hỏi.

## 0:00–1:00 | Mở đầu

> Xin chào thầy cô và các bạn.
> Khi theo dõi một trận Liên Quân, chúng ta thường tự hỏi:
> những tướng nào hay được chọn cùng nhau,
> nên cân nhắc cấm hoặc chọn tướng nào,
> và đội hình đã hoàn tất thì cơ hội thắng ra sao?
>
> Nhóm em xây dựng **Liqily** — một ứng dụng khai thác dữ liệu giải đấu để giúp trả lời những câu hỏi đó bằng ba góc nhìn:
> khám phá đội hình, trợ lý cấm chọn và thử nghiệm dự đoán sau khi đã chọn đủ hai đội hình.

## 1:00–2:30 | Bài toán và mục tiêu

> Cấm chọn thường dựa nhiều vào kinh nghiệm cá nhân. Trong khi đó, dữ liệu giải đấu có thể cho ta thêm góc nhìn về những mẫu hình đã xuất hiện.
>
> Mục tiêu của Liqily không phải đưa ra “đội hình chắc thắng”, mà là biến dữ liệu thành thông tin dễ khám phá:
> tìm luật kết hợp, tham khảo gợi ý pick/ban và thử nghiệm mô hình dự đoán.
>
> Câu hỏi quan trọng của dự án là: **làm thế nào để cung cấp thông tin hữu ích mà vẫn nói rõ dữ liệu và mô hình thực sự chứng minh được điều gì?**

## 2:30–5:00 | Dữ liệu → xử lý → phân tích trực quan

### 2:30–3:25 | Nguồn và cấu trúc dữ liệu

> Dữ liệu được tổng hợp từ thông tin giải **Đấu Trường Danh Vọng mùa Xuân 2026** trên Liquipedia, với **299 ván**. Đây là bảng dữ liệu dạng hàng và cột: **mỗi hàng là một ván**, không phải một tướng hay một series.
>
> Nếu nhìn vào một hàng mẫu, `game_id` xác định ván và `series_id` cho biết ván thuộc loạt trận nào. Hai cột `team_a_heroes` và `team_b_heroes` lưu danh sách **năm ID tướng mỗi đội**; `team_a_side` ghi phe xanh hoặc đỏ; `patch_id` ghi phiên bản; `team_a_win` là nhãn đúng/sai cho biết đội A có thắng không.
>
> Bảng CSV còn có cột về nguồn và xuất xứ để đối chiếu, nhưng mô hình **chỉ dùng bốn nhóm đầu vào**: tướng đội A, tướng đội B, phe đội A và patch; nhãn thắng/thua chỉ dùng khi huấn luyện, không đưa vào đầu vào dự đoán. Ngoài bảng ván đấu còn có danh mục tướng và dữ liệu cấm chọn phục vụ tra cứu.

**Bảng minh họa một hàng dữ liệu** (ván đầu tiên trong `dataset/035ce761e53a47db/csv/train.csv`):

| `game_id` | `series_id` | `team_a_heroes` | `team_b_heroes` | `team_a_side` | `patch_id` | `team_a_win` |
| --- | --- | --- | --- | --- | --- | --- |
| `…:M1:map1` | `…:M1` | Hayate, Iggy, Tachi, Toro, Biron | Y'bneth, Keera, Marja, Heino, Capheny | `red` | `aov:vn:2026-02-14` | `true` |

*Để dễ trình chiếu, hai mã định danh được rút gọn và ID tướng trong CSV được ánh xạ sang tên; đây là **một hàng thật**, không phải dữ liệu giả. Bảng chỉ hiển thị các cột chính: CSV còn có `game_number`, thông tin chia tập, thời gian theo lịch series và các cột truy xuất nguồn. `game_id`/`series_id` dùng để định danh và chia tập, **không** là đầu vào mô hình.*

**Khi chiếu:** Chỉ vào hai cột đội hình (đầu vào), cột phe và patch (đầu vào), rồi cột `team_a_win` (nhãn). Không cần đọc từng tướng.

### 3:25–4:05 | Luồng xử lý dữ liệu

> Luồng xử lý có thể tóm tắt như sau:
> **dữ liệu trận đấu → kiểm tra chất lượng và chuẩn hóa đội hình/tướng → tách train, validation, test theo series → khám phá dữ liệu và tạo đầu vào cho từng chức năng**.
>
> Nhóm kiểm tra các trường thiếu, đội hình có đúng năm tướng, JSON có đọc được và ID trận có trùng không.
> Sau đó chia thành **231 ván train / 60 series**, **28 ván validation / 7 series** và **40 ván test / 8 series**, giữ các ván cùng series trong cùng một tập.
>
> Từ train, mỗi ván tạo hai giao dịch đội hình, tức **462 transaction** cho khai phá luật kết hợp.
> Phần dự đoán chỉ học trên train; validation dùng để chọn mô hình, test dùng để đánh giá cuối cùng.

### 4:05–5:00 | Nhìn nhanh qua các biểu đồ EDA

> Ở **biểu đồ quy mô và nhãn**, train có 231 ván, còn validation và test nhỏ hơn nhiều. Tỷ lệ đội A thắng lần lượt khoảng **55%, 57% và 68%**;
> vì test chỉ có 40 ván, một con số accuracy cao vẫn cần được so với baseline và phân tích theo từng lớp.
>
> **Biểu đồ phân bố patch** cho thấy patch ngày **23/04/2026** chỉ có ở test.
> Đây là tình huống mô hình gặp một phiên bản chưa thấy trong train, nên không thể mặc nhiên kỳ vọng kết quả ổn định.
>
> Cuối cùng, **biểu đồ tướng được chọn nhiều** cho thấy Toro đứng đầu về lượt chọn trong toàn giải. Tần suất chọn phản ánh xu hướng xuất hiện, **không tự nó chứng minh tướng mạnh hơn**. Những quan sát này giúp nhóm hiểu dữ liệu trước khi chuyển sang ba chức năng của sản phẩm.

**Biểu đồ nên chiếu theo thứ tự:**

1. [Quy mô và phân bố nhãn](../../visualization_output/01_eda/01_quy_mo_va_nhan.png).
2. [Phân bố theo patch](../../visualization_output/01_eda/03_phan_bo_patch.png).
3. [Top tướng được chọn](../../visualization_output/01_eda/04_top_tuong.png).

**Lưu ý:** Biểu đồ EDA mô tả cả ba tập để hiểu dữ liệu; thống kê đưa vào web, khai phá và huấn luyện chỉ dùng train, không dùng test để chọn lại mô hình.

## 5:00–5:45 | Giới thiệu sản phẩm

> Đây là giao diện Liqily. Ứng dụng có ba chức năng chính.
>
> Một là **khám phá dữ liệu**, để tìm luật kết hợp và các combo đã xuất hiện.  
> Hai là **trợ lý cấm chọn**, đưa ra gợi ý dựa trên dữ liệu train.  
> Ba là **dự đoán sau draft**, thử ước lượng kết quả khi đã biết đầy đủ hai đội hình, phe và patch.
>
> Sau đây, em xin minh họa nhanh từng chức năng.

## 5:45–8:15 | Demo 1: Khám phá đội hình

> Ở mục “Khám phá đội hình”, người dùng có thể chọn Apriori hoặc FP-Growth, sau đó điều chỉnh support, confidence và lift trước khi chạy phân tích.
> Hai thuật toán cũng có thể được so sánh trên cùng dữ liệu và ngưỡng.
>
> Kết quả hiển thị các luật kết hợp cùng những chỉ số như support, confidence và lift.
> Người dùng có thể xem combo quan sát được, tra cứu một nhóm tướng cụ thể hoặc tải kết quả dạng CSV.
>
> Cần lưu ý: các chỉ số này mô tả những gì thường xuất hiện trong dữ liệu.
> Ví dụ, một luật có confidence cao **không có nghĩa** đội hình đó gây ra chiến thắng. Đây là mối liên hệ quan sát được, không phải bằng chứng nhân quả.

**Thao tác demo:** Chạy phân tích với thiết lập có sẵn; mở bảng luật hoặc tab combo; nếu thuận tiện, thử tra cứu một nhóm tướng.

**Bảng so sánh Apriori và FP-Growth** trên 462 giao dịch train, cùng ngưỡng support ≥ 1%, confidence ≥ 50%, lift ≥ 1 và tối đa 5 tướng:

| Thuật toán | Tập phổ biến | Tổng số luật | Luật → thắng | Luật → thua | Thời gian một lần chạy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Apriori | 752 | 308 | 102 | 75 | 0,0285 giây |
| FP-Growth | 752 | 308 | 102 | 75 | 0,0337 giây |

> Hai thuật toán cho cùng số tập và luật ở cấu hình này; thời gian rất nhỏ và phụ thuộc máy chạy, **không kết luận thuật toán nào luôn nhanh hơn** từ một lần đo. 308 là tổng mọi luật, còn hai cột thắng/thua chỉ đếm luật có kết quả trận là vế phải.

*Nguồn: chạy `AlgorithmComparer` trên `association_train.csv` với cấu hình của giao diện (support 0,01; confidence 0,5; lift 1; max_heroes 5).*

## 8:15–10:00 | Demo 2: Trợ lý cấm chọn

> Tiếp theo là trợ lý cấm chọn. Người dùng nhập tướng của đội mình, đội đối thủ và các tướng đã bị cấm hoặc khóa, rồi yêu cầu gợi ý chọn hoặc cấm.
>
> Với gợi ý chọn, hệ thống xếp hạng theo độ tương đồng cosine với các tướng đồng đội. Với gợi ý cấm, hệ thống dựa trên tần suất tướng bị cấm trong tập train. Mỗi gợi ý có thông tin để người dùng hiểu điểm số dựa trên đâu.
>
> Vì vậy, đây là công cụ tham khảo dữ liệu — không phải bộ tối ưu chiến thuật. Điểm pick không phải xác suất thắng; tần suất ban cũng không đo mức độ khắc chế.

**Thao tác demo:** Chọn một hoặc hai tướng ở đội mình, chọn gợi ý pick, rồi cho xem danh sách Top 5.

**Bảng kết quả và phạm vi đánh giá của hai cách gợi ý:**

| Tác vụ | Cách xếp hạng đang dùng | Bằng chứng/kết quả hiện có | Giới hạn |
| --- | --- | --- | --- |
| Gợi ý chọn (pick) | Cosine đồng xuất hiện với tướng đồng đội | Validation hồi cứu: **95/280 trường hợp** có tướng thực tế trong Top 5 (**33,9%**) | Không phải tỷ lệ thắng; phép thử biết đội hình đối thủ cuối cùng và chưa mô phỏng lượt draft live |
| Gợi ý cấm (ban) | Tần suất tướng bị cấm trong 231 ván train | Hiển thị số lần bị cấm / 231 ván cho từng gợi ý | Chưa có kết quả đánh giá độc lập V2 hay kiểm tra luật cấm chọn thực tế |

> Pick và ban là **hai tác vụ khác nhau**, không so sánh điểm cosine với tần suất ban. Hit@5 chỉ đo mức trùng với lựa chọn quan sát được trong validation, không chứng minh gợi ý tốt về chiến thuật.

*Nguồn: `src/liqily/draft/vendor/liqi_draft/models/selected_config.json` (pick) và `src/liqily/draft/vendor/liqi_draft/service.py` (cách tính điểm và phạm vi đánh giá).*

## 10:00–12:00 | Demo 3: Dự đoán sau draft

**Quy trình xây dựng mô hình:**  
`231 ván train → kiểm tra dữ liệu → học bộ mã hóa từ train → 173 đặc trưng → huấn luyện các mô hình → chọn bằng Brier trên 28 ván validation → khóa cấu hình → đánh giá một lần trên 40 ván test → lưu mô hình để phục vụ dự đoán`

> Với mỗi ván, nhóm chỉ lấy thông tin có trước khi trận bắt đầu: năm tướng của mỗi đội, phe đội A và patch. Bộ mã hóa học danh sách tướng, patch **chỉ từ train**, rồi chuyển đội hình thành các cột có/không có tướng ở từng đội; phe và patch cũng được mã hóa. Tổng cộng có **173 đặc trưng**. Nhãn đội A thắng/thua được giữ riêng, không đưa vào đầu vào.
>
> Nhóm huấn luyện Logistic Regression và Random Forest trên train, so sánh bằng Brier score trên validation, sau đó chọn **Random Forest 200 cây, độ sâu tối đa 3**. Cấu hình được khóa trước khi đánh giá test; không học lại trên validation/test. Khi chạy ứng dụng, hệ thống nạp mô hình đã lưu, mã hóa đội hình người dùng theo cùng bộ cột và trả về xác suất ước lượng đội A thắng.

> Chức năng thứ ba yêu cầu đủ năm tướng cho mỗi đội, phe của đội A và patch. Sau đó hệ thống trả về xác suất ước lượng đội A thắng và baseline chỉ theo phe để đối chiếu.
>
> Đây là phần cần diễn giải thận trọng nhất. Trên tập test 40 ván, mô hình có Brier score **0,235367**, trong khi baseline theo phe đạt **0,233249** — thấp hơn là tốt hơn. Nói cách khác, mô hình **chưa vượt baseline**.
>
> Vì vậy, xác suất hiển thị là kết quả của một thử nghiệm nghiên cứu, không phải lời khẳng định về kết quả trận đấu.

**Thao tác demo:** Nếu đã chuẩn bị sẵn đội hình, nhập đủ hai bên và hiển thị kết quả; nếu không, trình bày ảnh chụp hoặc mô tả luồng thao tác để tiết kiệm thời gian.

**Bảng so sánh mô hình và baseline** (Brier càng thấp càng tốt; test chỉ đánh giá mô hình được chọn trên validation):

| Phương pháp | Brier validation (28 ván) ↓ | Brier test (40 ván) ↓ | Accuracy test ↑ |
| --- | ---: | ---: | ---: |
| Baseline tỷ lệ thắng chung | 0,2452 | 0,233989 | 67,5% |
| Baseline theo phe | 0,2485 | **0,233249** | **67,5%** |
| Logistic Regression (`C=0,1`) | 0,2551 | Không đánh giá | — |
| Logistic Regression (`C=1`) | 0,2950 | Không đánh giá | — |
| Random Forest (độ sâu 3, **được chọn**) | **0,2441** | 0,235367 | 65,0% |
| Random Forest (độ sâu 5) | 0,2449 | Không đánh giá | — |

> Random Forest độ sâu 3 được chọn vì Brier validation thấp nhất **trong các mô hình huấn luyện**. Tuy nhiên, trên test, cả baseline tỷ lệ chung và baseline theo phe đều tốt hơn; không dùng test để chọn lại mô hình.

*Nguồn: `docs/report/khung_bao_cao.md` mục 4.2 và `docs/report/prediction_final_evaluation.md`. Khi chiếu, chỉ nhấn mạnh hai dòng Random Forest được chọn và baseline theo phe.*

## 12:00–13:30 | Giá trị và giới hạn

> Điểm nhóm muốn nhấn mạnh là Liqily đưa nhiều bước phân tích vào cùng một giao diện: từ khai phá mẫu hình, xem gợi ý cấm chọn đến thử nghiệm dự đoán. Người dùng có thể điều chỉnh tham số và xuất kết quả, thay vì chỉ nhận một kết luận cố định.
>
> Đồng thời, nhóm công khai các giới hạn: dữ liệu chỉ đến từ một giải đấu; luật kết hợp không chứng minh quan hệ nhân quả; gợi ý chưa được đánh giá trên thứ tự draft live; và mô hình dự đoán hiện chưa vượt baseline. Dữ liệu cũng cần được xác minh quyền phân phối trước khi phát hành rộng rãi.

## 13:30–14:00 | Hướng phát triển

> Hướng phát triển tiếp theo là bổ sung dữ liệu từ nhiều giải đấu và patch, đánh giá gợi ý cấm chọn theo đúng thứ tự draft thực tế, và huấn luyện, kiểm tra mô hình trên dữ liệu mới.
>
> Trọng tâm không chỉ là cải thiện điểm số, mà còn là xây dựng quy trình đánh giá đáng tin cậy hơn.

## 14:00–15:00 | Kết luận và hỏi đáp

> Tóm lại, Liqily là một ứng dụng nghiên cứu giúp khám phá dữ liệu cấm chọn Liên Quân qua ba chức năng: luật kết hợp, gợi ý pick/ban và dự đoán sau draft.
>
> Giá trị của sản phẩm không nằm ở việc hứa hẹn chiến thắng, mà ở việc giúp người dùng nhìn thấy dữ liệu, thử các giả thuyết và hiểu rõ giới hạn của kết quả.
>
> Nhóm em xin cảm ơn thầy cô và các bạn đã lắng nghe. Nhóm em sẵn sàng nhận câu hỏi.

## Nhắc khi trình bày

- Nếu demo trực tiếp, nên chuẩn bị sẵn dữ liệu và một vài đội hình mẫu.
- Tránh khẳng định “combo mạnh” hay “gợi ý tối ưu” nếu chỉ dựa vào tần suất hoặc luật kết hợp.
