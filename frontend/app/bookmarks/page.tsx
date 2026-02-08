'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCertification } from '@/contexts/CertificationContext';
import { useQuiz } from '@/contexts/QuizContext';
import { Card, CardHeader, CardContent, Button, LoadingSpinner } from '@/components/shared';
import type { BookmarkedQuestion } from '@/types';

export default function BookmarksPage() {
  const router = useRouter();
  const { selectedCertification, certifications } = useCertification();
  const { bookmarks, loadBookmarks, removeBookmark, loading } = useQuiz();
  const [expandedQuestion, setExpandedQuestion] = useState<string | null>(null);

  useEffect(() => {
    if (selectedCertification) {
      loadBookmarks(selectedCertification.id);
    }
  }, [selectedCertification]);

  if (!selectedCertification) {
    if (certifications.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">⭐</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">No Bookmarks</h1>
          <p className="text-gray-600 mb-6">Upload a certification and bookmark questions during quizzes</p>
          <Button onClick={() => router.push('/library')}>
            📤 Go to Library
          </Button>
        </div>
      );
    }

    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">⭐</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Select a Certification</h1>
        <p className="text-gray-600 mb-6">Choose a certification from the dashboard to view bookmarks</p>
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
          <p className="text-gray-600 mt-4">Loading bookmarks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bookmarked Questions</h1>
          <p className="text-gray-600 mt-1">{bookmarks.length} bookmarks for {selectedCertification.name}</p>
        </div>
        {bookmarks.length > 0 && (
          <Button onClick={() => router.push('/quiz')}>
            📝 Quiz from Bookmarks
          </Button>
        )}
      </div>

      {/* Bookmarks List */}
      {bookmarks.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <div className="text-6xl mb-4">⭐</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No Bookmarks Yet</h2>
            <p className="text-gray-600 mb-6">
              Bookmark questions during quizzes to review them later
            </p>
            <Button onClick={() => router.push('/quiz')}>
              Start a Quiz
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {bookmarks.map((bookmark) => (
            <Card key={bookmark.id} className="overflow-hidden">
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div 
                    className="flex-1 cursor-pointer"
                    onClick={() => setExpandedQuestion(
                      expandedQuestion === bookmark.id ? null : bookmark.id
                    )}
                  >
                    <p className="text-gray-900 font-medium line-clamp-2">
                      {bookmark.question?.question_text || 'Question text unavailable'}
                    </p>
                    {bookmark.notes && (
                      <p className="text-sm text-gray-500 mt-2 italic">
                        Note: {bookmark.notes}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => removeBookmark(bookmark.question_id)}
                    className="ml-4 p-2 text-yellow-500 hover:text-gray-400 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Remove bookmark"
                  >
                    ⭐
                  </button>
                </div>

                {/* Expanded View */}
                {expandedQuestion === bookmark.id && bookmark.question && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="space-y-2">
                      {bookmark.question.options?.map((option, index) => {
                        const letter = String.fromCharCode(65 + index);
                        const isCorrect = letter === bookmark.question?.correct_answer;
                        
                        return (
                          <div 
                            key={letter}
                            className={`p-3 rounded-lg ${
                              isCorrect 
                                ? 'bg-green-50 border border-green-200' 
                                : 'bg-gray-50'
                            }`}
                          >
                            <span className={`font-medium ${isCorrect ? 'text-green-700' : 'text-gray-700'}`}>
                              {letter}.
                            </span>{' '}
                            <span className={isCorrect ? 'text-green-900' : 'text-gray-900'}>
                              {option}
                            </span>
                            {isCorrect && (
                              <span className="ml-2 text-green-600">✓ Correct</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    
                    {bookmark.question.explanation && (
                      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                        <p className="text-sm text-blue-900">
                          <strong>Explanation:</strong> {bookmark.question.explanation}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-3 text-xs text-gray-400">
                  Bookmarked {new Date(bookmark.created_at).toLocaleDateString()}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
