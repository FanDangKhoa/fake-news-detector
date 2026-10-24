from datasets import load_dataset

DATASET_ID = "tranthaihoa/vifactcheck"
PREVIEW_CHARS = 300

ds = load_dataset(DATASET_ID)
print("Các tập:", {name: len(split) for name, split in ds.items()})

train = ds["train"].to_pandas()
print("\nCác cột:", list(train.columns))
print("\nKiểu dữ liệu:")
print(train.dtypes)

print("\n=== 2 MẪU ĐẦU TIÊN ===")
for i in range(min(2, len(train))):
    print(f"\n--- Mẫu {i} ---")
    for col in train.columns:
        value = str(train.iloc[i][col]).replace("\n", " ")
        if len(value) > PREVIEW_CHARS:
            value = value[:PREVIEW_CHARS] + "..."
        print(f"{col}: {value}")

print("\n=== PHÂN BỐ CÁC CỘT ÍT GIÁ TRỊ (nhãn, chủ đề...) ===")
for col in train.columns:
    try:
        n_unique = train[col].nunique()
    except TypeError:
        continue
    if n_unique <= 20:
        print(f"\n{col}:")
        print(train[col].value_counts())

print("\n=== ĐỘ DÀI VĂN BẢN (số ký tự, trung bình) ===")
for col in train.columns:
    if train[col].dtype == object:
        try:
            print(f"{col}: {train[col].astype(str).str.len().mean():.0f}")
        except Exception:
            pass
