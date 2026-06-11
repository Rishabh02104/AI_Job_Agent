import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Job Agent — Autonomous Career Search Portfolio",
  description: "Finds jobs, scores relevance, tailors resumes and cover letters, and tracks applications autonomously.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-100 dark">
      <body className={`${inter.className} min-h-full flex`}>
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Workspace content */}
        <div className="flex-1 pl-64 min-h-screen flex flex-col bg-slate-950">
          <main className="flex-1 p-8 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
