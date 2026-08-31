import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "IP-SAKTI 360 — Innovation Intelligence",
  description: "Source-grounded IP, traditional knowledge, evidence, regulatory and ABS decision support.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
