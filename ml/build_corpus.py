import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

DATASET_ID = "tranthaihoa/vifactcheck"
EMBED_MODEL = "BAAI/bge-m3"  # đa ngữ, hỗ trợ tiếng Việt, không cần tách từ
MAX_SEQ = 256
BATCH = 32
MIN_EVIDENCE_CHARS = 30
OUT_PARQUET = "evidence_corpus.parquet"
OUT_EMB = "evidence_embeddings.npy"


def cut(x, n=250):
    return str(x).replace("\n", " ")[:n]


# 1. Tải toàn bộ các tập và gộp lại
ds = load_dataset(DATASET_ID)
df = pd.concat(
    [ds[name].to_pandas().assign(split=name) for name in ds.keys()],
    ignore_index=True,
)
print(f"Tổng số mẫu: {len(df)}")

# 2. Xem nội dung từng nhãn để xác định ý nghĩa
print("\n=== 2 MẪU CHO MỖI NHÃN ===")
for lab in sorted(df["labels"].unique()):
    for _, r in df[df["labels"] == lab].head(2).iterrows():
        print(f"\n[nhãn {lab}] Statement: {cut(r['Statement'])}")
        print(f"          Evidence : {cut(r['Evidence'])}")
        print(f"          Nguồn    : {r['Author']} | {cut(r['Url'], 90)}")

# 3. Dựng kho bằng chứng: Evidence duy nhất, đủ dài
df["Evidence"] = df["Evidence"].fillna("").astype(str).str.strip()
print(f"\nEvidence rỗng: {(df['Evidence'] == '').sum()}")
print("Độ dài Evidence trung bình (ký tự):", int(df["Evidence"].str.len().mean()))

corpus = (
    df[df["Evidence"].str.len() >= MIN_EVIDENCE_CHARS]
    .drop_duplicates(subset="Evidence")[["Evidence", "Author", "Topic", "Url"]]
    .reset_index(drop=True)
)
print(f"Số đoạn bằng chứng duy nhất trong kho: {len(corpus)}")

# 4. Mã hóa bằng mô hình embedding
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\nĐang tải mô hình embedding {EMBED_MODEL} trên {device} (lần đầu tải ~2GB)...")
model = SentenceTransformer(EMBED_MODEL, device=device)
model.max_seq_length = MAX_SEQ
if device == "cuda":
    model.half()

emb = model.encode(
    corpus["Evidence"].tolist(),
    batch_size=BATCH,
    normalize_embeddings=True,
    show_progress_bar=True,
    convert_to_numpy=True,
).astype(np.float32)

np.save(OUT_EMB, emb)
corpus.to_parquet(OUT_PARQUET, index=False)
print(f"\nĐã lưu {OUT_PARQUET} và {OUT_EMB} (kích thước {emb.shape})")

# 5. Chạy thử tìm kiếm để xem chất lượng và mức điểm thông thường
queries = [
    "Giá xăng dầu được điều chỉnh tăng",
    "Học sinh được nghỉ học vì mưa bão",
    "Tiêm vắc xin phòng bệnh cho trẻ em",
    "Bạn đã trúng thưởng 25 tỷ đồng, hãy chuyển phí nhận thưởng ngay",
    "asdkjh qwe zxc",
]
q_emb = model.encode(queries, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)

print("\n=== THỬ TÌM KIẾM (điểm cosine, càng gần 1 càng giống) ===")
for q, qv in zip(queries, q_emb):
    scores = emb @ qv
    top = np.argsort(-scores)[:3]
    print(f"\nTruy vấn: {q}")
    for i in top:
        print(f"  {scores[i]:.3f} | {corpus.loc[i, 'Author']} | {cut(corpus.loc[i, 'Evidence'], 140)}")
