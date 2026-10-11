'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

type Item = {
  id: number;
  text: string;
  label: 'fake' | 'real';
  confidence: number;
  createdAt: string;
};

type Filter = 'all' | 'fake' | 'real';

const API = 'http://localhost:3001';

const filters: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Tất cả' },
  { key: 'fake', label: 'Nghi ngờ tin giả' },
  { key: 'real', label: 'Có vẻ tin thật' },
];

export default function HistoryPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API}/analysis/history?limit=50`);
        if (!res.ok) throw new Error('Không tải được lịch sử.');
        const data: Item[] = await res.json();
        if (!cancelled) {
          setItems(data);
          setError('');
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : 'Không thể kết nối đến máy chủ. Kiểm tra backend đã chạy ở port 3001 chưa.',
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const refresh = () => {
    setLoading(true);
    setReloadKey((k) => k + 1);
  };

  const shown = filter === 'all' ? items : items.filter((i) => i.label === filter);

  return (
    <main className="px-4 py-10 md:py-14">
      <div className="mx-auto w-full max-w-2xl">
        <h1 className="mb-2 text-3xl font-semibold tracking-tight md:text-4xl">
          Lịch sử quét
        </h1>
        <p className="mb-8 text-[15px] text-[#7C8494]">
          50 lượt quét gần nhất, mới nhất nằm trên cùng.
        </p>

        <div className="mb-4 flex items-center justify-between gap-4">
          <div className="flex flex-wrap gap-2">
            {filters.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`h-8 border px-3 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B] ${
                  filter === f.key
                    ? 'border-[#C9A24B] text-[#C9A24B]'
                    : 'border-[#232A3A] text-[#7C8494] hover:text-[#EDEAE2]'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button
            onClick={refresh}
            className="text-sm text-[#7C8494] transition-colors hover:text-[#EDEAE2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B]"
          >
            Làm mới
          </button>
        </div>

        {loading && <p className="text-sm text-[#7C8494]">Đang tải...</p>}

        {error && (
          <div className="border border-[#E8576B]/40 bg-[#E8576B]/10 px-4 py-3 text-sm text-[#E8576B]">
            {error}
          </div>
        )}

        {!loading && !error && shown.length === 0 && (
          <div className="border border-[#232A3A] bg-[#12161F] p-6 text-sm text-[#7C8494]">
            Chưa có lượt quét nào ở mục này.{' '}
            <Link href="/" className="text-[#C9A24B] hover:underline">
              Quét văn bản đầu tiên
            </Link>
          </div>
        )}

        {!loading && !error && shown.length > 0 && (
          <ul className="border-t border-[#232A3A]">
            {shown.map((item) => {
              const fake = item.label === 'fake';
              const color = fake ? '#E8576B' : '#3FBE85';
              return (
                <li
                  key={item.id}
                  className="flex gap-4 border-b border-[#232A3A] py-4"
                >
                  <span
                    className="mt-2 h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 break-words text-[15px] leading-relaxed">
                      {item.text}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#7C8494]">
                      <span style={{ color }}>
                        {fake ? 'Nghi ngờ tin giả' : 'Có vẻ tin thật'}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>
                        {Math.round(item.confidence * 100)}%
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>
                        {new Date(item.createdAt).toLocaleString('vi-VN')}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </main>
  );
}
