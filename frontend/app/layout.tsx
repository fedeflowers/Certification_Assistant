import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Navigation } from '@/components/layout';
import { CertificationProvider } from '@/contexts/CertificationContext';
import { QuizProvider } from '@/contexts/QuizContext';
import { AnalyticsProvider } from '@/contexts/AnalyticsContext';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Certification Assistant',
  description: 'Study smarter for your IT certification exams',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CertificationProvider>
          <QuizProvider>
            <AnalyticsProvider>
              <div className="min-h-screen bg-gray-50">
                <Navigation />
                <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                  {children}
                </main>
              </div>
            </AnalyticsProvider>
          </QuizProvider>
        </CertificationProvider>
      </body>
    </html>
  );
}
