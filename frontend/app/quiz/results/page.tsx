'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuiz } from '@/contexts/QuizContext';
import { useCertification } from '@/contexts/CertificationContext';
import { Card, CardHeader, CardContent, Button, ProgressBar } from '@/components/shared';
import { api } from '@/lib/api';
import type { SessionResults } from '@/types';

export default function QuizResultsPage() {
  const router = useRouter();
  const { selectedCertification } = useCertification();
  const { lastSessionId } = useQuiz();
  const [results, setResults] = useState<SessionResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    // Wait a tick to ensure lastSessionId is set from context
    const timer = setTimeout(() => {
      setChecked(true);
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!checked) return;
    
    if (lastSessionId) {
      loadResults();
    } else {
      router.push('/quiz');
    }
  }, [lastSessionId, checked]);

  const loadResults = async () => {
    if (!lastSessionId) return;
    
    try {
      const data = await api.quiz.getSessionResults(lastSessionId);
      setResults(data);
    } catch (error) {
      console.error('Failed to load results:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !results) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mx-auto mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-64 mx-auto"></div>
        </div>
      </div>
    );
  }

  const accuracy = results.total_questions > 0 
    ? (results.correct_answers / results.total_questions) * 100 
    : 0;

  const getPerformanceMessage = () => {
    if (accuracy >= 90) return { emoji: '🏆', message: 'Outstanding!', color: 'text-green-600' };
    if (accuracy >= 80) return { emoji: '🌟', message: 'Great job!', color: 'text-green-600' };
    if (accuracy >= 70) return { emoji: '👍', message: 'Good work!', color: 'text-blue-600' };
    if (accuracy >= 60) return { emoji: '📚', message: 'Keep practicing!', color: 'text-yellow-600' };
    return { emoji: '💪', message: 'Don\'t give up!', color: 'text-orange-600' };
  };

  const performance = getPerformanceMessage();

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="text-6xl mb-4">{performance.emoji}</div>
        <h1 className={`text-3xl font-bold ${performance.color}`}>{performance.message}</h1>
        <p className="text-gray-600 mt-2">Quiz completed for {selectedCertification?.name}</p>
      </div>

      {/* Score Card */}
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <div className="text-5xl font-bold text-gray-900 mb-2">
              {accuracy.toFixed(0)}%
            </div>
            <p className="text-gray-600">
              {results.correct_answers} out of {results.total_questions} correct
            </p>
            <ProgressBar 
              value={accuracy} 
              max={100} 
              color={accuracy >= 70 ? 'success' : accuracy >= 50 ? 'warning' : 'error'}
              className="mt-4 h-4"
              showLabel
            />
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-green-600">{results.correct_answers}</div>
            <div className="text-sm text-gray-600">Correct</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-red-600">{results.incorrect_answers}</div>
            <div className="text-sm text-gray-600">Incorrect</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-gray-600">{results.skipped_answers}</div>
            <div className="text-sm text-gray-600">Skipped</div>
          </CardContent>
        </Card>
      </div>

      {/* Time Stats */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Session Details</h2>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Duration:</span>
              <span className="ml-2 font-medium">{formatDuration(results.duration_seconds)}</span>
            </div>
            <div>
              <span className="text-gray-500">Avg. per question:</span>
              <span className="ml-2 font-medium">
                {results.total_questions > 0 
                  ? formatDuration(Math.round(results.duration_seconds / results.total_questions))
                  : 'N/A'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-center space-x-4">
        <Button variant="secondary" onClick={() => router.push('/analytics')}>
          📊 View Analytics
        </Button>
        <Button onClick={() => router.push('/quiz')}>
          📝 Start New Quiz
        </Button>
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
