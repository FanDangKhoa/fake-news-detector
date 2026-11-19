import numpy as np
import pandas as pd
import torch
from scipy.special import log_softmax, softmax
from sklearn.model_selection import train_test_split
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from underthesea import word_tokenize

NEW_DIR = "phobert_model_aug"
MAX_LEN = 256
SEED = 42

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
use_amp = device.type == "cuda"
print("Thiết bị:", device)

tokenizer = AutoTokenizer.from_pretrained(NEW_DIR)
model = AutoModelForSequenceClassification.from_pretrained(NEW_DIR).to(device)
model.eval()


def seg(texts):
    return [word_tokenize(str(t), format="text") for t in texts]


@torch.no_grad()
def get_logits(seg_texts):
    enc = tokenizer(
        list(seg_texts),
        truncation=True,
        max_length=MAX_LEN,
        padding="max_length",
        return_tensors="pt",
    )
    out = []
    for i in range(0, len(enc["input_ids"]), 32):
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            lg = model(
                input_ids=enc["input_ids"][i : i + 32].to(device),
                attention_mask=enc["attention_mask"][i : i + 32].to(device),
            ).logits
        out.append(lg.float().cpu().numpy())
    return np.concatenate(out)


def fit_temperature(logits, y):
    """Tìm T làm cực tiểu NLL trên tập hiệu chỉnh (tìm theo lưới)."""
    best_t, best_nll = 1.0, float("inf")
    for t in np.arange(1.0, 20.01, 0.25):
        lp = log_softmax(logits / t, axis=1)
        nll = -lp[np.arange(len(y)), y].mean()
        if nll < best_nll:
            best_t, best_nll = float(t), float(nll)
    return best_t, best_nll


def nll_at(logits, y, t):
    lp = log_softmax(logits / t, axis=1)
    return float(-lp[np.arange(len(y)), y].mean())


# 1. Dữ liệu (cùng cách chia như các script trước)
orig_train = pd.read_csv("data/train.csv")
orig_test = pd.read_csv("data/test.csv")
scam_eval = pd.read_csv("data_scam/scam_eval.csv")
_, val_orig = train_test_split(
    orig_train, test_size=0.15, random_state=SEED, stratify=orig_train["label"]
)

# Tập hiệu chỉnh = validation gốc + tập kiểm tra lừa đảo. Tập test gốc (45) giữ lại
# để đánh giá độc lập sau hiệu chỉnh.
calib = pd.concat([val_orig[["text", "label"]], scam_eval], ignore_index=True)
print(f"Tập hiệu chỉnh: {len(calib)} mẫu | Test gốc giữ riêng: {len(orig_test)} mẫu")

L_calib = get_logits(seg(calib["text"]))
y_calib = calib["label"].values.astype(int)
T, nll_after = fit_temperature(L_calib, y_calib)
print(f"\nNhiệt độ tối ưu T = {T:.2f}  (NLL {nll_at(L_calib, y_calib, 1.0):.4f} -> {nll_after:.4f})")

# 2. Kiểm tra độc lập trên test gốc
L_test = get_logits(seg(orig_test["text"]))
y_test = orig_test["label"].values.astype(int)
for name, temp in (("Trước hiệu chỉnh (T=1)", 1.0), (f"Sau hiệu chỉnh (T={T:.2f})", T)):
    p = softmax(L_test / temp, axis=1)
    conf, pred = p.max(axis=1), p.argmax(axis=1)
    acc = (pred == y_test).mean()
    print(f"{name}: accuracy {acc:.2%} | độ tin cậy trung bình {conf.mean():.2%} | chênh lệch {conf.mean() - acc:+.2%}")

# 3. Bảng ngưỡng sau hiệu chỉnh
L_scam = get_logits(seg(scam_eval["text"]))
y_scam = scam_eval["label"].values.astype(int)
print("\n=== THEO NGƯỠNG TIN CẬY SAU HIỆU CHỈNH ===")
for set_name, L, y in (("Test gốc (45)", L_test, y_test), ("Kiểm tra lừa đảo", L_scam, y_scam)):
    p = softmax(L / T, axis=1)
    conf, pred = p.max(axis=1), p.argmax(axis=1)
    print(f"[{set_name}]  ngưỡng | được kết luận | độ chính xác phần được kết luận")
    for th in (0.6, 0.7, 0.8, 0.9, 0.95):
        m = conf >= th
        if m.sum() == 0:
            print(f"   {th:.2f}  | 0.0%          | không có mẫu")
        else:
            print(f"   {th:.2f}  | {m.mean():12.1%}  | {(pred[m] == y[m]).mean():.2%}")

# 4. Câu thử, gồm câu KHÔNG có trong dữ liệu huấn luyện
probes = [
    ("Bạn đã trúng thưởng 25 tỷ đồng, hãy chuyển phí nhận thưởng ngay", "gần khuôn huấn luyện"),
    ("Giá xăng dầu được điều chỉnh tăng từ chiều nay, xăng RON 95 lên hơn 23.000 đồng/lít", "tin thật"),
    ("Uống nước ép nghệ mỗi sáng sẽ chữa khỏi bệnh dạ dày, bác sĩ không công khai cách này", "câu C của demo"),
    ("Nhà mạng thông báo sim của bạn sẽ bị khóa, hãy soạn tin theo cú pháp để xác thực ngay", "mới"),
    ("Chính phủ vừa ban hành nghị định mới về quản lý hoạt động kinh doanh vàng miếng", "mới, tin thật"),
    ("Con mèo nhà tôi rất thích ngủ trên ghế sofa vào buổi chiều", "ngoài miền"),
]
Lp = get_logits(seg([t for t, _ in probes]))
print("\n=== CÂU THỬ (1 = giả/lừa đảo, 0 = thật) ===")
for (text, note), lg in zip(probes, Lp):
    a = softmax(lg)
    b = softmax(lg / T)
    print(f"{text[:62]:62s} | {note:22s} | chưa HC: {a.argmax()} ({a.max():.0%}) | sau HC: {b.argmax()} ({b.max():.0%})")

with open(f"{NEW_DIR}/temperature.txt", "w") as f:
    f.write(f"{T}\n")
print(f"\nĐã lưu {NEW_DIR}/temperature.txt (T = {T:.2f}). FastAPI sẽ tự dùng giá trị này.")
