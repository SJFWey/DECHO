import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DECHO",
  description: "AI-powered audio processing",
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
  },
};

import { ApiProvider } from "@/components/providers/api-provider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col bg-background text-foreground`}
      >
        <ApiProvider>
          <main className="flex-1 flex flex-col items-center w-full relative pt-16">
              {children}
          </main>
          <Toaster />
        </ApiProvider>
      </body>
    </html>
  );
}
