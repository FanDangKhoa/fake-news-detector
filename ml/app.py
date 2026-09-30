from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import joblib
from underthesea import word_tokenize

app = FastAPI(title="Fake News Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # chỉ cho NestJS backend gọi vào
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model đã huấn luyện ở Phase 4 (load 1 lần lúc khởi động, không load lại mỗi request)
model = joblib.load("model.joblib")
vectorizer = joblib.load("vectorizer.joblib")


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10)


@app.post("/predict")
def predict(req: AnalyzeRequest):
    tokenized = word_tokenize(req.text, format="text")
    X = vectorizer.transform([tokenized])

    label_idx = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0]
    confidence = float(proba[label_idx])

    return {
        "text": req.text,
        "label": "fake" if label_idx == 1 else "real",
        "confidence": round(confidence, 2),
    }


@app.get("/health")
def health():
    return {"status": "ok"}