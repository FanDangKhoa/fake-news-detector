"use client";
import { useState, useRef, useEffect } from "react";
type AnalysisResult = {
  text: string;
  label: "fake" | "real";
  confidence: number;
  analyzedAt: string;
};
type SpeechRecognitionType = typeof window extends {
  webkitSpeechRecognition: infer T;
}
  ? T
  : any;
export default function Home() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const recognitionRef = useRef<any>(null);
  const charCount = text.trim().length;
  const isValid = charCount >= 10;
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "vi-VN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = (event: any) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setText(transcript);
    };
    recognition.onerror = () => {
      setIsListening(false);
      setError(
        "Không nhận diện được giọng nói. Vui lòng thử lại hoặc kiểm tra quyền micro.",
      );
    };
    recognition.onend = () => {
      setIsListening(false);
    };
    recognitionRef.current = recognition;
  }, []);
  const toggleListening = () => {
    if (!recognitionRef.current) return;
    setError("");
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setText("");
      recognitionRef.current.start();
      setIsListening(true);
    }
  };
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
      speakResult(data);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Không thể kết nối đến máy chủ. Kiểm tra backend đã chạy ở port 3001 chưa.",
      );
    } finally {
      setLoading(false);
    }
  };
  const handleClear = () => {
    setText("");
    setResult(null);
    setError("");
  };
  const isFake = result?.label === "fake";
  const speakResult = (r: AnalysisResult) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const label =
      r.label === "fake" ? "Nghi ngờ là tin giả" : "Có vẻ là tin thật";
    const percent = Math.round(r.confidence * 100);
    const utterance = new SpeechSynthesisUtterance(
      `Kết quả phân tích: ${label}, với độ tin cậy ${percent} phần trăm.`,
    );
    utterance.lang = "vi-VN";
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  };
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 flex items-start justify-center px-4 py-16">
      {" "}
      <div className="w-full max-w-xl">
        {" "}
        <div className="text-center mb-8">
          {" "}
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
            {" "}
            Kiểm tra tin giả{" "}
          </h1>{" "}
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {" "}
            Dán văn bản hoặc dùng giọng nói để hệ thống phân tích độ tin
            cậy{" "}
          </p>{" "}
        </div>{" "}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-slate-200 dark:border-slate-700">
          {" "}
          <div className="relative">
            {" "}
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              placeholder="Ví dụ: 'Bạn đã trúng thưởng 25 tỷ đồng...' hoặc bấm micro để nói"
              className="w-full resize-none rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white p-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />{" "}
            {speechSupported && (
              <button
                type="button"
                onClick={toggleListening}
                title={isListening ? "Dừng ghi âm" : "Nhấn để nói"}
                className={`absolute top-3 right-3 h-8 w-8 rounded-full flex items-center justify-center transition-colors ${isListening ? "bg-red-500 text-white animate-pulse" : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-600"}`}>
                {" "}
                🎤{" "}
              </button>
            )}{" "}
          </div>{" "}
          {isListening && (
            <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
              {" "}
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />{" "}
              Đang nghe... nói rõ và bấm lại micro để dừng{" "}
            </p>
          )}{" "}
          {!speechSupported && (
            <p className="text-xs text-amber-500 mt-1">
              {" "}
              Trình duyệt này không hỗ trợ nhận diện giọng nói. Hãy dùng Chrome
              hoặc Edge.{" "}
            </p>
          )}{" "}
          <div className="flex items-center justify-between mt-2">
            {" "}
            <span
              className={`text-xs ${isValid ? "text-slate-400" : "text-amber-500"}`}>
              {" "}
              {charCount}/10 ký tự tối thiểu{" "}
            </span>{" "}
            {text.length > 0 && (
              <button
                onClick={handleClear}
                className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                {" "}
                Xóa{" "}
              </button>
            )}{" "}
          </div>{" "}
          <button
            onClick={handleAnalyze}
            disabled={loading || !isValid}
            className="mt-4 w-full rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed dark:disabled:bg-slate-700 text-white font-medium py-2.5 transition-colors flex items-center justify-center gap-2">
            {" "}
            {loading ? (
              <>
                {" "}
                <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />{" "}
                Đang phân tích...{" "}
              </>
            ) : (
              "Phân tích"
            )}{" "}
          </button>{" "}
          {error && (
            <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
              {" "}
              {error}{" "}
            </div>
          )}{" "}
          {result && (
            <div
              className={`mt-6 rounded-xl border p-4 ${isFake ? "bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800" : "bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800"}`}>
              {" "}
              <div className="flex items-center gap-2 mb-3">
                {" "}
                <span
                  className={`h-2.5 w-2.5 rounded-full ${isFake ? "bg-red-500" : "bg-emerald-500"}`}
                />{" "}
                <span
                  className={`font-semibold ${isFake ? "text-red-700 dark:text-red-300" : "text-emerald-700 dark:text-emerald-300"}`}>
                  {" "}
                  {isFake ? "Nghi ngờ tin giả" : "Có vẻ tin thật"}{" "}
                </span>{" "}
                <button
                  onClick={() => result && speakResult(result)}
                  className="ml-auto text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 flex items-center gap-1"
                  title="Nghe lại kết quả">
                  {" "}
                  🔊 Nghe lại{" "}
                </button>
              </div>{" "}
              <div className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                {" "}
                <div className="flex justify-between">
                  {" "}
                  <span>Độ tin cậy</span>{" "}
                  <span className="font-medium">
                    {" "}
                    {(result.confidence * 100).toFixed(0)}%{" "}
                  </span>{" "}
                </div>{" "}
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 mt-1">
                  {" "}
                  <div
                    className={`h-1.5 rounded-full ${isFake ? "bg-red-500" : "bg-emerald-500"}`}
                    style={{ width: `${result.confidence * 100}%` }}
                  />{" "}
                </div>{" "}
              </div>{" "}
              <p className="text-xs text-slate-400 mt-3">
                {" "}
                Phân tích lúc{" "}
                {new Date(result.analyzedAt).toLocaleString("vi-VN")}{" "}
              </p>{" "}
            </div>
          )}{" "}
        </div>{" "}
      </div>{" "}
    </main>
  );
}
