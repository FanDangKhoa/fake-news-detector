import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

DATASET_ID = "tranthaihoa/vifactcheck"
SPLIT = "test"
EMBED_MODEL = "BAAI/bge-m3"
CORPUS_FILE = "evidence_corpus.parquet"
EMB_FILE = "evidence_embeddings.npy"
MAX_SEQ = 256

# 1. Nạp kho bằng chứng đã dựng ở bước trước
corpus = pd.read_parquet(CORPUS_FILE)
E = np.load(EMB_FILE)
evid_to_idx = {text: i for i, text in enumerate(corpus["Evidence"])}
print(f"Kho: {len(corpus)} đoạn bằng chứng")

# 2. Nạp các luận điểm của tập test, gắn với bằng chứng gốc trong kho
df = load_dataset(DATASET_ID)[SPLIT].to_pandas()
df["Evidence"] = df["Evidence"].fillna("").astype(str).str.strip()
df["gold"] = df["Evidence"].map(evid_to_idx)
before = len(df)
df = df.dropna(subset=["gold"]).reset_index(drop=True)
df["gold"] = df["gold"].astype(int)
print(f"Tập {SPLIT}: {len(df)}/{before} luận điểm có bằng chứng gốc trong kho")

# 3. Mã hóa luận điểm và tính độ tương đồng với toàn bộ kho
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(EMBED_MODEL, device=device)
model.max_seq_length = MAX_SEQ
if device == "cuda":
    model.half()

Q = model.encode(
    df["Statement"].astype(str).tolist(),
    batch_size=64,
    normalize_embeddings=True,
    show_progress_bar=True,
    convert_to_numpy=True,
).astype(np.float32)

S = Q @ E.T
n = len(df)
gold_scores = S[np.arange(n), df["gold"].values]
ranks = (S > gold_scores[:, None]).sum(axis=1) + 1  # hạng của bằng chứng gốc
top1 = S.max(axis=1)

# 4. Chỉ số tìm kiếm
print("\n=== CHẤT LƯỢNG TÌM KIẾM (bằng chứng gốc nằm trong top-k) ===")
for k in (1, 3, 5, 10):
    print(f"Recall@{k:<2}: {(ranks <= k).mean():.2%}")
print(f"MRR      : {(1.0 / ranks).mean():.3f}")

print("\n=== THEO TỪNG NHÃN ===")
print("nhãn | số mẫu | Recall@1 | Recall@5 | điểm top-1 trung bình")
for lab in sorted(df["labels"].unique()):
    m = (df["labels"] == lab).values
    print(
        f"{lab:<4} | {m.sum():<6} | {(ranks[m] <= 1).mean():8.2%} "
        f"| {(ranks[m] <= 5).mean():8.2%} | {top1[m].mean():.3f}"
    )

# 5. Chọn ngưỡng điểm: nếu chỉ hiển thị khi điểm top-1 >= ngưỡng
print("\n=== THEO NGƯỠNG ĐIỂM TƯƠNG ĐỒNG ===")
print("ngưỡng | tỷ lệ có kết quả | bằng chứng gốc nằm trong top-3")
hit3 = ranks <= 3
for t in np.arange(0.50, 0.86, 0.05):
    mask = top1 >= t
    if mask.sum() == 0:
        print(f"{t:.2f}   | 0.0%             | không có mẫu")
        continue
    print(f"{t:.2f}   | {mask.mean():15.1%}  | {hit3[mask].mean():.2%}")
