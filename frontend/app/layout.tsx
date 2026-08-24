import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Insurance Decision Platform",
  description: "Invite-only beta. Foundation build.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
