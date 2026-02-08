'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from '@/lib/api';
import type { QuizSession, Question, AnswerResponse, SessionResults, QuizSuggestion, SessionType } from '@/types';

interface QuizContextType {
  currentSession: QuizSession | null;
  lastSessionId: string | null;
  questions: Question[];
  currentQuestion: Question | null;
  currentQuestionIndex: number;
  totalQuestions: number;
  answers: Map<string, AnswerResponse>;
  isLoading: boolean;
  loading: boolean;
  error: string | null;
  startSession: (certId: string, type: SessionType, count?: number, perTopic?: number) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  submitAnswer: (answer: string) => Promise<AnswerResponse | null>;
  nextQuestion: () => void;
  previousQuestion: () => void;
  goToQuestion: (index: number) => void;
  completeSession: () => Promise<SessionResults>;
  endSession: () => Promise<void>;
  toggleBookmark: (questionId: string) => Promise<void>;
  getSuggestions: (certId: string) => Promise<QuizSuggestion[]>;
  resetQuiz: () => void;
}

const QuizContext = createContext<QuizContextType | undefined>(undefined);

export function QuizProvider({ children }: { children: ReactNode }) {
  const [currentSession, setCurrentSession] = useState<QuizSession | null>(null);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, AnswerResponse>>(new Map());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = useCallback(async (certId: string, type: SessionType, count?: number, perTopic?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const session = await api.quiz.startSession(certId, type, count, perTopic);
      setCurrentSession(session);

      const questionsData = await api.quiz.getQuestions(session.id);
      setQuestions(questionsData);
      setCurrentQuestionIndex(session.current_question_index);
      setAnswers(new Map());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const session = await api.quiz.getSession(sessionId);
      setCurrentSession(session);

      const questionsData = await api.quiz.getQuestions(sessionId);
      setQuestions(questionsData);
      setCurrentQuestionIndex(session.current_question_index);

      // Build answers map from existing answers
      const answersMap = new Map<string, AnswerResponse>();
      questionsData.forEach((q) => {
        if (q.user_answer) {
          answersMap.set(q.id, {
            question_id: q.id,
            user_answer: q.user_answer,
            is_correct: q.user_answer.toUpperCase() === q.correct_answer.charAt(0).toUpperCase(),
            correct_answer: q.correct_answer,
            explanation: q.explanation,
          });
        }
      });
      setAnswers(answersMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const submitAnswer = useCallback(async (answer: string): Promise<AnswerResponse | null> => {
    if (!currentSession) {
      throw new Error('No active session');
    }
    
    const currentQ = questions[currentQuestionIndex];
    if (!currentQ) return null;

    const response = await api.quiz.submitAnswer(currentSession.id, currentQ.id, answer);
    setAnswers((prev) => new Map(prev).set(currentQ.id, response));

    // Update session correct count
    if (response.is_correct && currentSession) {
      setCurrentSession((prev) =>
        prev ? { ...prev, correct_answers: prev.correct_answers + 1 } : null
      );
    }

    return response;
  }, [currentSession, questions, currentQuestionIndex]);

  const nextQuestion = useCallback(() => {
    setCurrentQuestionIndex((prev) => Math.min(prev + 1, questions.length - 1));
  }, [questions.length]);

  const previousQuestion = useCallback(() => {
    setCurrentQuestionIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  const goToQuestion = useCallback((index: number) => {
    if (index >= 0 && index < questions.length) {
      setCurrentQuestionIndex(index);
    }
  }, [questions.length]);

  const completeSession = useCallback(async (): Promise<SessionResults> => {
    if (!currentSession) {
      throw new Error('No active session');
    }

    const results = await api.quiz.completeSession(currentSession.id);
    setCurrentSession((prev) => (prev ? { ...prev, status: 'completed' } : null));
    return results;
  }, [currentSession]);

  const toggleBookmark = useCallback(async (questionId: string) => {
    const question = questions.find((q) => q.id === questionId);
    if (!question) return;

    if (question.is_bookmarked) {
      await api.bookmarks.remove(questionId);
    } else {
      await api.bookmarks.add(questionId);
    }

    // Update local state
    setQuestions((prev) =>
      prev.map((q) =>
        q.id === questionId ? { ...q, is_bookmarked: !q.is_bookmarked } : q
      )
    );
  }, [questions]);

  const getSuggestions = useCallback(async (certId: string): Promise<QuizSuggestion[]> => {
    const response = await api.quiz.getSuggestions(certId);
    return response.suggestions;
  }, []);

  const endSession = useCallback(async () => {
    if (currentSession) {
      setLastSessionId(currentSession.id);
      await api.quiz.completeSession(currentSession.id);
      setCurrentSession(null);
      setQuestions([]);
      setCurrentQuestionIndex(0);
      setAnswers(new Map());
    }
  }, [currentSession]);

  const resetQuiz = useCallback(() => {
    setCurrentSession(null);
    setQuestions([]);
    setCurrentQuestionIndex(0);
    setAnswers(new Map());
    setError(null);
  }, []);

  // Computed values
  const currentQuestion = questions[currentQuestionIndex] || null;
  const totalQuestions = questions.length;

  return (
    <QuizContext.Provider
      value={{
        currentSession,
        lastSessionId,
        questions,
        currentQuestion,
        currentQuestionIndex,
        totalQuestions,
        answers,
        isLoading,
        loading: isLoading,
        error,
        startSession,
        loadSession,
        submitAnswer,
        nextQuestion,
        previousQuestion,
        goToQuestion,
        completeSession,
        endSession,
        toggleBookmark,
        getSuggestions,
        resetQuiz,
      }}
    >
      {children}
    </QuizContext.Provider>
  );
}

export function useQuiz() {
  const context = useContext(QuizContext);
  if (context === undefined) {
    throw new Error('useQuiz must be used within a QuizProvider');
  }
  return context;
}
