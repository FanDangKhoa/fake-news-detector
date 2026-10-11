'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

type Stats = {
  total: number;
  fake: number;
  real: number;
  daily: { date: string; total: number; fake: number }[];
};

const API = 'http://localhost:3001';
const GOLD = '#C9A24B';
const RED = '#E8576B';
const GREEN = '#3FBE85';
const mono = { fontFamily: 'var(--font-mono)' };
const BAR_MAX_PX = 96;

function lastSevenDays(): string[] {
  const days: string[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toLocaleDateString('en-CA'));
  }
  return days;
}

function Reticle({ color }: { color: string }) {
  return (
    <>
      <span className="absolute -left-px -top-px h-3 w-3 border-l border-t" style={{ borderColor: color }} />
      <span className="absolute -right-px -top-px h-3 w-3 border-r border-t" style={{ borderColor: color }} />
      <span className="absolute -bottom-px -left-px h-3 w-3 border-b border-l" style={{ borderColor: color }} />
      <span className="absolute -bottom-px -right-px h-3 w-3 border-b border-r" style={{ borderColor: color }} />
    </>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API}/analysis/stats`);
        if (!res.ok) throw new Error('Không tải được thống kê.');
        const data: Stats = await res.json();
        if (!cancelled) setStats(data);
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
  }, []);

  const fakePercent =
    stats && stats.total > 0 ? Math.round((stats.fake / stats.total) * 100) : 0;

  const series = (() => {
    if (!stats) return [];
    const byDate = new Map(stats.daily.map((d) => [d.date, d]));
    return lastSevenDays().map((date) => {
      const d = byDate.get(date);
      return { date, total: d?.total ?? 0, fake: d?.fake ?? 0 };
    });
  })();
  const maxDay = Math.max(1, ...series.map((s) => s.total));

  return (
    <main className="px-4 py-10 md:py-14">
      <div className="mx-auto w-full max-w-2xl">
        <h1 className="mb-2 text-3xl font-semibold tracking-tight md:text-4xl">
          Thống kê
        </h1>
        <p className="mb-8 text-[15px] text-[#7C8494]">
          Tổng hợp từ tất cả lượt quét đã lưu.
        </p>

        {loading && <p className="text-sm text-[#7C8494]">Đang tải...</p>}

        {error && (
          <div className="border border-[#E8576B]/40 bg-[#E8576B]/10 px-4 py-3 text-sm text-[#E8576B]">
            {error}
          </div>
        )}

        {stats && stats.total === 0 && (
          <div className="border border-[#232A3A] bg-[#12161F] p-6 text-sm text-[#7C8494]">
            Chưa có dữ liệu để thống kê.{' '}
            <Link href="/" className="text-[#C9A24B] hover:underline">
              Quét văn bản đầu tiên
            </Link>
          </div>
        )}

        {stats && stats.total > 0 && (
          <div className="space-y-10">
            <div className="relative">
              <Reticle color={GOLD} />
              <div className="grid grid-cols-3 border border-[#232A3A] bg-[#12161F]">
                <div className="p-5">
                  <p className="text-xs text-[#7C8494]">Tổng lượt quét</p>
                  <p className="mt-2 text-4xl" style={{ ...mono, color: GOLD }}>
                    {stats.total}
                  </p>
                </div>
                <div className="border-l border-[#232A3A] p-5">
                  <p className="text-xs text-[#7C8494]">Nghi ngờ tin giả</p>
                  <p className="mt-2 text-4xl" style={{ ...mono, color: RED }}>
                    {stats.fake}
                  </p>
                </div>
                <div className="border-l border-[#232A3A] p-5">
                  <p className="text-xs text-[#7C8494]">Có vẻ tin thật</p>
                  <p className="mt-2 text-4xl" style={{ ...mono, color: GREEN }}>
                    {stats.real}
                  </p>
                </div>
              </div>
            </div>

            <section>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-[#7C8494]">Tỷ lệ tin giả</span>
                <span style={{ ...mono, color: RED }}>{fakePercent}%</span>
              </div>
              <div className="flex h-2 w-full bg-[#232A3A]">
                <div style={{ width: `${fakePercent}%`, backgroundColor: RED }} />
                <div style={{ width: `${100 - fakePercent}%`, backgroundColor: GREEN }} />
              </div>
            </section>

            <section>
              <h2 className="mb-4 text-sm text-[#7C8494]">7 ngày gần nhất</h2>
              <div className="flex h-[132px] items-end gap-3 border-b border-[#232A3A]">
                {series.map((s) => {
                  const barPx = Math.round((s.total / maxDay) * BAR_MAX_PX);
                  const fakePx = s.total ? Math.round((barPx * s.fake) / s.total) : 0;
                  const realPx = barPx - fakePx;
                  return (
                    <div
                      key={s.date}
                      className="flex h-full flex-1 flex-col items-center justify-end"
                    >
                      <span className="mb-1 text-xs text-[#7C8494]" style={mono}>
                        {s.total}
                      </span>
                      <div className="flex w-full max-w-[40px] flex-col">
                        <div style={{ height: fakePx, backgroundColor: RED }} />
                        <div style={{ height: realPx, backgroundColor: GREEN }} />
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="mt-2 flex gap-3">
                {series.map((s) => (
                  <span
                    key={s.date}
                    className="flex-1 text-center text-xs text-[#4B5364]"
                    style={mono}
                  >
                    {s.date.slice(8, 10)}/{s.date.slice(5, 7)}
                  </span>
                ))}
              </div>
              <div className="mt-4 flex gap-5 text-xs text-[#7C8494]">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2" style={{ backgroundColor: RED }} />
                  Nghi ngờ tin giả
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2" style={{ backgroundColor: GREEN }} />
                  Có vẻ tin thật
                </span>
              </div>
            </section>
          </div>
        )}
      </div>
    </main>
  );
}
