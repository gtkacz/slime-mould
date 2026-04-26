import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useTraceReplay } from '../useTraceReplay'
import type { Trace } from '../../api/types'

function makeTrace(L: number, mode: 'unified' | 'stratified', frameDeltas: [number, number, number][][]): Trace {
  return {
    version: 1,
    puzzle_id: 't',
    config: { tau_max: 10, tau_signed: true },
    seed: 0,
    header: { N: 2, K: 1, L, waypoints: [], walls: [], blocked: [] },
    frames: frameDeltas.map((edges, i) => ({
      t: i,
      v_b: 0,
      v_c: 0,
      tau_delta: { mode, edges },
      best: { path: [], fitness: 0 },
      walkers: [],
    })),
    footer: {
      solved: false,
      infeasible: false,
      solution: null,
      iterations_used: 0,
      wall_clock_s: 0,
      best_fitness: 0,
    },
  }
}

describe('useTraceReplay', () => {
  it('accumulates deltas forward', () => {
    const trace = makeTrace(2, 'unified', [
      [[0, -1, 0.5]],
      [[1, -1, 0.25]],
      [[0, -1, -0.1]],
    ])
    const idx = ref(0)
    const replay = useTraceReplay(ref(trace), idx)
    expect(Array.from(replay.tau.value)).toEqual([0, 0, 0, 0])
    idx.value = 1
    expect(Array.from(replay.tau.value)).toEqual([0.5, 0, 0, 0])
    idx.value = 2
    expect(Array.from(replay.tau.value)).toEqual([0.5, 0.25, 0, 0])
    idx.value = 3
    expect(replay.tau.value[0]).toBeCloseTo(0.4)
  })

  it('seeking forward and back gives the same field as forward replay', () => {
    const deltas: [number, number, number][][] = []
    for (let i = 0; i < 200; i++) {
      deltas.push([[(i * 7) % 16, -1, 0.01]])
    }
    const trace = makeTrace(8, 'unified', deltas)
    const idx = ref(0)
    const replay = useTraceReplay(ref(trace), idx, { checkpointInterval: 32 })

    idx.value = 199
    const forward = Float32Array.from(replay.tau.value)
    idx.value = 0
    idx.value = 199
    const seek = Float32Array.from(replay.tau.value)
    expect(Array.from(seek)).toEqual(Array.from(forward))
  })

  it('exposes current frame, walkers, and best path', () => {
    const trace = makeTrace(2, 'unified', [[]])
    const idx = ref(0)
    const replay = useTraceReplay(ref(trace), idx)
    expect(replay.frame.value?.t).toBe(0)
    expect(replay.walkers.value).toEqual([])
    expect(replay.bestPath.value).toEqual([])
  })
})
