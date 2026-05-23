import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SteelOptimizerJm',
  description: 'GA-based steel section optimizer (AISC 360 / EC3 / NSR-10)',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  )
}
