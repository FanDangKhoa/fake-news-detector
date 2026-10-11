import type { Metadata } from 'next';
import { Be_Vietnam_Pro, IBM_Plex_Mono } from 'next/font/google';
import './globals.css';
import Nav from '../components/Nav';

const beVietnamPro = Be_Vietnam_Pro({
  subsets: ['vietnamese', 'latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-sans',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['vietnamese', 'latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'Xác Thực — Kiểm tra tin giả',
  description: 'Quét văn bản hoặc giọng nói để phát hiện tin giả tiếng Việt',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={`${beVietnamPro.variable} ${plexMono.variable}`}>
      <body
        className="bg-[#0B0E16] text-[#EDEAE2] antialiased"
        style={{ fontFamily: 'var(--font-sans)' }}
      >
        <Nav />
        {children}
      </body>
    </html>
  );
}
