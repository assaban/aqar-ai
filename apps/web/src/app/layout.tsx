import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Aqar.ai - AI-Powered Real Estate in Morocco",
    template: "%s | Aqar.ai",
  },
  description:
    "Find your property in Tangier and Tetouan. Automated data extraction from YouTube real estate videos.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-sand-50 text-sand-800 antialiased">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
