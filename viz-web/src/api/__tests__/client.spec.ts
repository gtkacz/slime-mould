import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ApiClient, ApiError } from '../client'
import type { RunResponse } from '../types'

const fakeRunResponse: RunResponse = {
  trace_id: 'trace-1',
  trace: {
    version: 1,
    puzzle_id: 'level_1',
    config: {},
    seed: 0,
    header: { N: 2, K: 1, L: 4, waypoints: [], walls: [], blocked: [] },
    frames: [],
    footer: {
      solved: true,
      infeasible: false,
      solution: null,
      iterations_used: 0,
      wall_clock_s: 0,
      best_fitness: 0,
    },
  },
}

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('GETs absolute paths under /api', async () => {
    const fetchMock = vi.fn<() => Promise<Response>>(
      async () => new Response(JSON.stringify({ status: 'ok', version: '0.1.0' })),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    const out = await client.health()
    expect(out.status).toBe('ok')
    const url = String((fetchMock.mock.calls[0] as unknown[])[0])
    expect(url.endsWith('/api/health')).toBe(true)
  })

  it('uses an explicit API base URL', async () => {
    const fetchMock = vi.fn<() => Promise<Response>>(
      async () => new Response(JSON.stringify({ status: 'ok', version: '0.1.0' })),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient('https://api.example.com/api')
    await client.health()
    expect((fetchMock.mock.calls[0] as unknown[])[0]).toBe('https://api.example.com/api/health')
  })

  it('throws ApiError with kind+detail on non-2xx', async () => {
    const body = JSON.stringify({ kind: 'puzzle_not_found', detail: 'no-such' })
    const fetchMock = vi.fn<() => Promise<Response>>(
      async () => new Response(body, { status: 404 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    const promise = client.runSolve({
      puzzle_id: 'no-such',
      variant: 'zipmould-uni-positive',
      seed: 0,
    })
    await expect(promise).rejects.toBeInstanceOf(ApiError)
    await expect(promise).rejects.toMatchObject({
      kind: 'puzzle_not_found',
      detail: 'no-such',
      status: 404,
    })
  })

  it('caches successful solver runs in localStorage', async () => {
    const fetchMock = vi.fn<() => Promise<Response>>(
      async () => new Response(JSON.stringify(fakeRunResponse)),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    const req = {
      puzzle_id: 'level_1',
      variant: 'zipmould-uni-positive',
      seed: 0,
    }

    const first = await client.runSolve(req)
    const second = await client.runSolve(req)

    expect(first.trace_id).toBe('trace-1')
    expect(second.trace_id).toBe('trace-1')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('normalizes config overrides when building the local run cache key', async () => {
    const fetchMock = vi.fn<() => Promise<Response>>(
      async () => new Response(JSON.stringify(fakeRunResponse)),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()

    await client.runSolve({
      puzzle_id: 'level_1',
      variant: 'zipmould-uni-positive',
      seed: 0,
      config_overrides: { beta: 2, alpha: 1 },
    })
    await client.runSolve({
      puzzle_id: 'level_1',
      variant: 'zipmould-uni-positive',
      seed: 0,
      config_overrides: { alpha: 1, beta: 2 },
    })
    await client.runSolve({
      puzzle_id: 'level_1',
      variant: 'zipmould-uni-positive',
      seed: 0,
      config_overrides: { alpha: 3, beta: 2 },
    })

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
