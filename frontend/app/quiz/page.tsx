'use client';

import React, { useState, useEffect } from 'react';
import { useCertification } from '@/contexts/CertificationContext';
import { useQuiz } from '@/contexts/QuizContext';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent, Button, LoadingSpinner } from '@/components/shared';
import { api } from '@/lib/api';
import type { QuizSuggestions, TopicsResponse, SessionType } from '@/types';

export default function QuizStartPage() {
  const router = useRouter();
  const { selectedCertification, certifications } = useCertification();
  const { startSession, loading: sessionLoading, currentSession } = useQuiz();
  
  const [suggestions, setSuggestions] = useState<QuizSuggestions | null>(null);
  const [topics, setTopics] = useState<TopicsResponse | null>(null);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  
  // Quiz mode settings
  const [quizMode, setQuizMode] = useState<'count' | 'all' | 'stratified'>('count');
  const [questionCount, setQuestionCount] = useState(10);

  useEffect(() => {
    if (selectedCertification) {
      loadSuggestions();
      loadTopics();
    }
  }, [selectedCertification]);

  useEffect(() => {
    if (currentSession) {
      router.push('/quiz/session');
    }
  }, [currentSession, router]);

  const loadSuggestions = async () => {
    if (!selectedCertification) return;
    
    setLoadingSuggestions(true);
    try {
      const data = await api.quiz.getSuggestions(selectedCertification.id);
      setSuggestions(data);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const loadTopics = async () => {
    if (!selectedCertification) return;
    
    try {
      const data = await api.quiz.getTopics(selectedCertification.id);
      setTopics(data);
    } catch (error) {
      console.error('Failed to load topics:', error);
    }
  };

  const handleStartQuiz = async (mode: SessionType) => {
    if (!selectedCertification) return;
    
    if (mode === 'full' && quizMode === 'all') {
      // All questions - no limit
      await startSession(selectedCertification.id, 'full', undefined);
    } else if (mode === 'stratified' || quizMode === 'stratified') {
      // Stratified by topic - pass questionCount to distribute across topics
      await startSession(selectedCertification.id, 'stratified', questionCount);
    } else {
      // Standard mode with count
      await startSession(selectedCertification.id, mode, questionCount);
    }
  };

  if (!selectedCertification) {
    if (certifications.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">📚</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">No Certifications Yet</h1>
          <p className="text-gray-600 mb-6">Upload a certification PDF to start practicing</p>
          <Button onClick={() => router.push('/library')}>
            📤 Go to Library
          </Button>
        </div>
      );
    }

    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">📝</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Select a Certification</h1>
        <p className="text-gray-600 mb-6">Choose a certification from the dashboard to start a quiz</p>
        <Button onClick={() => router.push('/')}>
          ← Go to Dashboard
        </Button>
      </div>
    );
  }

  const totalQuestions = selectedCertification.total_questions || topics?.total_questions || 0;
  const topicCount = topics?.topics?.length || 0;
  
  // Find topics that haven't been answered yet or have low accuracy
  const weakTopics = topics?.topics?.filter(t => t.accuracy === null || t.accuracy === undefined || t.accuracy < 70) || [];
  const unansweredTopics = topics?.topics?.filter(t => t.accuracy === null || t.accuracy === undefined) || [];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Start Quiz</h1>
        <p className="text-gray-600 mt-1">Practice for {selectedCertification.name}</p>
        <p className="text-sm text-gray-500 mt-1">
          {totalQuestions} questions • {topicCount} topics
        </p>
      </div>

      {/* Quiz Mode Selector */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Quiz Settings</h2>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Mode Selection */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-3">Quiz Mode:</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={() => setQuizMode('count')}
                className={`p-4 rounded-lg text-left transition-all ${
                  quizMode === 'count'
                    ? 'bg-primary-50 border-2 border-primary-500 ring-2 ring-primary-200'
                    : 'bg-gray-50 border-2 border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-gray-900">📊 Random</div>
                <div className="text-sm text-gray-600 mt-1">Random questions selection</div>
              </button>
              
              <button
                onClick={() => setQuizMode('stratified')}
                className={`p-4 rounded-lg text-left transition-all ${
                  quizMode === 'stratified'
                    ? 'bg-primary-50 border-2 border-primary-500 ring-2 ring-primary-200'
                    : 'bg-gray-50 border-2 border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-gray-900">🎯 Stratified</div>
                <div className="text-sm text-gray-600 mt-1">
                  Distributed by topic
                  {unansweredTopics.length > 0 && (
                    <span className="block text-orange-600 text-xs mt-1">
                      {unansweredTopics.length} topics not yet studied
                    </span>
                  )}
                </div>
              </button>
              
              <button
                onClick={() => setQuizMode('all')}
                className={`p-4 rounded-lg text-left transition-all ${
                  quizMode === 'all'
                    ? 'bg-primary-50 border-2 border-primary-500 ring-2 ring-primary-200'
                    : 'bg-gray-50 border-2 border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-gray-900">📋 All Questions</div>
                <div className="text-sm text-gray-600 mt-1">{totalQuestions} questions</div>
              </button>
            </div>
          </div>

          {/* Question Count - shown for count and stratified modes */}
          {(quizMode === 'count' || quizMode === 'stratified') && (
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-3">
                Number of Questions:
                {quizMode === 'stratified' && (
                  <span className="font-normal text-gray-500 ml-2">
                    (distributed across {topicCount} topics, prioritizing weak areas)
                  </span>
                )}
              </label>
              <div className="flex flex-wrap gap-2">
                {[5, 10, 20, 50, 100].map((count) => (
                  <button
                    key={count}
                    onClick={() => setQuestionCount(count)}
                    disabled={count > totalQuestions}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      questionCount === count
                        ? 'bg-primary-100 text-primary-700 border-2 border-primary-500'
                        : count > totalQuestions
                          ? 'bg-gray-100 text-gray-400 border-2 border-transparent cursor-not-allowed'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-2 border-transparent'
                    }`}
                  >
                    {count}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Topics Preview - shown for stratified mode */}
          {quizMode === 'stratified' && topics && topics.topics.length > 0 && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-700 mb-3">
                Topic Distribution Preview:
              </div>
              <div className="flex flex-wrap gap-2">
                {topics.topics
                  .sort((a, b) => {
                    // Sort: unanswered first, then by accuracy ascending
                    const aScore = a.accuracy === null || a.accuracy === undefined ? -1 : a.accuracy;
                    const bScore = b.accuracy === null || b.accuracy === undefined ? -1 : b.accuracy;
                    return aScore - bScore;
                  })
                  .slice(0, 12)
                  .map((topic, idx) => (
                    <span 
                      key={idx}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                        topic.accuracy === null || topic.accuracy === undefined
                          ? 'bg-orange-100 text-orange-700 border border-orange-300'
                          : topic.accuracy >= 70 
                            ? 'bg-green-100 text-green-700'
                            : topic.accuracy >= 50 
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {topic.topic} ({topic.question_count})
                      {topic.accuracy !== null && topic.accuracy !== undefined ? (
                        <span className="ml-1">• {topic.accuracy}%</span>
                      ) : (
                        <span className="ml-1">• NEW</span>
                      )}
                    </span>
                  ))}
                {topics.topics.length > 12 && (
                  <span className="px-3 py-1.5 text-xs text-gray-500">
                    +{topics.topics.length - 12} more topics
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-3">
                ⚡ Questions will be distributed proportionally, prioritizing topics marked as NEW or with lower accuracy
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Start Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Start Quiz Button - Primary */}
        <Card 
          className="md:col-span-2 hover:shadow-lg transition-shadow cursor-pointer bg-primary-50 border-2 border-primary-200" 
          onClick={() => {
            if (quizMode === 'all') {
              handleStartQuiz('full');
            } else if (quizMode === 'stratified') {
              handleStartQuiz('stratified');
            } else {
              handleStartQuiz('random');
            }
          }}
        >
          <CardContent className="py-6">
            <div className="flex items-center justify-center space-x-4">
              <div className="text-4xl">🚀</div>
              <div className="text-center">
                <h3 className="text-xl font-bold text-primary-800">Start Quiz</h3>
                <p className="text-sm text-primary-600 mt-1">
                  {quizMode === 'all' && `All ${totalQuestions} questions`}
                  {quizMode === 'count' && `${questionCount} random questions`}
                  {quizMode === 'stratified' && `${questionCount} questions distributed by topic`}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weak Areas */}
        {suggestions?.weak_areas && suggestions.weak_areas.question_count > 0 && (
          <Card 
            className="hover:shadow-lg transition-shadow cursor-pointer border-2 border-orange-200" 
            onClick={() => handleStartQuiz('weak_areas')}
          >
            <CardContent className="py-6">
              <div className="flex items-start space-x-4">
                <div className="text-3xl">🎯</div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">Focus on Weak Areas</h3>
                  <p className="text-sm text-gray-600 mt-1">{suggestions.weak_areas.description}</p>
                  <span className="inline-block mt-2 px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-full">
                    {suggestions.weak_areas.question_count} questions
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Review Mistakes */}
        {suggestions?.review_incorrect && suggestions.review_incorrect.question_count > 0 && (
          <Card 
            className="hover:shadow-lg transition-shadow cursor-pointer border-2 border-red-200" 
            onClick={() => handleStartQuiz('review')}
          >
            <CardContent className="py-6">
              <div className="flex items-start space-x-4">
                <div className="text-3xl">🔄</div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">Review Mistakes</h3>
                  <p className="text-sm text-gray-600 mt-1">{suggestions.review_incorrect.description}</p>
                  <span className="inline-block mt-2 px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">
                    {suggestions.review_incorrect.question_count} to review
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Continue Where Left Off */}
        {suggestions?.continue_session && suggestions.continue_session.question_count > 0 && (
          <Card 
            className="hover:shadow-lg transition-shadow cursor-pointer border-2 border-blue-200" 
            onClick={() => handleStartQuiz('continue')}
          >
            <CardContent className="py-6">
              <div className="flex items-start space-x-4">
                <div className="text-3xl">▶️</div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">Continue Studying</h3>
                  <p className="text-sm text-gray-600 mt-1">{suggestions.continue_session.description}</p>
                  <span className="inline-block mt-2 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                    {suggestions.continue_session.question_count} unseen
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {sessionLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card>
            <CardContent className="py-8 px-12 text-center">
              <LoadingSpinner size="lg" />
              <p className="text-gray-700 mt-4">Starting your quiz...</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
