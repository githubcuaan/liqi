# Kết quả đánh giá cuối cùng — dự đoán thắng/thua

## Quy trình và policy chốt trước test

- Snapshot: `035ce761e53a47dbfd18ca1d9fabe7ceb0ec79115271bccac303bed2a6c0195c`.
- Train: 231 ván / 60 series; validation: 28 ván / 7 series; test: 40 ván / 8 series.
- Mã hóa 173 đặc trưng và fit mô hình **chỉ trên train**. Chọn mô hình từ validation bằng Brier score; không fit lại trên validation/test.
- `forest_depth_3`: 200 cây, `max_depth=3`, `min_samples_leaf=5`, `random_state=42`, `n_jobs=1`; ngưỡng phân loại `0.5`.
- `model_selection.json` đã được lưu **trước khi chạy đánh giá test**. Không áp dụng đối xứng hóa: trên validation, Brier gốc là `0.244140`, còn đối xứng hóa là `0.249859` (cao hơn là kém hơn). Sai khác đổi đội trung bình `0.122090`, lớn nhất `0.198158`; mô hình gốc không bảo đảm nhất quán xác suất khi đổi đội.
- Hai baseline (tỷ lệ thắng chung và theo phe) cũng chỉ tính từ train. Test được đánh giá một lần theo policy đã chốt; không chỉnh mô hình sau khi xem kết quả.

## Test (40 ván, đội A thắng 27 ván)

| Phương pháp | Brier ↓ | Log loss ↓ | Accuracy ↑ | Balanced accuracy ↑ |
| --- | ---: | ---: | ---: | ---: |
| `forest_depth_3` | 0.235367 | 0.663581 | 0.6500 | 0.4815 |
| Majority baseline | 0.233989 | 0.661010 | 0.6750 | 0.5000 |
| Side baseline | **0.233249** | **0.659431** | **0.6750** | **0.5000** |

**Kết luận:** Mô hình được chọn **không vượt hai baseline trên test** theo Brier hoặc log loss. Accuracy của nó cũng thấp hơn và balanced accuracy dưới 0,5. Chênh lệch Brier validation so với majority baseline vốn rất nhỏ (`0.244140` so với `0.2452`); kết quả test không chứng minh mô hình tổng quát tốt hơn. Không chọn lại mô hình hay điều chỉnh ngưỡng theo kết quả test này.

Ma trận nhầm lẫn của `forest_depth_3` (hàng = thực tế, cột = dự đoán; thứ tự `[thua, thắng]`):

|  | Dự đoán A thua | Dự đoán A thắng |
| --- | ---: | ---: |
| A thua | 0 | 13 |
| A thắng | 1 | 26 |

Mô hình gần như luôn dự đoán A thắng và không nhận diện đúng ván A thua nào trong test. Accuracy 65% vì test có nhiều ván A thắng, không phải bằng chứng phân biệt tốt hai lớp.

## Danh mục mới và giới hạn

Các nhóm sau **có thể giao nhau**; số ván rất nhỏ nên chỉ dùng để mô tả, không so sánh để chọn lại mô hình:

| Nhóm | Số ván | Brier của mô hình | Accuracy |
| --- | ---: | ---: | ---: |
| Tướng và patch đều đã thấy trong train | 33 | 0.233826 | 0.6364 |
| Có tướng chưa thấy trong train | 4 | 0.240531 | 0.7500 |
| Patch chưa thấy trong train | 6 | 0.244954 | 0.6667 |
| Có cả tướng và patch mới | 3 | 0.244483 | 0.6667 |

Chỉ có một giải đấu; 299 ván không đủ để khẳng định khả năng áp dụng cho xếp hạng hoặc patch khác. Lịch series là đại diện cho thứ tự thời gian, không phải thời điểm thi đấu thực tế đã xác minh. Tướng/patch mới có mã hóa unknown nhưng tác động của chúng không được học từ train. Các ván cùng series không hoàn toàn độc lập. Nếu cần phát triển tiếp, thu thập **dữ liệu mới và lập một đánh giá mới**; không dùng lại test này như validation để tối ưu mô hình.

## Tái lập

```bash
.venv/bin/python -m pytest tests/prediction -q
.venv/bin/python -m liqily.prediction.final_evaluation --validation
.venv/bin/python -m liqily.prediction.final_evaluation --test
```

Lệnh `--test` dùng policy tại `docs/report/model_selection.json`. Việc chạy lại chỉ để **tái lập cùng một kết quả đã khóa**, không tạo thêm một lần chọn mô hình mới. Bản ghi đánh giá ban đầu dùng Python 3.12.12, NumPy 2.5.4 và scikit-learn 1.9.1.
