'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuiz } from '@/contexts/QuizContext';
import { Card, CardContent, Button, LoadingSpinner, ProgressBar } from '@/components/shared';

export default function QuizSessionPage() {
  const router = useRouter();
  const {
    currentSession,
    currentQuestion,
    currentQuestionIndex,
    totalQuestions,
    answers,
    submitAnswer,
    nextQuestion,
    previousQuestion,
    endSession,
    toggleBookmark,
    loading
  } = useQuiz();

  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  useEffect(() => {
    if (!currentSession && !isEnding) {
      router.push('/quiz');
    }
  }, [currentSession, router, isEnding]);

  useEffect(() => {
    // Reset state when question changes, check if already answered
    if (currentQuestion) {
      const existing = answers.get(currentQuestion.id);
      if (existing) {
        setSelectedAnswer(existing.user_answer);
        setIsSubmitted(true);
      } else {
        setSelectedAnswer(null);
        setIsSubmitted(false);
      }
    }
  }, [currentQuestion?.id]);

  if (!currentSession || !currentQuestion) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const handleSubmit = async () => {
    if (!selectedAnswer) return;

    await submitAnswer(selectedAnswer);
    setIsSubmitted(true);

    // Auto-advance to next question or finish
    if (currentQuestionIndex < totalQuestions - 1) {
      setTimeout(() => nextQuestion(), 300);
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < totalQuestions - 1) {
      nextQuestion();
    } else {
      handleEndQuiz();
    }
  };

  const handleEndQuiz = async () => {
    setIsEnding(true);
    await endSession();
    router.push('/quiz/results');
  };

  const progress = ((currentQuestionIndex + 1) / totalQuestions) * 100;
  const answeredCount = answers.size;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Progress Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-600">
            Question {currentQuestionIndex + 1} of {totalQuestions}
          </span>
          <ProgressBar value={progress} max={100} className="w-48" />
          <span className="text-xs text-gray-400">
            {answeredCount}/{totalQuestions} answered
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => toggleBookmark(currentQuestion.id)}
          >
            {currentQuestion.is_bookmarked ? '⭐' : '☆'} Bookmark
          </Button>
          <Button variant="secondary" size="sm" onClick={handleEndQuiz}>
            End Quiz
          </Button>
        </div>
      </div>

      {/* Question Card */}
      <Card className="overflow-hidden">
        <CardContent className="p-6">
          {/* Question Text */}
          <div className="prose max-w-none mb-6">
            <h2 className="text-xl font-semibold text-gray-900 leading-relaxed">
              {currentQuestion.question_text}
            </h2>
          </div>

          {/* Question Images */}
          {currentQuestion.images && currentQuestion.images.length > 0 && (
            <div className="mb-6 space-y-4">
              {currentQuestion.images.map((image, index) => (
                <div key={index} className="border rounded-lg overflow-hidden bg-gray-50">
                  <img
                    src={`/api/images/${image.image_path}`}
                    alt={`Question image ${index + 1}`}
                    className="max-w-full h-auto mx-auto"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Answer Options */}
          <div className="space-y-3">
            {currentQuestion.options.map((option, index) => {
              const letter = String.fromCharCode(65 + index); // A, B, C, D...
              const isSelected = selectedAnswer === letter;

              let optionClasses = 'w-full p-4 rounded-lg border-2 text-left transition-all ';
              optionClasses += isSelected
                ? 'border-primary-500 bg-primary-50 text-primary-900'
                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50';

              return (
                <button
                  key={letter}
                  onClick={() => {
                    if (!isSubmitted) {
                      setSelectedAnswer(letter);
                    }
                  }}
                  disabled={isSubmitted}
                  className={optionClasses}
                >
                  <div className="flex items-start space-x-3">
                    <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                      isSelected
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-200 text-gray-700'
                    }`}>
                      {letter}
                    </span>
                    <span className="flex-1 text-base">{option}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Submitted indicator */}
          {isSubmitted && (
            <div className="mt-4 p-3 rounded-lg bg-gray-50 border border-gray-200 text-center">
              <span className="text-sm text-gray-600">
                ✓ Answer submitted — you&apos;ll see the result at the end of the quiz
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={previousQuestion}
          disabled={currentQuestionIndex === 0}
        >
          ← Previous
        </Button>

        <div className="flex space-x-3">
          {!isSubmitted ? (
            <Button
              onClick={handleSubmit}
              disabled={!selectedAnswer || loading}
              loading={loading}
            >
              Submit Answer
            </Button>
          ) : (
            <Button onClick={handleNext}>
              {currentQuestionIndex < totalQuestions - 1 ? 'Next Question →' : 'Finish Quiz'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
