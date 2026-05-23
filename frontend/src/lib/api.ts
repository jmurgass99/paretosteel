import axios from 'axios'

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '',
  headers: { 'Content-Type': 'application/json' },
})

export interface OptimizerRequest {
  catalog: string
  norms: string[]
  objective: 'weight' | 'cost'
  constraints: {
    L_m: number
    Mu_kNm: number
    Pu_kN: number
    deflection_limit?: number
  }
  ga: {
    population: number
    generations: number
  }
}

export interface OptimizerCandidate {
  section: string
  weight_kg: number
  cost_usd: number
  utilization: number
  feasible: boolean
}

export interface OptimizerResponse {
  best: OptimizerCandidate
  pareto: OptimizerCandidate[]
  history: { gen: number; best_weight: number; best_cost: number }[]
}

export async function runOptimizer(req: OptimizerRequest): Promise<OptimizerResponse> {
  const { data } = await api.post<OptimizerResponse>('/api/optimizer/run', req)
  return data
}
