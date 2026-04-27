export type WalkerStatus = 'alive' | 'dead-end' | 'complete'

export interface WalkerSnapshot {
  id: number
  cell: [number, number]
  segment: number
  status: WalkerStatus
  fitness: number
}

export interface BestPath {
  path: [number, number][]
  fitness: number
}

export interface TauDelta {
  mode: 'unified' | 'stratified'
  edges: [number, number, number][]
}

export type TraceWall = [[number, number], [number, number]]

export interface Frame {
  t: number
  v_b: number
  v_c: number
  tau_delta: TauDelta
  best: BestPath
  walkers: WalkerSnapshot[]
}

export interface TraceHeader {
  N: number
  K: number
  L: number
  waypoints: [number, number][]
  walls: TraceWall[]
  blocked: [number, number][]
}

export interface TraceFooter {
  solved: boolean
  infeasible: boolean
  solution: [number, number][] | null
  iterations_used: number
  wall_clock_s: number
  best_fitness: number
}

export interface Trace {
  version: number
  puzzle_id: string
  config: Record<string, unknown>
  seed: number
  header: TraceHeader
  frames: Frame[]
  footer: TraceFooter
}

export interface PuzzleSummary {
  id: string
  name: string
  difficulty: string
  N: number
  K: number
  L: number
  waypoints: [number, number][]
  walls: TraceWall[]
  blocked: [number, number][]
}

export interface VariantSummary {
  name: string
  config_path: string
  defaults: Record<string, unknown>
}

export interface RunRequest {
  puzzle_id: string
  variant: string
  seed: number
  config_overrides?: Record<string, unknown>
}

export interface RunResponse {
  trace_id: string
  trace: Trace
}

export interface HealthResponse {
  status: string
  version: string
}
