'use client';

import { useState, useRef, useEffect } from 'react';

type Evidence = {
  text: string;
  source: string;
  topic: string;
  url: string;
  score: number;
};

type Claim = {
  text: string;
  evidence: Evidence[];
};

type AnalysisResult = {
  text: string;
  label: 'fake' | 'real';
  verdict: 'fake' | 'real' | 'uncertain';
  confidence: number;
  analyzedAt: string;
  threshold?: number;
  claims?: Claim[];
};

const VERDICT = {
  fake: {
    label: 'Nghi ngờ tin giả',
    color: '#E8576B',
  },
  real: {
    label: 'Có vẻ tin thật',
    color: '#3FBE85',
  },
  uncertain: {
    label: 'Chưa đủ căn cứ để kết luận',
    color: '#9AA3B5',
  },
} as const;

export default function Home() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const recognitionRef = useRef<any>(null);

  const charCount = text.trim().length;
  const isValid = charCount >= 10;

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setText(transcript);
    };
    recognition.onerror = () => {
      setIsListening(false);
      setError('Không nhận diện được giọng nói. Kiểm tra quyền micro.');
    };
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    setError('');
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setText('');
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const speakResult = (r: AnalysisResult) => {
    if (!('speechSynthesis' in window)) return;
    const doSpeak = () => {
      window.speechSynthesis.cancel();
      const percent = Math.round(r.confidence * 100);
      const message =
        r.verdict === 'uncertain'
          ? `Chưa đủ căn cứ để kết luận. Độ tin cậy của mô hình chỉ ${percent} phần trăm.`
          : `Kết quả phân tích: ${
              r.verdict === 'fake' ? 'Nghi ngờ là tin giả' : 'Có vẻ là tin thật'
            }, với độ tin cậy ${percent} phần trăm.`;
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.lang = 'vi-VN';
      utterance.rate = 1;
      window.speechSynthesis.speak(utterance);
    };
    if (window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.onvoiceschanged = doSpeak;
    } else {
      doSpeak();
    }
  };

  const handleAnalyze = async () => {
    setError('');
    setResult(null);
    setLoading(true);
    try {
      const res = await fetch('http://localhost:3001/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Có lỗi xảy ra');
      }
      const data = await res.json();
      setResult(data);
      speakResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không thể kết nối đến máy chủ.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setText('');
    setResult(null);
    setError('');
  };

  const verdict = result ? VERDICT[result.verdict] : null;
  const verdictColor = verdict?.color ?? '#9AA3B5';
  const hasEvidence = !!result?.claims?.some((c) => c.evidence.length > 0);

  return (
    <main className="flex min-h-screen flex-col items-center bg-[#0B0E16] px-4 py-12 text-[#EDEAE2] md:py-20">
      <div className="w-full max-w-lg">
        <div className="mb-10 flex items-center gap-2">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="8" stroke="#C9A24B" strokeWidth="1.2" />
            <circle cx="9" cy="9" r="3" fill="#C9A24B" />
          </svg>
          <span className="text-sm tracking-wide text-[#7C8494]">Xác Thực</span>
        </div>

        <h1 className="mb-3 text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl">
          Kiểm tra tin giả
        </h1>
        <p className="mb-10 max-w-sm text-[15px] leading-relaxed text-[#7C8494]">
          Dán một đoạn văn bản hoặc dùng giọng nói. Hệ thống quét và trả về mức độ
          tin cậy trong vài giây.
        </p>

        <div className="relative mb-1">
          <span className="absolute -left-px -top-px h-3 w-3 border-l border-t border-[#C9A24B]" />
          <span className="absolute -right-px -top-px h-3 w-3 border-r border-t border-[#C9A24B]" />
          <span className="absolute -bottom-px -left-px h-3 w-3 border-b border-l border-[#C9A24B]" />
          <span className="absolute -bottom-px -right-px h-3 w-3 border-b border-r border-[#C9A24B]" />

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            placeholder="Ví dụ: 'Bạn đã trúng thưởng 25 tỷ đồng, nhấn vào đây để nhận...'"
            className="w-full resize-none border border-[#232A3A] bg-[#12161F] p-4 pr-14 text-[15px] leading-relaxed text-[#EDEAE2] transition-colors placeholder:text-[#4B5364] focus:border-[#C9A24B] focus:outline-none"
          />

          {speechSupported && (
            <button
              type="button"
              onClick={toggleListening}
              title={isListening ? 'Dừng ghi âm' : 'Nhấn để nói'}
              className={`absolute right-4 top-4 flex h-8 w-8 items-center justify-center border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B] ${
                isListening
                  ? 'border-[#E8576B] text-[#E8576B]'
                  : 'border-[#232A3A] text-[#7C8494] hover:border-[#C9A24B] hover:text-[#C9A24B]'
              }`}
            >
              {isListening ? (
                <span className="h-2 w-2 animate-pulse rounded-full bg-[#E8576B]" />
              ) : (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="4.5" y="1" width="5" height="8" rx="2.5" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M2 7.5C2 10 4.2 12 7 12C9.8 12 12 10 12 7.5" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M7 12V13.3" stroke="currentColor" strokeWidth="1.2" />
                </svg>
              )}
            </button>
          )}
        </div>

        <div className="mb-6 flex items-center justify-between text-xs">
          <span
            className={isValid ? 'text-[#4B5364]' : 'text-[#C9A24B]'}
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            {charCount.toString().padStart(2, '0')} / 10
          </span>
          <div className="flex items-center gap-4">
            {isListening && (
              <span className="flex items-center gap-1.5 text-[#E8576B]">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#E8576B]" />
                đang nghe
              </span>
            )}
            {text.length > 0 && (
              <button
                onClick={handleClear}
                className="text-[#7C8494] transition-colors hover:text-[#EDEAE2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B]"
              >
                Xóa
              </button>
            )}
          </div>
        </div>

        {!speechSupported && (
          <p className="-mt-4 mb-6 text-xs text-[#C9A24B]">
            Trình duyệt này không hỗ trợ giọng nói. Dùng Chrome hoặc Edge để bật tính
            năng này.
          </p>
        )}

        <button
          onClick={handleAnalyze}
          disabled={loading || !isValid}
          className="flex h-12 w-full items-center justify-center gap-2 bg-[#C9A24B] text-[15px] font-medium text-[#0B0E16] transition-colors hover:bg-[#DBB868] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B] disabled:cursor-not-allowed disabled:bg-[#232A3A] disabled:text-[#4B5364]"
        >
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#0B0E16]/30 border-t-[#0B0E16]" />
              Đang quét
            </>
          ) : (
            'Quét văn bản'
          )}
        </button>

        {error && (
          <div className="mt-4 border border-[#E8576B]/40 bg-[#E8576B]/10 px-4 py-3 text-sm text-[#E8576B]">
            {error}
          </div>
        )}

        {result && (
          <div className="relative mt-10">
            <span className="absolute -left-px -top-px h-3 w-3 border-l border-t" style={{ borderColor: verdictColor }} />
            <span className="absolute -right-px -top-px h-3 w-3 border-r border-t" style={{ borderColor: verdictColor }} />
            <span className="absolute -bottom-px -left-px h-3 w-3 border-b border-l" style={{ borderColor: verdictColor }} />
            <span className="absolute -bottom-px -right-px h-3 w-3 border-b border-r" style={{ borderColor: verdictColor }} />

            <div className="border border-[#232A3A] bg-[#12161F] p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: verdictColor }} />
                  <span className="text-[15px] font-semibold" style={{ color: verdictColor }}>
                    {verdict?.label}
                  </span>
                </div>
                <button
                  onClick={() => result && speakResult(result)}
                  title="Nghe lại kết quả"
                  className="text-[#7C8494] transition-colors hover:text-[#EDEAE2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B]"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M2 6V10H5L9 13V3L5 6H2Z" fill="currentColor" />
                    <path d="M11.5 5.5C12.5 6.5 12.5 9.5 11.5 10.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                </button>
              </div>

              <div className="mb-1.5 flex items-center justify-between text-xs text-[#7C8494]">
                <span>Độ tin cậy</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: verdictColor }}>
                  {(result.confidence * 100).toFixed(0).padStart(2, '0')}%
                </span>
              </div>
              <div className="h-[2px] w-full bg-[#232A3A]">
                <div
                  className="h-[2px] transition-all"
                  style={{ width: `${result.confidence * 100}%`, backgroundColor: verdictColor }}
                />
              </div>

              {result.verdict === 'uncertain' && (
                <p className="mt-3 text-xs leading-relaxed text-[#7C8494]">
                  Độ tin cậy dưới {Math.round((result.threshold ?? 0.8) * 100)}%, hệ thống không đưa ra kết luận giả hay thật.
                  Hãy kiểm chứng thêm từ nguồn chính thống.
                </p>
              )}

              <div className="mt-5 border-t border-[#232A3A] pt-4">
                <h2 className="text-sm font-medium">Nguồn liên quan</h2>
                <p className="mt-1 text-xs leading-relaxed text-[#7C8494]">
                  Các đoạn dưới đây lấy từ kho báo chí đã thu thập. Chúng chỉ liên quan về
                  chủ đề, chưa phải kết luận ủng hộ hay bác bỏ luận điểm của bạn.
                </p>

                {!hasEvidence ? (
                  <p className="mt-3 text-sm text-[#7C8494]">
                    Không tìm thấy nguồn liên quan trong kho dữ liệu hiện có.
                  </p>
                ) : (
                  <div className="mt-3 space-y-4">
                    {(result.claims ?? [])
                      .filter((c) => c.evidence.length > 0)
                      .map((claim, ci) => (
                        <div key={ci}>
                          <p className="text-xs text-[#7C8494]">
                            Luận điểm:{' '}
                            <span className="text-[#EDEAE2]">{claim.text}</span>
                          </p>
                          <ul className="mt-2 space-y-3">
                            {claim.evidence.map((ev, ei) => (
                              <li key={ei} className="border-l-2 border-[#232A3A] pl-3">
                                <p className="text-[13px] leading-relaxed">{ev.text}</p>
                                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#7C8494]">
                                  <span className="text-[#C9A24B]">{ev.source}</span>
                                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                                    {Math.round(ev.score * 100)}%
                                  </span>
                                  {/^https?:\/\//.test(ev.url) && (
                                    <a
                                      href={ev.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="underline underline-offset-2 transition-colors hover:text-[#EDEAE2]"
                                    >
                                      Xem bài gốc
                                    </a>
                                  )}
                                </div>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                  </div>
                )}
              </div>

              <p className="mt-4 text-xs text-[#4B5364]" style={{ fontFamily: 'var(--font-mono)' }}>
                {new Date(result.analyzedAt).toLocaleString('vi-VN')}
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
