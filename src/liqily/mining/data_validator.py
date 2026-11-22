import os
import json
import pandas as pd

from liqily.mining.config import Config

def inspect_association_train():
    file_path = Config.RAW_DATA_PATH
    
    print("=" * 70)
    print("      KIỂM TRA CẤU TRÚC DATASET (association_train.csv)")
    print("=" * 70)
    
    # 1. Kiểm tra sự tồn tại của file
    if not os.path.exists(file_path):
        print(f"❌ CHƯA THẤY FILE DỮ LIỆU TẠI: {file_path}")
        print("👉 Giải nén snapshot dữ liệu vào dataset/035ce761e53a47db/.")
        return False

    print(f"✅ Đã tìm thấy file tại: {file_path}\n")

    # 2. Đọc dữ liệu CSV
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file CSV: {e}")
        return False

    # 3. Thông tin tổng quan
    print(f"📊 Tổng số dòng (records): {df.shape[0]}")
    print(f"📊 Tổng số cột (columns): {df.shape[1]}")
    print("\n📌 Danh sách các cột:")
    for idx, col in enumerate(df.columns, 1):
        print(f"   {idx}. {col} ({df[col].dtype})")

    # 4. Kiểm tra giá trị khuyết thiếu (Missing/Null)
    print("\n⚠️ Thống kê giá trị thiếu (Null/NaN):")
    null_counts = df.isnull().sum()
    has_null = False
    for col, count in null_counts.items():
        if count > 0:
            print(f"   - Cột '{col}': thiếu {count} dòng")
            has_null = True
    if not has_null:
        print("   => Dữ liệu hoàn toàn sạch, không bị thiếu (0 missing value).")

    # 5. Hiển thị 3 dòng mẫu
    print("\n📝 3 dòng dữ liệu mẫu đầu tiên:")
    print(df.head(3).to_string())

    # 6. Kiểm tra sâu hero_ids và is_winner
    print("\n🔍 KIỂM TRA CỘT FOR MINING:")
    if 'hero_ids' in df.columns:
        first_hero_val = df['hero_ids'].iloc[0]
        print(f"   - Kiểu dữ liệu gốc 'hero_ids': {type(first_hero_val)}")
        print(f"   - Mẫu giá trị: {first_hero_val}")
        try:
            parsed_list = json.loads(first_hero_val) if isinstance(first_hero_val, str) else first_hero_val
            print(f"   - Kết quả json.loads(): {parsed_list} (Số lượng: {len(parsed_list)})")
        except Exception as parse_err:
            print(f"   ❌ Lỗi parse JSON: {parse_err}")

    if 'is_winner' in df.columns:
        print(f"   - Cột 'is_winner' kiểu: {df['is_winner'].dtype}")
        print(f"   - Phân bố Win/Lose:\n{df['is_winner'].value_counts().to_string()}")

    print("=" * 70)
    return True

if __name__ == '__main__':
    inspect_association_train()
