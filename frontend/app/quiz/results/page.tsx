'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuiz } from '@/contexts/QuizContext';
import { useCertification } from '@/contexts/CertificationContext';
import { Card, CardHeader, CardContent, Button, ProgressBar } from '@/components/shared';
import { api } from '@/lib/api';
import type { SessionResults, Question, TopicStat } from '@/types';

export default function QuizResultsPage() {
  const router = useRouter();
  const { selectedCertification } = useCertification();
  const { lastSessionId } = useQuiz();
  const [results, setResults] = useState<SessionResults | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [checked, setChecked] = useState(false);
  const [filter, setFilter] = useState<'all' | 'correct' | 'incorrect'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
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
      const [data, questionsData] = await Promise.all([
        api.quiz.getSessionResults(lastSessionId),
        api.quiz.getQuestions(lastSessionId),
      ]);
      setResults(data);
      setQuestions(questionsData);
    } catch (error) {
      console.error('Failed to load results:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !results) {
    return (
      <div className="max-w-4xl mx-auto text-center py-16">
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

  // Filter questions
  const filteredQuestions = questions.filter((q) => {
    if (filter === 'all') return true;
    if (!q.user_answer) return filter === 'incorrect'; // unanswered = incorrect
    const first = q.user_answer.charAt(0).toUpperCase();
    const correctFirst = q.correct_answer.charAt(0).toUpperCase();
    const isCorrect = first === correctFirst;
    return filter === 'correct' ? isCorrect : !isCorrect;
  });

  const incorrectCount = results.total_questions - results.correct_answers;

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    if (m < 60) return `${m}m ${s}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  };

  const sessionTypeLabel: Record<string, string> = {
    random: 'Random',
    full: 'Full Exam',
    weak_areas: 'Weak Areas',
    review: 'Review',
    continue: 'Continue',
    stratified: 'Stratified',
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-green-600">{results.correct_answers}</div>
            <div className="text-sm text-gray-600">Correct</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-red-600">{incorrectCount}</div>
            <div className="text-sm text-gray-600">Incorrect</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {results.duration_seconds ? formatDuration(results.duration_seconds) : '—'}
            </div>
            <div className="text-sm text-gray-600">Duration</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-bold text-purple-600">
              {results.session_type ? (sessionTypeLabel[results.session_type] || results.session_type) : '—'}
            </div>
            <div className="text-sm text-gray-600">Mode</div>
          </CardContent>
        </Card>
      </div>

      {/* Per-Topic Breakdown */}
      {results.topic_stats && results.topic_stats.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-900">Performance by Topic</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {results.topic_stats.map((ts) => (
                <div key={ts.topic}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 truncate mr-4">{ts.topic}</span>
                    <span className="text-sm text-gray-500 whitespace-nowrap">
                      {ts.correct}/{ts.total} — {ts.accuracy}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full transition-all ${
                        ts.accuracy >= 70 ? 'bg-green-500' : ts.accuracy >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${ts.accuracy}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Question Review Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Question Review</h2>
          <div className="flex space-x-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All ({questions.length})
            </button>
            <button
              onClick={() => setFilter('correct')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === 'correct'
                  ? 'bg-green-600 text-white'
                  : 'bg-green-50 text-green-700 hover:bg-green-100'
              }`}
            >
              ✓ Correct ({results.correct_answers})
            </button>
            <button
              onClick={() => setFilter('incorrect')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === 'incorrect'
                  ? 'bg-red-600 text-white'
                  : 'bg-red-50 text-red-700 hover:bg-red-100'
              }`}
            >
              ✗ Incorrect ({incorrectCount})
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {filteredQuestions.map((q, idx) => {
            const userFirst = q.user_answer?.charAt(0).toUpperCase();
            const correctFirst = q.correct_answer.charAt(0).toUpperCase();
            const isCorrect = userFirst === correctFirst;
            const isExpanded = expandedId === q.id;

            return (
              <Card
                key={q.id}
                className={`border-l-4 cursor-pointer transition-shadow hover:shadow-md ${
                  !q.user_answer
                    ? 'border-l-gray-400'
                    : isCorrect
                    ? 'border-l-green-500'
                    : 'border-l-red-500'
                }`}
              >
                <CardContent className="py-4">
                  {/* Question header - always visible */}
                  <div
                    className="flex items-start justify-between"
                    onClick={() => setExpandedId(isExpanded ? null : q.id)}
                  >
                    <div className="flex items-start space-x-3 flex-1 min-w-0">
                      <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold shrink-0 ${
                        !q.user_answer
                          ? 'bg-gray-200 text-gray-600'
                          : isCorrect
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {q.question_number}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 line-clamp-2">
                          {q.question_text}
                        </p>
                        <div className="flex items-center space-x-3 mt-1">
                          {q.user_answer ? (
                            <>
                              <span className="text-xs text-gray-500">
                                Your answer: <span className={`font-semibold ${isCorrect ? 'text-green-600' : 'text-red-600'}`}>{q.user_answer}</span>
                              </span>
                              {!isCorrect && (
                                <span className="text-xs text-gray-500">
                                  Correct: <span className="font-semibold text-green-600">{q.correct_answer}</span>
                                </span>
                              )}
                            </>
                          ) : (
                            <span className="text-xs text-gray-400 italic">Not answered</span>
                          )}
                          {q.topic && (
                            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{q.topic}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <span className="text-gray-400 ml-2 shrink-0">
                      {isExpanded ? '▲' : '▼'}
                    </span>
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
                      {/* Options */}
                      <div className="space-y-2">
                        {q.options.map((option, optIdx) => {
                          const letter = String.fromCharCode(65 + optIdx);
                          const isUserChoice = userFirst === letter;
                          const isCorrectOption = correctFirst === letter;

                          let cls = 'flex items-start space-x-2 p-2 rounded-lg text-sm ';
                          if (isCorrectOption) {
                            cls += 'bg-green-50 border border-green-200';
                          } else if (isUserChoice && !isCorrect) {
                            cls += 'bg-red-50 border border-red-200';
                          } else {
                            cls += 'bg-gray-50';
                          }

                          return (
                            <div key={letter} className={cls}>
                              <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold shrink-0 ${
                                isCorrectOption
                                  ? 'bg-green-500 text-white'
                                  : isUserChoice && !isCorrect
                                  ? 'bg-red-500 text-white'
                                  : 'bg-gray-200 text-gray-600'
                              }`}>
                                {isCorrectOption ? '✓' : isUserChoice && !isCorrect ? '✗' : letter}
                              </span>
                              <span className="flex-1">{option}</span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Images */}
                      {q.images && q.images.length > 0 && (
                        <div className="space-y-2">
                          {q.images.map((image, imgIdx) => (
                            <div key={imgIdx} className="border rounded-lg overflow-hidden bg-gray-50">
                              <img
                                src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/images/${image.image_path}`}
                                alt={`Question image ${imgIdx + 1}`}
                                className="max-w-full h-auto mx-auto"
                              />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Explanation */}
                      {q.explanation && (
                        <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                          <p className="text-sm font-semibold text-blue-800 mb-1">Explanation</p>
                          <p className="text-sm text-blue-900">{q.explanation}</p>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-center space-x-4 pb-8">
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
