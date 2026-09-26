"use client";
import { useState } from "react";
type AnalysisResult = {
  text: string;
  label: "fake" | "real";
  confidence: number;
  analyzedAt: string;
};
export default function Home() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const handleAnalyze = async () => {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const res = await fetch("http://localhost:3001/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || "Có lỗi xảy ra");
      }
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không thể kết nối backend");
    } finally {
      setLoading(false);
    }
  };
  return (
    <main
      style={{
        maxWidth: 600,
        margin: "60px auto",
        padding: 20,
        fontFamily: "sans-serif",
      }}>
      {" "}
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>
        {" "}
        Kiểm tra tin giả{" "}
      </h1>{" "}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        placeholder="Dán đoạn văn bản cần kiểm tra..."
        style={{ width: "100%", padding: 10, fontSize: 14 }}
      />{" "}
      <button
        onClick={handleAnalyze}
        disabled={loading || text.trim().length < 10}
        style={{
          marginTop: 12,
          padding: "10px 20px",
          background: "#111",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          cursor: "pointer",
        }}>
        {" "}
        {loading ? "Đang phân tích..." : "Phân tích"}{" "}
      </button>{" "}
      {error && <p style={{ color: "red", marginTop: 16 }}>{error}</p>}{" "}
      {result && (
        <div
          style={{
            marginTop: 24,
            padding: 16,
            border: "1px solid #ddd",
            borderRadius: 8,
          }}>
          {" "}
          <p>
            <strong>Kết quả:</strong>{" "}
            {result.label === "fake" ? "Nghi ngờ tin giả" : "Có vẻ tin thật"}
          </p>
          <p>
            <strong>Độ tin cậy:</strong> {(result.confidence * 100).toFixed(0)}%
          </p>{" "}
          <p style={{ fontSize: 12, color: "#888" }}>
            Phân tích lúc: {new Date(result.analyzedAt).toLocaleString("vi-VN")}
          </p>{" "}
        </div>
      )}{" "}
    </main>
  );
}
