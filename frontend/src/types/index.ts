export interface Dataset {
  id: string
  name: string
  description?: string
  source_type: string
  record_count?: number
  time_range_start?: string
  time_range_end?: string
  is_validated: boolean
  created_at: string
  quality_report?: Record<string, any>
  schema_info?: Record<string, any>
  statistics?: {
    n_batches: number
    n_failure_events: number
    n_major_failures: number
  }
}

export interface FailureEvent {
  id: string
  batch_id?: string
  machine_id?: string
  event_time: string
  event_type: string
  severity: 'minor' | 'moderate' | 'major' | 'critical'
  description?: string
  affected_quantity?: number
  downtime_hours?: number
}

export interface Investigation {
  id: string
  name: string
  description?: string
  dataset_id: string
  failure_event_id?: string
  machine_id?: string
  analysis_start_time: string
  analysis_end_time: string
  status: 'created' | 'running' | 'completed' | 'failed'
  created_at: string
  started_at?: string
  completed_at?: string
  candidate_count: number
  top_mechanism_name?: string
  top_mechanism_score?: number
}

export interface CandidateMechanism {
  id: string
  investigation_id: string
  mechanism_type: string
  name: string
  description: string
  rank: number
  overall_score: number
  confidence: number
  cause: string
  process_condition: string
  intermediate_effect: string
  observable_failure: string
  variables_involved: string[]
  entities_involved: string[]
  temporal_conditions: Record<string, any>
  expected_effects: string[]
  discovery_method: string
  temporal_consistency_score: number
  evidence_strength_score: number
  evidence_coverage_score: number
  recurrence_score: number
  plausibility_score: number
  contradiction_penalty: number
  supporting_evidence_count: number
  contradicting_evidence_count: number
  missing_evidence_count: number
  llm_explanation?: string
}

export interface MechanismEvidence {
  id: string
  evidence_type: string
  polarity: 'supporting' | 'contradicting' | 'missing' | 'inconclusive'
  description: string
  strength: number
  source_table: string
  source_id?: string
  source_timestamp?: string
  measured_value?: number
  expected_value?: number
  deviation?: number
  metadata?: Record<string, any>
}

export interface TimelineEvent {
  id: string
  timestamp: string
  event_type: string
  entity_id: string
  entity_type: string
  name: string
  description: string
  severity?: 'normal' | 'low' | 'medium' | 'high' | 'critical'
  metadata?: Record<string, any>
}

export interface GraphNode {
  id: string
  label: string
  type: 'machine' | 'batch' | 'material' | 'sensor' | 'event' | 'mechanism'
  properties?: Record<string, any>
  color?: string
  val?: number
}

export interface GraphLink {
  source: string
  target: string
  relation: string
  weight?: number
  temporal_lag_hours?: number
}

export interface RelationshipGraph {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface Experiment {
  experiment_id: string
  name: string
  experiment_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  metrics: Record<string, number>
}

export interface EvaluationSummary {
  experiments: Experiment[]
  total: number
}
