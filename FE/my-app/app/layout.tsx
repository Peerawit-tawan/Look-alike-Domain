import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Look-alike Domain Dashboard",
  description: "Scan and review look-alike domains in a client-style dashboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
