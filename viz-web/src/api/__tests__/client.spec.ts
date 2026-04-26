import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ApiClient, ApiError } from '../client'

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('GETs absolute paths under /api', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ status: 'ok', version: '0.1.0' })),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    const out = await client.health()
    expect(out.status).toBe('ok')
    const url = String(fetchMock.mock.calls[0][0])
    expect(url.endsWith('/api/health')).toBe(true)
  })

  it('throws ApiError with kind+detail on non-2xx', async () => {
    const body = JSON.stringify({ kind: 'puzzle_not_found', detail: 'no-such' })
    const fetchMock = vi.fn(async () => new Response(body, { status: 404 }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new ApiClient()
    await expect(
      client.runSolve({ puzzle_id: 'no-such', variant: 'zipmould-uni-positive', seed: 0 }),
    ).rejects.toMatchObject({
      kind: 'puzzle_not_found',
      detail: 'no-such',
      status: 404,
    })
  })
})
