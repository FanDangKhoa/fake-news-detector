import random

import numpy as np
import pandas as pd
import torch
from scipy.stats import binomtest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from torch.utils.data import DataLoader, TensorDataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)
from underthesea import word_tokenize

MODEL_NAME = "vinai/phobert-base-v2"
MAX_LEN = 256
BATCH_SIZE = 8
EPOCHS = 4  # cố định cho mọi fold, không chọn epoch bằng dữ liệu test
LR = 2e-5
N_SPLITS = 5
SEED = 42

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
use_amp = device.type == "cuda"
print("Thiết bị:", device)

# 1. Gộp toàn bộ 225 mẫu (train + test của Phase 3) để đánh giá chéo
df = pd.concat(
    [pd.read_csv("data/train.csv"), pd.read_csv("data/test.csv")],
    ignore_index=True,
)
print(f"Tổng số mẫu: {len(df)} | Fake: {int((df['label'] == 1).sum())} | Real: {int((df['label'] == 0).sum())}")

print("Đang tách từ tiếng Việt...")
df["seg"] = df["text"].apply(lambda t: word_tokenize(str(t), format="text"))
y_all = df["label"].values

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


def run_tfidf(train_texts, train_labels, test_texts):
    vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2)
    X_tr = vec.fit_transform(train_texts)
    X_te = vec.transform(test_texts)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(X_tr, train_labels)
    proba = clf.predict_proba(X_te)
    return proba.argmax(axis=1), proba.max(axis=1)


