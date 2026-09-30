import pandas as pd
import joblib
from underthesea import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# 1. Load dữ liệu đã làm sạch từ Phase 3
train_df = pd.read_csv('data/train.csv')
test_df = pd.read_csv('data/test.csv')

print(f"Train: {len(train_df)} mẫu | Test: {len(test_df)} mẫu")

# 2. Tách từ tiếng Việt (VD: "học sinh" -> "học_sinh")
def tokenize_vi(text: str) -> str:
    return word_tokenize(str(text), format='text')

print("Đang tách từ tiếng Việt (có thể mất chút thời gian)...")
train_df['text_tokenized'] = train_df['text'].apply(tokenize_vi)
test_df['text_tokenized'] = test_df['text'].apply(tokenize_vi)

# 3. Xây dựng TF-IDF vectorizer
vectorizer = TfidfVectorizer(
    max_features=5000,      # giới hạn số từ vựng, tránh overfit với dataset nhỏ
    ngram_range=(1, 2),     # dùng cả từ đơn và cụm 2 từ
    min_df=2,               # từ phải xuất hiện ít nhất 2 lần
)

X_train = vectorizer.fit_transform(train_df['text_tokenized'])
X_test = vectorizer.transform(test_df['text_tokenized'])

y_train = train_df['label']
y_test = test_df['label']

print(f"Số chiều đặc trưng (từ vựng): {X_train.shape[1]}")

# 4. Huấn luyện Logistic Regression
model = LogisticRegression(max_iter=1000, class_weight='balanced')
model.fit(X_train, y_train)

# 5. Đánh giá trên tập test
y_pred = model.predict(X_test)

print("\n=== KẾT QUẢ ĐÁNH GIÁ ===")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2%}")
print("\nBáo cáo chi tiết:")
print(classification_report(y_test, y_pred, target_names=['Real (0)', 'Fake (1)']))
print("Ma trận nhầm lẫn (Confusion Matrix):")
print(confusion_matrix(y_test, y_pred))

# 6. Lưu model + vectorizer để dùng ở Phase 5 (FastAPI)
joblib.dump(model, 'model.joblib')
joblib.dump(vectorizer, 'vectorizer.joblib')
print("\nĐã lưu model.joblib và vectorizer.joblib")