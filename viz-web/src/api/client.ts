import type {
  HealthResponse,
  PuzzleSummary,
  RunRequest,
  RunResponse,
  VariantSummary,
} from './types'

export class ApiError extends Error {
  readonly kind: string
  readonly detail: string
  readonly status: number
  constructor(kind: string, detail: string, status: number) {
    super(`[${status}] ${kind}: ${detail}`)
    this.kind = kind
    this.detail = detail
    this.status = status
  }
}

async function parseError(resp: Response): Promise<never> {
  let kind = 'http_error'
  let detail = resp.statusText
  try {
    const body = (await resp.json()) as { kind?: string; detail?: string }
    if (body.kind) kind = body.kind
    if (body.detail) detail = body.detail
  } catch {
    // body wasn't JSON; keep defaults
  }
  throw new ApiError(kind, detail, resp.status)
}

export class ApiClient {
  constructor(private readonly base = '/api') {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const resp = await fetch(`${this.base}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
    if (!resp.ok) await parseError(resp)
    return (await resp.json()) as T
  }

  health(): Promise<HealthResponse> {
    return this.request('/health')
  }

  listPuzzles(): Promise<PuzzleSummary[]> {
    return this.request('/puzzles')
  }

  listVariants(): Promise<VariantSummary[]> {
    return this.request('/variants')
  }

  runSolve(req: RunRequest): Promise<RunResponse> {
    return this.request('/runs', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  }

  async uploadTrace(file: Blob): Promise<RunResponse> {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${this.base}/traces/upload`, {
      method: 'POST',
      body: form,
    })
    if (!resp.ok) await parseError(resp)
    return (await resp.json()) as RunResponse
  }

  downloadTraceUrl(traceId: string): string {
    return `${this.base}/traces/${traceId}.cbor`
  }
}

export const api = new ApiClient()
