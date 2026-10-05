import axios from 'axios'
import type {
  Dataset,
  FailureEvent,
  Investigation,
  CandidateMechanism,
  MechanismEvidence,
  TimelineEvent,
  RelationshipGraph,
  EvaluationSummary,
  Experiment,
} from '../types'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // ── Health ──
  getHealth: async () => {
    const res = await apiClient.get('/health')
    return res.data
  },

  // ── Datasets ──
  getDatasets: async (skip = 0, limit = 50): Promise<Dataset[]> => {
    const res = await apiClient.get('/data/datasets', { params: { skip, limit } })
    return res.data
  },

  getDataset: async (id: string): Promise<Dataset> => {
    const res = await apiClient.get(`/data/datasets/${id}`)
    return res.data
  },

  getDatasetFailureEvents: async (datasetId: string): Promise<{ failure_events: FailureEvent[] }> => {
    const res = await apiClient.get(`/data/datasets/${datasetId}/failure-events`)
    return res.data
  },

  uploadDataset: async (formData: FormData): Promise<any> => {
    const res = await apiClient.post('/data/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  generateSyntheticData: async (params: { n_batches?: number; random_seed?: number }): Promise<any> => {
    const form = new FormData()
    if (params.n_batches) form.append('n_batches', params.n_batches.toString())
    if (params.random_seed) form.append('random_seed', params.random_seed.toString())
    const res = await apiClient.post('/data/generate', form)
    return res.data
  },

  // ── Investigations ──
  getInvestigations: async (skip = 0, limit = 50): Promise<{ investigations: Investigation[]; total: number }> => {
    const res = await apiClient.get('/investigations', { params: { skip, limit } })
    return res.data
  },

  getInvestigation: async (id: string): Promise<Investigation> => {
    const res = await apiClient.get(`/investigations/${id}`)
    return res.data
  },

  createInvestigation: async (payload: {
    name: string
    description?: string
    dataset_id: string
    failure_event_id?: string
    machine_id?: string
    analysis_start_time: string
    analysis_end_time: string
  }): Promise<Investigation> => {
    const res = await apiClient.post('/investigations', payload)
    return res.data
  },

  runInvestigation: async (id: string): Promise<{ message: string; investigation_id: string }> => {
    const res = await apiClient.post(`/investigations/${id}/run`)
    return res.data
  },

  getInvestigationMechanisms: async (id: string): Promise<{ mechanisms: CandidateMechanism[]; total: number }> => {
    const res = await apiClient.get(`/investigations/${id}/mechanisms`)
    return res.data
  },

  getInvestigationTimeline: async (id: string): Promise<{ timeline: TimelineEvent[]; total: number }> => {
    const res = await apiClient.get(`/investigations/${id}/timeline`)
    return res.data
  },

  getInvestigationGraph: async (id: string): Promise<RelationshipGraph> => {
    const res = await apiClient.get(`/investigations/${id}/graph`)
    return res.data
  },

  // ── Mechanisms ──
  getMechanism: async (id: string): Promise<CandidateMechanism> => {
    const res = await apiClient.get(`/mechanisms/${id}`)
    return res.data
  },

  getMechanismEvidence: async (
    id: string,
    polarity?: string,
  ): Promise<{ mechanism_id: string; evidence: MechanismEvidence[] }> => {
    const res = await apiClient.get(`/mechanisms/${id}/evidence`, { params: { polarity } })
    return res.data
  },

  // ── Evaluation ──
  runEvaluation: async (payload: {
    dataset_id: string
    experiment_type: string
    description?: string
    config?: Record<string, any>
  }): Promise<{ experiment_id: string; experiment_type: string; status: string; message: string }> => {
    const res = await apiClient.post('/evaluation/evaluate', payload)
    return res.data
  },

  getEvaluationResults: async (experiment_type?: string): Promise<EvaluationSummary> => {
    const res = await apiClient.get('/evaluation/results', { params: { experiment_type } })
    return res.data
  },
}

export default api
