import type { Metadata, Viewport } from "next";
import { Outfit } from "next/font/google";

import "./globals.css";
import { WorkspaceShell } from "@/components/workspace-shell";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Functional Proteomics Workbench",
  description: "Agent-native workbench over shared functional proteomics project state.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={outfit.variable}>
      <body>
        <WorkspaceShell>{children}</WorkspaceShell>
      </body>
    </html>
  );
}
