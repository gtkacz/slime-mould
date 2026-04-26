import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FitnessChart from '../FitnessChart.vue'
import WalkerTable from '../WalkerTable.vue'
import FrameMeta from '../FrameMeta.vue'
import FooterSummary from '../FooterSummary.vue'
import LayerToggles from '../LayerToggles.vue'
import { useTraceStore } from '../../stores/trace'
import { usePlaybackStore } from '../../stores/playback'
import type { Trace } from '../../api/types'

const trace: Trace = {
  version: 1,
  puzzle_id: 'tiny',
  config: { tau_max: 10, tau_signed: true },
  seed: 0,
  header: { N: 2, K: 1, L: 4, waypoints: [[0, 0]], walls: [], blocked: [] },
  frames: [
    {
      t: 0,
      v_b: 0.1,
      v_c: 0.0,
      tau_delta: { mode: 'unified', edges: [] },
      best: { path: [], fitness: 0 },
      walkers: [{ id: 0, cell: [0, 0], segment: 0, status: 'alive', fitness: 0.5 }],
    },
    {
      t: 5,
      v_b: 0.4,
      v_c: 0.2,
      tau_delta: { mode: 'unified', edges: [] },
      best: { path: [], fitness: 0.7 },
      walkers: [
        { id: 0, cell: [1, 1], segment: 1, status: 'complete', fitness: 0.9 },
        { id: 1, cell: [0, 1], segment: 0, status: 'alive', fitness: 0.3 },
      ],
    },
  ],
  footer: {
    solved: true,
    infeasible: false,
    solution: null,
    iterations_used: 5,
    wall_clock_s: 0.012,
    best_fitness: 0.9,
  },
}

describe('telemetry components', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const ts = useTraceStore()
    const pb = usePlaybackStore()
    ts.set('id', trace)
    pb.setTotal(trace.frames.length)
    pb.seek(1)
  })

  it('FitnessChart renders an svg path', () => {
    const w = mount(FitnessChart)
    expect(w.find('svg').exists()).toBe(true)
    expect(w.find('button[aria-label="fitness description"]').exists()).toBe(true)
    expect(w.findAll('path').length).toBeGreaterThan(0)
    expect(w.find('.text-emerald-400').text()).toBe('Vb')
    expect(w.find('.text-blue-400').text()).toBe('Vc')
    expect(w.findAll('sub').map((node) => node.text())).toEqual(['b', 'c'])
  })

  it('WalkerTable lists walkers from the current frame', () => {
    const w = mount(WalkerTable)
    expect(w.text()).toContain('alive')
    expect(w.text()).toContain('complete')
  })

  it('FrameMeta shows current t and V_b/V_c', () => {
    const w = mount(FrameMeta)
    expect(w.text()).toContain('t = 5')
    expect(w.findAll('dt .font-serif').map((node) => node.text())).toEqual(['Vb', 'Vc'])
    expect(w.findAll('sub').map((node) => node.text())).toEqual(['b', 'c'])
    expect(w.text()).toContain('0.4')
    expect(w.text()).toContain('0.2')
  })

  it('FooterSummary shows solved + iters + wall clock', () => {
    const w = mount(FooterSummary)
    expect(w.text().toLowerCase()).toContain('solved')
    expect(w.text()).toContain('5')
    expect(w.text()).toContain('0.012')
  })

  it('LayerToggles flips a layer flag in the playback store', async () => {
    const w = mount(LayerToggles)
    const pb = usePlaybackStore()
    await w.get('[data-test="toggle-pheromone"]').trigger('change')
    expect(pb.layers.pheromone).toBe(false)
  })
})
