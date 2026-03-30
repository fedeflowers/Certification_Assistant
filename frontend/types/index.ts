/**
 * TypeScript type definitions for the Certification Assistant.
 */

// Certification types
export interface Certification {
  id: string;
  name: string;
  slug: string;
  description?: string;
  pdf_path: string;
  total_questions: number;
  created_at: string;
  updated_at: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  processing_progress: number;
  last_studied?: string;
  accuracy?: number;
}

export interface CertificationListItem {
  id: string;
  name: string;
  slug: string;
  total_questions: number;
  processing_status: string;
  created_at: string;
  last_studied?: string;
  accuracy?: number;
}

// Question types
export interface QuestionImage {
  id: string;
  image_path: string;
  image_order: number;
  position_in_pdf?: string;
  width?: number;
  height?: number;
}

export interface Question {
  id: string;
  question_number: number;
  question_text: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  has_images: boolean;
  is_multi_select: boolean;
  topic?: string;
  difficulty?: string;
  images: QuestionImage[];
  is_bookmarked: boolean;
  user_answer?: string;
  is_answered?: boolean;
}

// Quiz session types
export type SessionType = 'weak_areas' | 'continue' | 'review' | 'random' | 'full' | 'stratified';

export interface TopicInfo {
  topic: string;
  question_count: number;
  accuracy?: number;
}

export interface TopicsResponse {
  topics: TopicInfo[];
  total_questions: number;
}

export interface QuizSession {
  id: string;
  certification_id: string;
  session_type: SessionType;
  started_at: string;
  completed_at?: string;
  total_questions: number;
  correct_answers: number;
  status: 'in_progress' | 'completed' | 'abandoned';
  current_question_index: number;
}

export interface TopicStat {
  topic: string;
  total: number;
  correct: number;
  accuracy: number;
}

export interface SessionResults {
  session_id: string;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  accuracy: number;
  duration_seconds?: number;
  session_type?: string;
  topic_stats: TopicStat[];
}

export interface AnswerResponse {
  question_id: string;
  user_answer: string;
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
}

// Quiz suggestion types
export interface QuizSuggestion {
  type: SessionType;
  title: string;
  description: string;
  question_count: number;
  data?: Record<string, unknown>;
}

// Bookmark types
export interface Bookmark {
  id: string;
  question_id: string;
  bookmarked_at: string;
  notes?: string;
  question_text?: string;
  certification_name?: string;
  last_answer_correct?: boolean;
}

// Analytics types
export interface OverallStats {
  total_questions_answered: number;
  correct_answers: number;
  accuracy: number;
  study_streak: number;
  total_time_spent_minutes: number;
  questions_today: number;
  trend?: 'up' | 'down' | 'stable';
  trend_value?: number;
  exam_readiness_score?: number;
}

export interface WeakArea {
  topic: string;
  total_questions: number;
  correct: number;
  accuracy: number;
  certification_id: string;
  certification_name: string;
}

export interface ProgressTrendItem {
  date: string;
  accuracy: number;
  questions_answered: number;
  correct: number;
}

export interface CertificationPerformance {
  certification_id: string;
  certification_name: string;
  total_questions: number;
  answered: number;
  correct: number;
  accuracy: number;
}

export interface ExamReadiness {
  certification_id: string;
  certification_name: string;
  readiness_score: number;
  components: {
    accuracy: number;
    coverage: number;
    weak_areas: number;
    trend: number;
  };
  recommendation: string;
}

export interface RecentActivity {
  type: 'quiz_completed' | 'certification_added' | 'milestone';
  title: string;
  description: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

// Upload types
export interface UploadResponse {
  job_id: string;
  certification_id: string;
  message: string;
}

export interface ProcessingStatus {
  certification_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  total_questions?: number;
  questions_extracted?: number;
  total_blocks?: number;
  current_block?: number;
  error?: string;
}
