"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Quét" },
  { href: "./history", label: "Lịch sử" },
  { href: "./dashboard", label: "Thống kê" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex justify-center gap-8 border-b border-[#232A3A] text-sm">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`-mb-px border-b-2 py-4 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#C9A24B] ${
              active
                ? "border-[#C9A24B] text-[#EDEAE2]"
                : "border-transparent text-[#7C8494] hover:text-[#EDEAE2]"
            }`}>
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
