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
    submitAnswer,
    nextQuestion,
    previousQuestion,
    endSession,
    toggleBookmark,
    loading
  } = useQuiz();

  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [explanation, setExplanation] = useState<string>('');

  useEffect(() => {
    if (!currentSession) {
      router.push('/quiz');
    }
  }, [currentSession, router]);

  useEffect(() => {
    // Reset state when question changes
    setSelectedAnswer(null);
    setShowFeedback(false);
    setIsCorrect(null);
    setExplanation('');
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

    const result = await submitAnswer(selectedAnswer);
    if (result) {
      setIsCorrect(result.is_correct);
      setExplanation(result.explanation || '');
      setShowFeedback(true);
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < totalQuestions - 1) {
      nextQuestion();
    } else {
      // End of quiz
      handleEndQuiz();
    }
  };

  const handleEndQuiz = async () => {
    await endSession();
    router.push('/quiz/results');
  };

  const progress = ((currentQuestionIndex + 1) / totalQuestions) * 100;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Progress Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-600">
            Question {currentQuestionIndex + 1} of {totalQuestions}
          </span>
          <ProgressBar value={progress} max={100} className="w-48" />
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
              const isCorrectAnswer = showFeedback && letter === currentQuestion.correct_answer;
              const isWrongSelection = showFeedback && isSelected && !isCorrect;

              let optionClasses = 'w-full p-4 rounded-lg border-2 text-left transition-all ';
              
              if (showFeedback) {
                if (isCorrectAnswer) {
                  optionClasses += 'border-green-500 bg-green-50 text-green-900';
                } else if (isWrongSelection) {
                  optionClasses += 'border-red-500 bg-red-50 text-red-900';
                } else {
                  optionClasses += 'border-gray-200 bg-gray-50 text-gray-600';
                }
              } else {
                optionClasses += isSelected
                  ? 'border-primary-500 bg-primary-50 text-primary-900'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50';
              }

              return (
                <button
                  key={letter}
                  onClick={() => !showFeedback && setSelectedAnswer(letter)}
                  disabled={showFeedback}
                  className={optionClasses}
                >
                  <div className="flex items-start space-x-3">
                    <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                      isSelected && !showFeedback
                        ? 'bg-primary-500 text-white'
                        : isCorrectAnswer
                        ? 'bg-green-500 text-white'
                        : isWrongSelection
                        ? 'bg-red-500 text-white'
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

          {/* Feedback Section */}
          {showFeedback && (
            <div className={`mt-6 p-4 rounded-lg ${isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-2xl">{isCorrect ? '✅' : '❌'}</span>
                <span className={`font-semibold ${isCorrect ? 'text-green-700' : 'text-red-700'}`}>
                  {isCorrect ? 'Correct!' : 'Incorrect'}
                </span>
              </div>
              {explanation && (
                <p className="text-gray-700 mt-2">{explanation}</p>
              )}
              {!isCorrect && (
                <p className="text-gray-600 mt-2">
                  The correct answer is: <strong>{currentQuestion.correct_answer}</strong>
                </p>
              )}
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
          {!showFeedback ? (
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
