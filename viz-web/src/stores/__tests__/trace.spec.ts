import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTraceStore } from '../trace'
import type { Trace } from '../../api/types'

const fakeTrace: Trace = {
  version: 1,
  puzzle_id: 'tiny',
  config: {},
  seed: 0,
  header: { N: 3, K: 2, L: 9, waypoints: [], walls: [], blocked: [] },
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

describe('trace store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts empty', () => {
    const s = useTraceStore()
    expect(s.trace).toBeNull()
    expect(s.traceId).toBeNull()
  })

  it('sets trace and id together', () => {
    const s = useTraceStore()
    s.set('abc', fakeTrace)
    expect(s.trace).toEqual(fakeTrace)
    expect(s.traceId).toBe('abc')
  })

  it('clears state', () => {
    const s = useTraceStore()
    s.set('abc', fakeTrace)
    s.clear()
    expect(s.trace).toBeNull()
    expect(s.traceId).toBeNull()
  })
})
