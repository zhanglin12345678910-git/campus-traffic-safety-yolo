export interface TraceStep {
  id: string
  sequence: number
  node_name: string
  status: 'running' | 'success' | 'error'
  duration_ms?: number
  error_message?: string
}

export interface Detection {
  class_id: number
  class_name: string
  display_name?: string
  confidence: number
  bbox_xyxy: number[]
  model_role?: 'traffic_sign' | 'general_object'
  model_name?: string
}

export interface VisionEvent {
  event_type: string
  label: string
  severity: 'low' | 'medium' | 'high'
  status: 'candidate' | 'confirmed'
  object_count: number
  threshold: number
  confidence: number
  model_name: string
  requires_manual_review: boolean
  requires_video_confirmation: boolean
  evidence: string
}

export interface RiskResult {
  risk_level: 'low' | 'medium' | 'high' | 'review'
  risk_score: number
  problem_summary: string
  evidence: string[]
  knowledge_references: Array<{ document: string; content: string; score?: number }>
  recommendations: string[]
  review_required: boolean
  uncertainty_note: string
  analysis_mode: string
}

export interface Inspection {
  id: string
  task_no: string
  location: string
  area_type: string
  description?: string
  inspector_name?: string
  status: string
  risk_level?: string
  review_required: boolean
  review_reasons: string[]
  vision_events?: VisionEvent[]
  original_image_url?: string
  result_image_url?: string
  detection_count?: number
  max_confidence?: number | null
  total_duration_ms?: number
  feedback_rating?: number
  feedback_text?: string
  created_at: string
  detections?: Detection[]
  risk_result?: RiskResult
  report_id?: string
}

export interface DailyTrendPoint {
  date: string
  total: number
  review_required: number
  high_risk: number
}

export interface Dashboard {
  total_tasks: number
  today_tasks?: number
  review_required: number
  completed_tasks: number
  risk_counts: Record<string, number>
  daily_trend?: DailyTrendPoint[]
  recent_tasks: Inspection[]
}

export interface AnalyticsSummary {
  total_tasks: number
  completed_tasks: number
  review_required: number
  completion_rate: number
  review_rate: number
  average_duration_ms: number
}

export interface AnalyticsOverview {
  configured_models?: Record<string, string | null>
  summary: AnalyticsSummary
  daily_trend: DailyTrendPoint[]
  risk_counts: Record<string, number>
  status_counts: Record<string, number>
  area_breakdown: Array<{
    area_type: string
    total: number
    review_required: number
    high_risk: number
    average_duration_ms: number
  }>
  review_reason_counts: Array<{ category: string; count: number }>
  model_breakdown: Array<{
    model_role: string
    model_name: string
    detection_count: number
    average_confidence: number
  }>
  class_breakdown: Array<{ class_name: string; detection_count: number }>
  agent_performance: Array<{
    node_name: string
    run_count: number
    average_duration_ms: number
    error_count: number
  }>
}

export interface CampusWeather {
  available: boolean
  message?: string
  weather?: string
  temperature?: string
  report_time?: string
}

export interface KnowledgeDocument {
  id: string
  name: string
  mime_type: string
  status: string
  chunk_count: number
  error_message?: string
  created_at: string
}
