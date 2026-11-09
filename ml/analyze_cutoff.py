import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

d = pd.read_csv("cv_results.csv")
y = d["label"].values

# Dựng lại xác suất "giả" từ nhãn dự đoán và độ tin cậy của nhãn đó
p_fake = np.where(d["pred_phobert"] == 1, d["conf_phobert"], 1 - d["conf_phobert"])

print(f"Số mẫu: {len(d)} | tin giả: {int((y == 1).sum())} | tin thật: {int((y == 0).sum())}")
print(f"ROC-AUC của PhoBERT (dự đoán ngoài mẫu huấn luyện): {roc_auc_score(y, p_fake):.4f}\n")

print("ngưỡng P(giả) | báo nhầm tin thật (FP) | bỏ sót tin giả (FN) | accuracy | recall giả | precision giả")
for cutoff in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
    pred = (p_fake >= cutoff).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    acc = float((pred == y).mean())
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    marker = "  <- mặc định" if cutoff == 0.5 else ""
    print(
        f"{cutoff:.1f}           | {fp:22d} | {fn:19d} | {acc:7.2%} "
        f"| {recall:10.3f} | {precision:13.3f}{marker}"
    )
