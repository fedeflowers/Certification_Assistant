'use client';

import React, { useState, useCallback } from 'react';
import { useCertification } from '@/contexts/CertificationContext';
import { Card, CardHeader, CardContent, Button, Modal, LoadingSpinner, ProgressBar } from '@/components/shared';
import { api } from '@/lib/api';
import type { Certification } from '@/types';

export default function LibraryPage() {
  const { 
    certifications, 
    loading, 
    uploadPdf, 
    deleteCertification, 
    selectCertification,
    selectedCertification 
  } = useCertification();

  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    certificationId: string;
    status: string;
    progress: number;
    questionsExtracted: number;
    currentBlock: number;
    totalBlocks: number;
    message: string;
  } | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [certToDelete, setCertToDelete] = useState<Certification | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(f => f.type === 'application/pdf');
    
    if (pdfFile) {
      await handleUpload(pdfFile);
    }
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleUpload(file);
    }
    // Reset input
    e.target.value = '';
  };

  const handleUpload = async (file: File) => {
    try {
      const response = await uploadPdf(file);
      
      // Start polling for progress
      pollProgress(response.certification_id);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const pollProgress = async (certificationId: string) => {
    const poll = async () => {
      try {
        const status = await api.certifications.getStatus(certificationId);
        
        setUploadProgress({
          certificationId,
          status: status.status,
          progress: status.progress,
          questionsExtracted: status.questions_extracted || 0,
          currentBlock: status.current_block || 0,
          totalBlocks: status.total_blocks || 0,
          message: status.message || ''
        });

        if (status.status === 'pending' || status.status === 'processing') {
          setTimeout(poll, 1000);
        } else if (status.status === 'completed') {
          // Refresh certifications list
          setTimeout(() => {
            setUploadProgress(null);
            window.location.reload(); // Simple refresh to get updated data
          }, 1500);
        } else if (status.status === 'failed') {
          setTimeout(() => setUploadProgress(null), 3000);
        }
      } catch (error) {
        console.error('Failed to poll status:', error);
        setUploadProgress(null);
      }
    };

    poll();
  };

  const handleDeleteClick = (cert: Certification) => {
    setCertToDelete(cert);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (certToDelete) {
      await deleteCertification(certToDelete.id);
      setDeleteModalOpen(false);
      setCertToDelete(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Certification Library</h1>
        <p className="text-gray-600 mt-1">Manage your certification PDFs</p>
      </div>

      {/* Upload Area */}
      <Card>
        <CardContent className="py-8">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
              isDragging
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <div className="text-5xl mb-4">📄</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {isDragging ? 'Drop your PDF here' : 'Upload Certification PDF'}
            </h3>
            <p className="text-gray-600 mb-4">
              Drag and drop a PDF file, or click to browse
            </p>
            <label className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 cursor-pointer transition-colors">
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
              📤 Choose File
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {uploadProgress && (
        <Card className="border-2 border-primary-200">
          <CardContent className="py-6">
            <div className="flex items-center space-x-4">
              {uploadProgress.status === 'processing' || uploadProgress.status === 'pending' ? (
                <LoadingSpinner size="md" />
              ) : uploadProgress.status === 'completed' ? (
                <span className="text-2xl">✅</span>
              ) : (
                <span className="text-2xl">❌</span>
              )}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="font-medium text-gray-900">
                      {uploadProgress.status === 'pending'
                        ? 'Preparing to process...'
                        : uploadProgress.status === 'processing'
                        ? uploadProgress.message || 'Processing PDF...'
                        : uploadProgress.status === 'completed'
                        ? 'Processing complete!'
                        : 'Processing failed'}
                    </span>
                    {uploadProgress.status === 'processing' && uploadProgress.totalBlocks > 0 && (
                      <span className="text-sm text-gray-500 ml-2">
                        (Block {uploadProgress.currentBlock}/{uploadProgress.totalBlocks})
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-semibold text-primary-600">
                    {uploadProgress.questionsExtracted} questions extracted
                  </span>
                </div>
                <ProgressBar 
                  value={uploadProgress.progress} 
                  max={100}
                  color={uploadProgress.status === 'failed' ? 'error' : 'primary'}
                />
                <div className="flex justify-between mt-1 text-xs text-gray-500">
                  <span>{uploadProgress.progress}%</span>
                  {uploadProgress.status === 'processing' && uploadProgress.totalBlocks > 0 && (
                    <span>
                      ~{Math.ceil((uploadProgress.totalBlocks - uploadProgress.currentBlock) * 2)} seconds remaining
                    </span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Certifications Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : certifications.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <div className="text-6xl mb-4">📚</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No Certifications Yet</h2>
            <p className="text-gray-600">Upload your first certification PDF to get started</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {certifications.map((cert) => (
            <Card 
              key={cert.id}
              className={`hover:shadow-lg transition-shadow cursor-pointer ${
                selectedCertification?.id === cert.id ? 'ring-2 ring-primary-500' : ''
              }`}
            >
              <CardContent className="py-6">
                <div className="flex items-start justify-between mb-4">
                  <div 
                    className="flex-1 cursor-pointer"
                    onClick={() => selectCertification(cert.id)}
                  >
                    <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                      {cert.name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {cert.question_count} questions
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteClick(cert);
                    }}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete certification"
                  >
                    🗑️
                  </button>
                </div>
                
                <div className="flex items-center justify-between text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    cert.status === 'completed'
                      ? 'bg-green-100 text-green-700'
                      : cert.status === 'processing'
                      ? 'bg-yellow-100 text-yellow-700'
                      : cert.status === 'failed'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}>
                    {cert.status === 'completed' ? '✓ Ready' : cert.status}
                  </span>
                  <span className="text-gray-400">
                    {new Date(cert.created_at).toLocaleDateString()}
                  </span>
                </div>

                {selectedCertification?.id === cert.id && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <span className="inline-flex items-center text-xs text-primary-600">
                      ✓ Currently selected
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Delete Certification"
      >
        <div className="py-4">
          <p className="text-gray-600">
            Are you sure you want to delete <strong>{certToDelete?.name}</strong>? 
            This will remove all questions and quiz history for this certification.
          </p>
        </div>
        <div className="flex justify-end space-x-3 pt-4 border-t">
          <Button variant="secondary" onClick={() => setDeleteModalOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleConfirmDelete}>
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
