import type { Metadata, Viewport } from "next";
import { Outfit } from "next/font/google";

import "./globals.css";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getDemoWorkspace } from "@/lib/demo-workspace";

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
  const workspace = getDemoWorkspace();

  return (
    <html lang="en" className={outfit.variable}>
      <body>
        <WorkspaceShell
          sharedStateLabel={`${workspace.project.id} loaded`}
          statusLabel={`${workspace.dataset.validation.status} dataset · ${workspace.trace_export.count} traces`}
        >
          {children}
        </WorkspaceShell>
      </body>
    </html>
  );
}
