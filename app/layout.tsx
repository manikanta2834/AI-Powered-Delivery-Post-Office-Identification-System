import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Postal Intelligence | AI-Powered Delivery Post Office Identification System",
  description: "AI-Powered Delivery Post Office Identification System & Postal Logistics Platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
