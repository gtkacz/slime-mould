import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFileLoader } from '../useFileLoader'
import { useTraceStore } from '../../stores/trace'
import { ApiClient } from '../../api/client'

describe('useFileLoader', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uploads the file and stores the resulting trace + id', async () => {
    const fakeTrace = {
      version: 1,
      puzzle_id: 'fixture',
      config: {},
      seed: 0,
      header: { N: 2, K: 1, L: 4, waypoints: [], walls: [], blocked: [] },
      frames: [],
      footer: {
        solved: false,
        infeasible: false,
        solution: null,
        iterations_used: 0,
        wall_clock_s: 0,
        best_fitness: 0,
      },
    }
    const client = new ApiClient()
    vi.spyOn(client, 'uploadTrace').mockResolvedValue({ trace_id: 'xyz', trace: fakeTrace })

    const loader = useFileLoader(client)
    const blob = new Blob([new Uint8Array([0xa0])], { type: 'application/cbor' })
    const file = new File([blob], 'tiny.cbor', { type: 'application/cbor' })
    await loader.load(file)

    const store = useTraceStore()
    expect(store.traceId).toBe('xyz')
    expect(store.trace?.puzzle_id).toBe('fixture')
  })
})
