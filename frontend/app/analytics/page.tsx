'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useCertification } from '@/contexts/CertificationContext';
import { useAnalytics } from '@/contexts/AnalyticsContext';
import { Card, CardHeader, CardContent, Button, LoadingSpinner, ProgressBar } from '@/components/shared';

export default function AnalyticsPage() {
  const router = useRouter();
  const { selectedCertification, certifications } = useCertification();
  const { 
    overallStats, 
    weakAreas, 
    progressTrend,
    loading,
    refreshStats,
    refreshWeakAreas,
    refreshProgressTrend
  } = useAnalytics();

  useEffect(() => {
    if (selectedCertification) {
      refreshStats(selectedCertification.id);
      refreshWeakAreas(selectedCertification.id);
      refreshProgressTrend(30, selectedCertification.id);
    }
  }, [selectedCertification]);

  if (!selectedCertification) {
    if (certifications.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">📊</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">No Data Yet</h1>
          <p className="text-gray-600 mb-6">Upload a certification and complete some quizzes to see analytics</p>
          <Button onClick={() => router.push('/library')}>
            📤 Go to Library
          </Button>
        </div>
      );
    }

    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">📊</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Select a Certification</h1>
        <p className="text-gray-600 mb-6">Choose a certification from the dashboard to view analytics</p>
        <Button onClick={() => router.push('/')}>
          ← Go to Dashboard
        </Button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="text-gray-600 mt-4">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-600 mt-1">Performance insights for {selectedCertification.name}</p>
        </div>
        <Button 
          variant="secondary" 
          onClick={() => {
            refreshStats();
            refreshWeakAreas();
            refreshProgressTrend(30);
          }}
        >
          🔄 Refresh
        </Button>
      </div>

      {/* Overall Stats */}
      {overallStats && (
        <>
          {/* Main Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-gray-900">{overallStats.total_questions_answered}</div>
                <div className="text-sm text-gray-600 mt-1">Questions Answered</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-blue-600">{overallStats.questions_today}</div>
                <div className="text-sm text-gray-600 mt-1">Today</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-green-600">{overallStats.correct_answers}</div>
                <div className="text-sm text-gray-600 mt-1">Correct</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6 text-center">
                <div className="text-3xl font-bold text-primary-600">
                  {overallStats.accuracy.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600 mt-1">Accuracy</div>
              </CardContent>
            </Card>
          </div>

          {/* Exam Readiness */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Exam Readiness Score</h2>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-6">
                <div className="flex-1">
                  <ProgressBar 
                    value={overallStats.exam_readiness_score} 
                    max={100}
                    color={overallStats.exam_readiness_score >= 80 ? 'success' : overallStats.exam_readiness_score >= 60 ? 'warning' : 'error'}
                    className="h-6"
                    showLabel
                  />
                </div>
                <div className="text-right">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                    overallStats.exam_readiness_score >= 80
                      ? 'bg-green-100 text-green-800'
                      : overallStats.exam_readiness_score >= 60
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {overallStats.exam_readiness_score >= 80
                      ? '✅ Ready for exam'
                      : overallStats.exam_readiness_score >= 60
                      ? '📚 Almost there'
                      : '💪 Keep practicing'}
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-500 mt-3">
                Based on your accuracy ({overallStats.accuracy.toFixed(1)}%) and coverage 
                ({overallStats.total_questions > 0 ? ((overallStats.questions_attempted / overallStats.total_questions) * 100).toFixed(0) : 0}% of questions attempted)
              </p>
            </CardContent>
          </Card>

          {/* Study Streak */}
          <Card>
            <CardContent className="py-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <span className="text-4xl">🔥</span>
                  <div>
                    <div className="text-2xl font-bold text-orange-600">{overallStats.study_streak} days</div>
                    <div className="text-sm text-gray-600">Current study streak</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-gray-700">{overallStats.total_sessions}</div>
                  <div className="text-sm text-gray-500">Total sessions</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Weak Areas */}
      {weakAreas && weakAreas.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Weak Areas</h2>
              <Button variant="ghost" size="sm" onClick={() => router.push('/quiz')}>
                Practice These →
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {weakAreas.map((area, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">{area.topic || `Question ${area.question_id.slice(0, 8)}`}</p>
                    <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                      <span>{area.attempts} attempts</span>
                      <span>•</span>
                      <span>{area.correct} correct</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-lg font-bold ${area.accuracy < 50 ? 'text-red-600' : 'text-orange-600'}`}>
                      {area.accuracy.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Progress Trend */}
      {progressTrend && progressTrend.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold">Progress Over Time</h2>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {/* Simple chart visualization */}
              <div className="flex items-end justify-between h-full space-x-1">
                {progressTrend.slice(-14).map((point, index) => {
                  const maxQuestions = Math.max(...progressTrend.map(p => p.questions_answered));
                  const height = maxQuestions > 0 ? (point.questions_answered / maxQuestions) * 100 : 0;
                  
                  return (
                    <div key={index} className="flex-1 flex flex-col items-center">
                      <div className="flex-1 w-full flex items-end">
                        <div 
                          className="w-full bg-primary-500 rounded-t transition-all hover:bg-primary-600"
                          style={{ height: `${height}%`, minHeight: point.questions_answered > 0 ? '4px' : '0' }}
                          title={`${point.date}: ${point.questions_answered} questions, ${point.accuracy.toFixed(0)}% accuracy`}
                        />
                      </div>
                      <div className="text-xs text-gray-400 mt-2 transform -rotate-45 origin-top-left w-8">
                        {new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center justify-center space-x-6 mt-8 text-sm text-gray-600">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-primary-500 rounded mr-2"></div>
                <span>Questions Answered</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {(!overallStats || overallStats.questions_attempted === 0) && (
        <Card>
          <CardContent className="py-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No Quiz Data Yet</h2>
            <p className="text-gray-600 mb-6">Complete some quizzes to see your analytics</p>
            <Button onClick={() => router.push('/quiz')}>
              Start a Quiz
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
