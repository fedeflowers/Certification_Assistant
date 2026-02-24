'use client';

import React from 'react';
import Link from 'next/link';
import { useCertification } from '@/contexts/CertificationContext';
import { useAnalytics } from '@/contexts/AnalyticsContext';
import { Card, CardHeader, CardContent } from '@/components/shared';
import { LoadingSpinner } from '@/components/shared';

export default function DashboardPage() {
  const { certifications, selectedCertification, selectCertification } = useCertification();
  const { overallStats, loading: statsLoading, refreshStats } = useAnalytics();

  React.useEffect(() => {
    if (selectedCertification) {
      refreshStats(selectedCertification.id);
    }
  }, [selectedCertification]);

  if (certifications.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">📚</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Certification Assistant</h1>
        <p className="text-gray-600 mb-6">Get started by uploading a certification PDF</p>
        <Link
          href="/library"
          className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 transition-colors"
        >
          📤 Upload Your First PDF
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Your certification study overview</p>
      </div>

      {/* Certification Selector */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Active Certification</h2>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {certifications.map((cert) => (
              <button
                key={cert.id}
                onClick={() => selectCertification(cert.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedCertification?.id === cert.id
                    ? 'bg-primary-100 text-primary-700 border-2 border-primary-500'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-2 border-transparent'
                }`}
              >
                {cert.name}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {selectedCertification && (
        <>
          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-primary-600">
                  {statsLoading ? <LoadingSpinner size="md" /> : selectedCertification.total_questions}
                </div>
                <div className="text-sm text-gray-600 mt-1">Total Questions</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-green-600">
                  {statsLoading ? <LoadingSpinner size="md" /> : overallStats?.total_questions_answered || 0}
                </div>
                <div className="text-sm text-gray-600 mt-1">Attempted</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {statsLoading ? (
                    <LoadingSpinner size="md" />
                  ) : (
                    `${overallStats?.accuracy?.toFixed(1) || 0}%`
                  )}
                </div>
                <div className="text-sm text-gray-600 mt-1">Accuracy</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-orange-600">
                  {statsLoading ? <LoadingSpinner size="md" /> : overallStats?.study_streak || 0}
                </div>
                <div className="text-sm text-gray-600 mt-1">Day Streak 🔥</div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="hover:shadow-lg transition-shadow">
              <CardContent className="py-8">
                <Link href="/quiz" className="flex items-center space-x-4">
                  <div className="text-4xl">📝</div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Start Quiz</h3>
                    <p className="text-sm text-gray-600">Practice with questions from {selectedCertification.name}</p>
                  </div>
                </Link>
              </CardContent>
            </Card>

            <Card className="hover:shadow-lg transition-shadow">
              <CardContent className="py-8">
                <Link href="/analytics" className="flex items-center space-x-4">
                  <div className="text-4xl">📊</div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">View Progress</h3>
                    <p className="text-sm text-gray-600">See detailed analytics and weak areas</p>
                  </div>
                </Link>
              </CardContent>
            </Card>
          </div>

          {/* Exam Readiness */}
          {overallStats && (
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold">Exam Readiness</h2>
              </CardHeader>
              <CardContent>
                <div className="relative pt-1">
                  <div className="flex mb-2 items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-primary-600 bg-primary-200">
                        {overallStats.exam_readiness_score >= 80
                          ? 'Ready!'
                          : overallStats.exam_readiness_score >= 60
                          ? 'Almost There'
                          : 'Keep Practicing'}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-semibold inline-block text-primary-600">
                        {overallStats.exam_readiness_score?.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="overflow-hidden h-2 text-xs flex rounded bg-primary-200">
                    <div
                      style={{ width: `${overallStats.exam_readiness_score || 0}%` }}
                      className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-primary-500 transition-all duration-500"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
