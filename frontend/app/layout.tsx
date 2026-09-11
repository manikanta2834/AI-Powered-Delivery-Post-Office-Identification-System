import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Postal Intelligence | AI-Powered Delivery Routing",
  description: "Prototype simulation for intelligent post office identification.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
