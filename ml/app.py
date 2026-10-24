import os

import joblib
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from underthesea import word_tokenize

from claims import extract_claims

PHOBERT_DIR = "phobert_model"
MAX_LEN = 256

# Cấu hình tìm bằng chứng
CORPUS_FILE = "evidence_corpus.parquet"
EMB_FILE = "evidence_embeddings.npy"
EMBED_MODEL = "BAAI/bge-m3"
EVIDENCE_MIN_SCORE = 0.65  # dưới ngưỡng này coi là không liên quan
EVIDENCE_TOP_K = 3
MAX_CLAIMS = 3

app = FastAPI(title="Fake News Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # chỉ cho NestJS backend gọi vào
    allow_methods=["*"],
    allow_headers=["*"],
)

use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")

# ---------- Bộ phân loại giả/thật ----------
use_phobert = os.path.isdir(PHOBERT_DIR)
if use_phobert:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    MODEL_NAME = "phobert"
    tokenizer = AutoTokenizer.from_pretrained(PHOBERT_DIR)
    phobert = AutoModelForSequenceClassification.from_pretrained(PHOBERT_DIR).to(device)
    phobert.eval()
else:
    MODEL_NAME = "tfidf"
    tfidf_model = joblib.load("model.joblib")
    vectorizer = joblib.load("vectorizer.joblib")

# ---------- Kho bằng chứng (tìm kiếm ngữ nghĩa) ----------
evidence_ready = os.path.exists(CORPUS_FILE) and os.path.exists(EMB_FILE)
if evidence_ready:
    from sentence_transformers import SentenceTransformer

    corpus_records = pd.read_parquet(CORPUS_FILE).to_dict("records")
    E = torch.from_numpy(np.load(EMB_FILE)).to(device)
    embedder = SentenceTransformer(EMBED_MODEL, device=str(device))
    embedder.max_seq_length = 256
    if use_cuda:
        embedder.half()
        E = E.half()

print(
    f"Phân loại: {MODEL_NAME} | Tìm bằng chứng: "
    f"{'bật (' + str(len(corpus_records)) + ' đoạn)' if evidence_ready else 'tắt'} | Thiết bị: {device}"
)


def _text(value) -> str:
    return "" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value)


def find_evidence(claims: list[str]) -> list[dict]:
    if not claims:
        return []
    if not evidence_ready:
        return [{"text": c, "evidence": []} for c in claims]

    q = embedder.encode(claims, convert_to_tensor=True, normalize_embeddings=True).to(E.dtype)
    scores = (q @ E.T).float()
    k = min(EVIDENCE_TOP_K, scores.shape[1])
    top_scores, top_idx = torch.topk(scores, k=k, dim=1)

    results: list[dict] = []
    seen: set[str] = set()  # tránh lặp lại cùng một đoạn giữa các luận điểm
    for claim, ss, ii in zip(claims, top_scores.tolist(), top_idx.tolist()):
        items = []
        for score, idx in zip(ss, ii):
            if score < EVIDENCE_MIN_SCORE:
                continue
            rec = corpus_records[idx]
            evidence_text = _text(rec.get("Evidence"))
            if evidence_text in seen:
                continue
            seen.add(evidence_text)
            items.append(
                {
                    "text": evidence_text,
                    "source": _text(rec.get("Author")),
                    "topic": _text(rec.get("Topic")),
                    "url": _text(rec.get("Url")),
                    "score": round(float(score), 2),
                }
            )
        results.append({"text": claim, "evidence": items})
    return results


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10)


@app.post("/predict")
def predict(req: AnalyzeRequest):
    tokenized = word_tokenize(req.text, format="text")

    if use_phobert:
        enc = tokenizer(
            tokenized,
            truncation=True,
            max_length=MAX_LEN,
            return_tensors="pt",
        ).to(device)
        with torch.inference_mode():
            logits = phobert(**enc).logits
        probs = torch.softmax(logits.float(), dim=-1)[0]
        label_idx = int(probs.argmax())
        confidence = float(probs[label_idx])
    else:
        X = vectorizer.transform([tokenized])
        label_idx = int(tfidf_model.predict(X)[0])
        confidence = float(tfidf_model.predict_proba(X)[0][label_idx])

    claims = extract_claims(req.text, max_claims=MAX_CLAIMS)

    return {
        "text": req.text,
        "label": "fake" if label_idx == 1 else "real",
        "confidence": round(confidence, 2),
        "model": MODEL_NAME,
        "claims": find_evidence(claims),
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "evidence": evidence_ready}
