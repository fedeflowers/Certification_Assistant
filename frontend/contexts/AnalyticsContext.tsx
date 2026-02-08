'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from '@/lib/api';
import type {
  OverallStats,
  WeakArea,
  ProgressTrendItem,
  CertificationPerformance,
  ExamReadiness,
  RecentActivity,
} from '@/types';

interface AnalyticsContextType {
  overallStats: OverallStats | null;
  weakAreas: WeakArea[];
  progressTrend: ProgressTrendItem[];
  certificationPerformance: CertificationPerformance[];
  examReadiness: ExamReadiness | null;
  recentActivity: RecentActivity[];
  loading: boolean;
  isLoading: boolean;
  error: string | null;
  fetchOverallStats: (certificationId?: string) => Promise<void>;
  fetchWeakAreas: (certificationId?: string) => Promise<void>;
  fetchProgressTrend: (period?: '7d' | '30d' | 'all', certificationId?: string) => Promise<void>;
  fetchCertificationPerformance: () => Promise<void>;
  fetchExamReadiness: (certificationId: string) => Promise<void>;
  fetchRecentActivity: (limit?: number) => Promise<void>;
  refreshAll: (certificationId?: string) => Promise<void>;
  refreshStats: (certificationId?: string) => Promise<void>;
  refreshWeakAreas: (certificationId?: string) => Promise<void>;
  refreshProgressTrend: (days?: number, certificationId?: string) => Promise<void>;
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined);

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  const [overallStats, setOverallStats] = useState<OverallStats | null>(null);
  const [weakAreas, setWeakAreas] = useState<WeakArea[]>([]);
  const [progressTrend, setProgressTrend] = useState<ProgressTrendItem[]>([]);
  const [certificationPerformance, setCertificationPerformance] = useState<CertificationPerformance[]>([]);
  const [examReadiness, setExamReadiness] = useState<ExamReadiness | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverallStats = useCallback(async (certificationId?: string) => {
    try {
      const stats = await api.analytics.getOverallStats(certificationId);
      setOverallStats(stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats');
    }
  }, []);

  const fetchWeakAreas = useCallback(async (certificationId?: string) => {
    try {
      const areas = await api.analytics.getWeakAreas(certificationId);
      setWeakAreas(areas);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch weak areas');
    }
  }, []);

  const fetchProgressTrend = useCallback(async (
    period: '7d' | '30d' | 'all' = '30d',
    certificationId?: string
  ) => {
    try {
      const response = await api.analytics.getProgressTrend(period, certificationId);
      setProgressTrend(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch progress trend');
    }
  }, []);

  const fetchCertificationPerformance = useCallback(async () => {
    try {
      const response = await api.analytics.getPerformance();
      setCertificationPerformance(response.certifications);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance');
    }
  }, []);

  const fetchExamReadiness = useCallback(async (certificationId: string) => {
    try {
      const readiness = await api.analytics.getExamReadiness(certificationId);
      setExamReadiness(readiness);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch exam readiness');
    }
  }, []);

  const fetchRecentActivity = useCallback(async (limit?: number) => {
    try {
      const response = await api.analytics.getRecentActivity(limit);
      setRecentActivity(response.activities);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch recent activity');
    }
  }, []);

  const refreshAll = useCallback(async (certificationId?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchOverallStats(certificationId),
        fetchWeakAreas(certificationId),
        fetchProgressTrend('30d', certificationId),
        fetchCertificationPerformance(),
        fetchRecentActivity(10),
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [fetchOverallStats, fetchWeakAreas, fetchProgressTrend, fetchCertificationPerformance, fetchRecentActivity]);

  return (
    <AnalyticsContext.Provider
      value={{
        overallStats,
        weakAreas,
        progressTrend,
        certificationPerformance,
        examReadiness,
        recentActivity,
        isLoading,
        loading: isLoading,
        error,
        fetchOverallStats,
        fetchWeakAreas,
        fetchProgressTrend,
        fetchCertificationPerformance,
        fetchExamReadiness,
        fetchRecentActivity,
        refreshAll,
        refreshStats: refreshAll,
        refreshWeakAreas: fetchWeakAreas,
        refreshProgressTrend: (days?: number, certificationId?: string) => fetchProgressTrend(days === 7 ? '7d' : days === 30 ? '30d' : 'all', certificationId),
      }}
    >
      {children}
    </AnalyticsContext.Provider>
  );
}

export function useAnalytics() {
  const context = useContext(AnalyticsContext);
  if (context === undefined) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider');
  }
  return context;
}
