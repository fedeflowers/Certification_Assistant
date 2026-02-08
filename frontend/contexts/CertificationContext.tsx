'use client';

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { api } from '@/lib/api';
import type { CertificationListItem, UploadResponse } from '@/types';

interface CertificationContextType {
  certifications: CertificationListItem[];
  selectedCertification: CertificationListItem | null;
  loading: boolean;
  error: string | null;
  fetchCertifications: () => Promise<void>;
  selectCertification: (id: string) => void;
  uploadPdf: (file: File) => Promise<UploadResponse>;
  deleteCertification: (id: string) => Promise<void>;
}

const CertificationContext = createContext<CertificationContextType | undefined>(undefined);

export function CertificationProvider({ children }: { children: ReactNode }) {
  const [certifications, setCertifications] = useState<CertificationListItem[]>([]);
  const [selectedCertification, setSelectedCertification] = useState<CertificationListItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCertifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.certifications.list();
      setCertifications(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch certifications');
    } finally {
      setLoading(false);
    }
  }, []);

  const selectCertification = useCallback((id: string) => {
    const cert = certifications.find((c) => c.id === id);
    setSelectedCertification(cert || null);
  }, [certifications]);

  const uploadPdf = useCallback(async (file: File): Promise<UploadResponse> => {
    const response = await api.certifications.upload(file);
    return response;
  }, []);

  const deleteCertification = useCallback(async (id: string) => {
    await api.certifications.delete(id);
    setCertifications((prev) => prev.filter((c) => c.id !== id));
    if (selectedCertification?.id === id) {
      setSelectedCertification(null);
    }
  }, [selectedCertification]);

  // Fetch certifications on mount
  useEffect(() => {
    fetchCertifications();
  }, [fetchCertifications]);

  return (
    <CertificationContext.Provider
      value={{
        certifications,
        selectedCertification,
        loading,
        error,
        fetchCertifications,
        selectCertification,
        uploadPdf,
        deleteCertification,
      }}
    >
      {children}
    </CertificationContext.Provider>
  );
}

export function useCertification() {
  const context = useContext(CertificationContext);
  if (context === undefined) {
    throw new Error('useCertification must be used within a CertificationProvider');
  }
  return context;
}
