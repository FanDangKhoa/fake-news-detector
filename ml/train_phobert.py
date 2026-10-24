import random

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)
from underthesea import word_tokenize

MODEL_NAME = "vinai/phobert-base-v2"
MAX_LEN = 256
BATCH_SIZE = 8
EPOCHS = 8
LR = 2e-5
SEED = 42
SAVE_DIR = "phobert_model"
TFIDF_BASELINE_ACC = 0.8889  # kết quả Phase 4, để so sánh

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
use_amp = device.type == "cuda"
print("Thiết bị:", device)
if not use_amp:
    print("Cảnh báo: không thấy GPU, huấn luyện sẽ rất chậm.")

# 1. Dữ liệu: dùng đúng train/test của Phase 3
train_df = pd.read_csv("data/train.csv")
test_df = pd.read_csv("data/test.csv")

# PhoBERT cần văn bản đã tách từ (VD: "học_sinh")
print("Đang tách từ tiếng Việt...")
for df in (train_df, test_df):
    df["seg"] = df["text"].apply(lambda t: word_tokenize(str(t), format="text"))

# Tách thêm tập validation từ train để chọn epoch, không đụng vào test
tr_df, val_df = train_test_split(
    train_df,
    test_size=0.15,
    random_state=SEED,
    stratify=train_df["label"],
)
print(f"Train: {len(tr_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


class NewsDataset(Dataset):
    def __init__(self, texts, labels):
        self.enc = tokenizer(
            list(texts),
            truncation=True,
            max_length=MAX_LEN,
            padding="max_length",
            return_tensors="pt",
        )
        self.labels = torch.tensor(list(labels), dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        return {
            "input_ids": self.enc["input_ids"][i],
            "attention_mask": self.enc["attention_mask"][i],
            "labels": self.labels[i],
        }


def make_loader(df, shuffle):
    ds = NewsDataset(df["seg"], df["label"])
    return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle)


train_loader = make_loader(tr_df, True)
val_loader = make_loader(val_df, False)
test_loader = make_loader(test_df, False)

model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
model.to(device)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
total_steps = len(train_loader) * EPOCHS
scheduler = get_linear_schedule_with_warmup(
    optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
)
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)


@torch.no_grad()
def predict(m, loader):
    m.eval()
    labels, preds, confs = [], [], []
    for b in loader:
        b = {k: v.to(device) for k, v in b.items()}
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            out = m(input_ids=b["input_ids"], attention_mask=b["attention_mask"])
        probs = torch.softmax(out.logits.float(), dim=-1)
        conf, pred = probs.max(dim=-1)
        labels.extend(b["labels"].cpu().tolist())
        preds.extend(pred.cpu().tolist())
        confs.extend(conf.cpu().tolist())
    return np.array(labels), np.array(preds), np.array(confs)


# 2. Huấn luyện, chọn epoch tốt nhất theo F1 trên validation
best_f1 = -1.0
for epoch in range(1, EPOCHS + 1):
    model.train()
    running = 0.0
    for b in train_loader:
        b = {k: v.to(device) for k, v in b.items()}
        optimizer.zero_grad()
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            loss = model(**b).loss
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        running += loss.item()

    y, p, _ = predict(model, val_loader)
    val_f1 = f1_score(y, p, average="macro")
    val_acc = accuracy_score(y, p)
    print(
        f"Epoch {epoch}/{EPOCHS} | loss {running / len(train_loader):.4f} "
        f"| val acc {val_acc:.2%} | val F1 {val_f1:.4f}"
    )
    if val_f1 > best_f1:
        best_f1 = val_f1
        model.save_pretrained(SAVE_DIR)
        tokenizer.save_pretrained(SAVE_DIR)
        print("  -> đã lưu epoch tốt nhất")

# 3. Đánh giá một lần duy nhất trên tập test bằng epoch tốt nhất
best = AutoModelForSequenceClassification.from_pretrained(SAVE_DIR).to(device)
y, p, c = predict(best, test_loader)

print("\n=== KẾT QUẢ TRÊN TẬP TEST ===")
acc = accuracy_score(y, p)
print(f"PhoBERT accuracy: {acc:.2%}   (TF-IDF Phase 4: {TFIDF_BASELINE_ACC:.2%})")
print(classification_report(y, p, target_names=["Real (0)", "Fake (1)"]))
print("Ma trận nhầm lẫn:")
print(confusion_matrix(y, p))

# 4. Độ chính xác theo ngưỡng tin cậy (dùng cho việc chọn ngưỡng "chưa kết luận")
print("\n=== THEO NGƯỠNG TIN CẬY ===")
print("ngưỡng | tỷ lệ được kết luận | độ chính xác phần được kết luận")
for t in (0.5, 0.6, 0.7, 0.8, 0.9):
    mask = c >= t
    if mask.sum() == 0:
        print(f"{t:.1f}    | 0%                 | không có mẫu")
        continue
    cov = mask.mean()
    a = accuracy_score(y[mask], p[mask])
    print(f"{t:.1f}    | {cov:6.1%}             | {a:.2%}")

print(f"\nĐã lưu model tại thư mục: {SAVE_DIR}/")
