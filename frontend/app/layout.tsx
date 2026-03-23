import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Layout } from "@/components/ui";

export const metadata: Metadata = {
  title: "OpsMind AI - Restaurant Operations Intelligence",
  description: "AI-powered restaurant operations platform with real-time analytics and autonomous recommendations",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full scroll-smooth">
      <body className="h-full bg-slate-950 text-slate-50 overflow-hidden">
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}
