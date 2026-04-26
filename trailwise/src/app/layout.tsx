import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trailwise — Walking Trail Guide",
  description: "Find, compare, and plan the perfect walk for today. AI-powered trail discovery for Sydney and NSW.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-stone-50 text-stone-900 antialiased">
        {children}
      </body>
    </html>
  );
}
