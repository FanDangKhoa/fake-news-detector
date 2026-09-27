import pandas as pd
import re
import unicodedata
from sklearn.model_selection import train_test_split

# 1. Load dữ liệu
df = pd.read_csv('dataset-raw/CSV/vn_news_226_tlfr.csv')
print(f"Số dòng ban đầu: {len(df)}")
print(df['label'].value_counts())

# 2. Loại bỏ dòng thiếu text hoặc label
df = df.dropna(subset=['text', 'label'])

# 3. Hàm làm sạch text
def clean_text(text: str) -> str:
    text = str(text)
    # Chuẩn hóa Unicode (quan trọng với tiếng Việt có dấu)
    text = unicodedata.normalize('NFC', text)
    # Xóa URL
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # Xóa thẻ HTML nếu có
    text = re.sub(r'<[^>]+>', '', text)
    # Xóa ký tự xuống dòng, tab thừa
    text = re.sub(r'[\r\n\t]+', ' ', text)
    # Xóa khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text

df['text'] = df['text'].apply(clean_text)

# 4. Loại bỏ text quá ngắn (rác) hoặc trùng lặp
df = df[df['text'].str.len() >= 10]
before = len(df)
df = df.drop_duplicates(subset=['text'])
print(f"Đã loại {before - len(df)} dòng trùng lặp")

# 5. Đảm bảo label đúng kiểu int
df['label'] = df['label'].astype(int)

print(f"Số dòng sau khi làm sạch: {len(df)}")
print(df['label'].value_counts())

# 6. Chia train/test (80/20), giữ tỷ lệ nhãn đều nhau (stratify)
train_df, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42,
    stratify=df['label'],
)

print(f"Train: {len(train_df)} dòng | Test: {len(test_df)} dòng")

# 7. Lưu ra file
import os
os.makedirs('data', exist_ok=True)
train_df.to_csv('data/train.csv', index=False, encoding='utf-8-sig')
test_df.to_csv('data/test.csv', index=False, encoding='utf-8-sig')
print("Đã lưu data/train.csv và data/test.csv")