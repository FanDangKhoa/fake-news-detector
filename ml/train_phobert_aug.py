import os
import random

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)
from underthesea import word_tokenize

BASE_MODEL = "vinai/phobert-base-v2"
BASELINE_DIR = "phobert_model"      # mô hình cũ (Phase 7A)
NEW_DIR = "phobert_model_aug"       # mô hình sau khi bổ sung dữ liệu
MAX_LEN = 256
BATCH_SIZE = 8
EPOCHS = 6
LR = 2e-5
SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
use_amp = device.type == "cuda"
print("Thiết bị:", device)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)


def seg(texts):
    return [word_tokenize(str(t), format="text") for t in texts]


def encode(seg_texts):
    enc = tokenizer(
        list(seg_texts),
        truncation=True,
        max_length=MAX_LEN,
        padding="max_length",
        return_tensors="pt",
    )
    return enc["input_ids"], enc["attention_mask"]


@torch.no_grad()
def predict(model, seg_texts):
    model.eval()
    ids, mask = encode(seg_texts)
    preds, confs = [], []
    for i in range(0, len(ids), 32):
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            logits = model(
                input_ids=ids[i : i + 32].to(device),
                attention_mask=mask[i : i + 32].to(device),
            ).logits
        probs = torch.softmax(logits.float(), dim=-1)
        conf, pred = probs.max(dim=-1)
        preds.extend(pred.cpu().tolist())
        confs.extend(conf.cpu().tolist())
    return np.array(preds), np.array(confs)


# 1. Dữ liệu
orig_train = pd.read_csv("data/train.csv")
orig_test = pd.read_csv("data/test.csv")
synth = pd.read_csv("data_scam/train_synth.csv")
scam_eval = pd.read_csv("data_scam/scam_eval.csv")

# Tập validation chỉ lấy từ dữ liệu gốc (cùng cách chia như train_phobert.py),
# để việc chọn epoch không bị nhiễm bởi các mẫu sinh theo khuôn.
tr_orig, val_orig = train_test_split(
    orig_train, test_size=0.15, random_state=SEED, stratify=orig_train["label"]
)
train_df = pd.concat([tr_orig, synth], ignore_index=True)
print(
    f"Huấn luyện: {len(train_df)} (gốc {len(tr_orig)} + bổ sung {len(synth)}) "
    f"| Validation: {len(val_orig)} | Test gốc: {len(orig_test)} | Kiểm tra lừa đảo: {len(scam_eval)}"
)
print("Phân bố nhãn huấn luyện:", train_df["label"].value_counts().to_dict())

print("Đang tách từ tiếng Việt...")
tr_seg, val_seg = seg(train_df["text"]), seg(val_orig["text"])
test_seg, scam_seg = seg(orig_test["text"]), seg(scam_eval["text"])

# 2. Huấn luyện
ids, mask = encode(tr_seg)
y = torch.tensor(train_df["label"].tolist(), dtype=torch.long)
loader = DataLoader(TensorDataset(ids, mask, y), batch_size=BATCH_SIZE, shuffle=True)

model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL, num_labels=2).to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
total_steps = len(loader) * EPOCHS
scheduler = get_linear_schedule_with_warmup(
    optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
)
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

best_f1 = -1.0
for epoch in range(1, EPOCHS + 1):
    model.train()
    running = 0.0
    for b_ids, b_mask, b_y in loader:
        b_ids, b_mask, b_y = b_ids.to(device), b_mask.to(device), b_y.to(device)
        optimizer.zero_grad()
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            loss = model(input_ids=b_ids, attention_mask=b_mask, labels=b_y).loss
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        running += loss.item()

    p, _ = predict(model, val_seg)
    f1 = f1_score(val_orig["label"], p, average="macro")
    print(
        f"Epoch {epoch}/{EPOCHS} | loss {running / len(loader):.4f} "
        f"| val acc {accuracy_score(val_orig['label'], p):.2%} | val F1 {f1:.4f}"
    )
    if f1 >= best_f1:  # dùng >= để ưu tiên epoch muộn hơn khi bằng điểm
        best_f1 = f1
        model.save_pretrained(NEW_DIR)
        tokenizer.save_pretrained(NEW_DIR)
        print("  -> đã lưu epoch tốt nhất")

del model, optimizer, scheduler, scaler
if use_amp:
    torch.cuda.empty_cache()

# 3. So sánh trước và sau trên cùng các tập kiểm tra
probes = [
    "Bạn đã trúng thưởng 25 tỷ đồng, hãy chuyển phí nhận thưởng ngay",
    "Ngân hàng thông báo tài khoản của bạn bị khóa, vui lòng cung cấp mã OTP để mở lại",
    "Tuyển nhân viên làm việc tại nhà lương 30 triệu mỗi tháng, đóng phí hồ sơ 2 triệu",
    "Ngân hàng khuyến cáo khách hàng tuyệt đối không cung cấp mã OTP cho bất kỳ ai",
    "Giá xăng dầu được điều chỉnh tăng từ chiều nay, xăng RON 95 lên hơn 23.000 đồng/lít",
    "Hôm nay Hà Nội có mưa rào rải rác, nhiệt độ từ 24 đến 30 độ C",
]
probe_seg = seg(probes)
sets = {
    "Test gốc (45 mẫu)": (test_seg, orig_test["label"].values),
    "Kiểm tra lừa đảo": (scam_seg, scam_eval["label"].values),
}
results = {}
for name, d in (("TRƯỚC khi bổ sung", BASELINE_DIR), ("SAU khi bổ sung", NEW_DIR)):
    if not os.path.isdir(d):
        print(f"\n[{name}] bỏ qua vì không thấy thư mục {d}")
        continue
    m = AutoModelForSequenceClassification.from_pretrained(d).to(device)
    print(f"\n=== {name} ({d}) ===")
    for set_name, (texts, labels) in sets.items():
        p, c = predict(m, texts)
        print(f"[{set_name}] accuracy {accuracy_score(labels, p):.2%} | macro-F1 {f1_score(labels, p, average='macro'):.4f}")
        print(confusion_matrix(labels, p, labels=[0, 1]))
    results[name] = predict(m, probe_seg)
    del m
    if use_amp:
        torch.cuda.empty_cache()

print("\n=== CÂU THỬ (nhãn: 1 = giả/lừa đảo, 0 = thật; kèm độ tin cậy) ===")
for i, text in enumerate(probes):
    row = [f"{text[:70]}"]
    for name, (p, c) in results.items():
        row.append(f"{name.split()[0]}: {int(p[i])} ({c[i]:.0%})")
    print(" | ".join(row))

print(f"\nĐã lưu mô hình mới tại: {NEW_DIR}/")
