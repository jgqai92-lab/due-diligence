import type { Metadata } from "next";
import "./globals.css";
import DashboardLayout from "@/components/DashboardLayout";

export const metadata: Metadata = {
  title: "The Skeptical Analyst",
  description: "Forensic Due Diligence & Portfolio Engine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="bg-nebula" />
        <div className="bg-stars" />
        <DashboardLayout>{children}</DashboardLayout>
      </body>
    </html>
  );
}