def run_phobert(train_texts, train_labels, test_texts, seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    def encode(texts):
        enc = tokenizer(
            list(texts),
            truncation=True,
            max_length=MAX_LEN,
            padding="max_length",
            return_tensors="pt",
        )
        return enc["input_ids"], enc["attention_mask"]

    tr_ids, tr_mask = encode(train_texts)
    te_ids, te_mask = encode(test_texts)
    tr_y = torch.tensor(list(train_labels), dtype=torch.long)
    loader = DataLoader(
        TensorDataset(tr_ids, tr_mask, tr_y), batch_size=BATCH_SIZE, shuffle=True
    )

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    total_steps = len(loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    for _ in range(EPOCHS):
        model.train()
        for ids, mask, y in loader:
            ids, mask, y = ids.to(device), mask.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                loss = model(input_ids=ids, attention_mask=mask, labels=y).loss
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

    model.eval()
    preds, confs = [], []
    with torch.no_grad():
        for i in range(0, len(te_ids), 32):
            ids = te_ids[i : i + 32].to(device)
            mask = te_mask[i : i + 32].to(device)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                logits = model(input_ids=ids, attention_mask=mask).logits
            probs = torch.softmax(logits.float(), dim=-1)
            conf, pred = probs.max(dim=-1)
            preds.extend(pred.cpu().tolist())
            confs.extend(conf.cpu().tolist())

    del model, optimizer, scheduler, scaler
    if use_amp:
        torch.cuda.empty_cache()
    return np.array(preds), np.array(confs)


# 2. Đánh giá chéo phân tầng
skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
n = len(df)
oof_tfidf = np.zeros(n, dtype=int)
oof_phobert = np.zeros(n, dtype=int)
oof_conf_phobert = np.zeros(n)
rows = []

for fold, (tr_idx, te_idx) in enumerate(skf.split(df["seg"], y_all), start=1):
    print(f"\n===== Fold {fold}/{N_SPLITS} (train {len(tr_idx)}, test {len(te_idx)}) =====")
    tr_texts, te_texts = df["seg"].iloc[tr_idx], df["seg"].iloc[te_idx]
    y_tr, y_te = y_all[tr_idx], y_all[te_idx]

    p_tf, _ = run_tfidf(tr_texts, y_tr, te_texts)
    p_ph, c_ph = run_phobert(tr_texts, y_tr, te_texts, seed=SEED + fold)

    oof_tfidf[te_idx] = p_tf
    oof_phobert[te_idx] = p_ph
    oof_conf_phobert[te_idx] = c_ph

    rows.append(
        {
            "fold": fold,
            "tfidf_acc": accuracy_score(y_te, p_tf),
            "phobert_acc": accuracy_score(y_te, p_ph),
            "tfidf_f1": f1_score(y_te, p_tf, average="macro"),
            "phobert_f1": f1_score(y_te, p_ph, average="macro"),
        }
    )
    print(
        f"TF-IDF acc {rows[-1]['tfidf_acc']:.2%} | PhoBERT acc {rows[-1]['phobert_acc']:.2%}"
    )

# 3. Tổng hợp
res = pd.DataFrame(rows)
print("\n=== KẾT QUẢ THEO TỪNG FOLD ===")
print(res.round(4).to_string(index=False))

print("\n=== TRUNG BÌNH ± ĐỘ LỆCH CHUẨN ===")
for name, a, f in (
    ("TF-IDF + Logistic Regression", "tfidf_acc", "tfidf_f1"),
    ("PhoBERT fine-tune", "phobert_acc", "phobert_f1"),
):
    print(
        f"{name:30s} accuracy {res[a].mean():.2%} ± {res[a].std():.2%} "
        f"| macro-F1 {res[f].mean():.4f} ± {res[f].std():.4f}"
    )

print("\n=== GỘP TOÀN BỘ DỰ ĐOÁN NGOÀI MẪU HUẤN LUYỆN ===")
print(f"TF-IDF : accuracy {accuracy_score(y_all, oof_tfidf):.2%}")
print(f"PhoBERT: accuracy {accuracy_score(y_all, oof_phobert):.2%}")

# 4. Kiểm định McNemar (exact): hai mô hình có thật sự khác nhau không?
tf_ok = oof_tfidf == y_all
ph_ok = oof_phobert == y_all
b = int((tf_ok & ~ph_ok).sum())  # TF-IDF đúng, PhoBERT sai
c = int((~tf_ok & ph_ok).sum())  # TF-IDF sai, PhoBERT đúng
p_value = 1.0 if (b + c) == 0 else binomtest(min(b, c), b + c, 0.5).pvalue
print("\n=== KIỂM ĐỊNH McNEMAR ===")
print(f"TF-IDF đúng & PhoBERT sai: {b} | TF-IDF sai & PhoBERT đúng: {c}")
print(f"p-value (hai phía, chính xác): {p_value:.4f}")
print(
    "=> Khác biệt có ý nghĩa thống kê (p < 0.05)"
    if p_value < 0.05
    else "=> Chưa đủ bằng chứng thống kê để khẳng định hai mô hình khác nhau (p >= 0.05)"
)

# 5. Ngưỡng tin cậy của PhoBERT trên toàn bộ dự đoán ngoài mẫu huấn luyện
print("\n=== PhoBERT THEO NGƯỠNG TIN CẬY (225 mẫu) ===")
print("ngưỡng | tỷ lệ được kết luận | độ chính xác phần được kết luận")
for t in (0.5, 0.6, 0.7, 0.8, 0.9):
    m = oof_conf_phobert >= t
    if m.sum() == 0:
        print(f"{t:.1f}    | 0.0%                | không có mẫu")
        continue
    print(
        f"{t:.1f}    | {m.mean():18.1%}  | "
        f"{accuracy_score(y_all[m], oof_phobert[m]):.2%}"
    )

# 6. Lưu để dùng lại khi viết báo cáo
out = df[["text", "label"]].copy()
out["pred_tfidf"] = oof_tfidf
out["pred_phobert"] = oof_phobert
out["conf_phobert"] = oof_conf_phobert
out.to_csv("cv_results.csv", index=False, encoding="utf-8-sig")
res.to_csv("cv_summary.csv", index=False)
print("\nĐã lưu cv_results.csv và cv_summary.csv")
