import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import GridCanvas from '../GridCanvas.vue'
import { useTraceStore } from '../../stores/trace'
import { usePlaybackStore } from '../../stores/playback'
import type { Trace } from '../../api/types'

const tinyTrace: Trace = {
  version: 1,
  puzzle_id: 'tiny',
  config: { tau_max: 10, tau_signed: true },
  seed: 0,
  header: {
    N: 2,
    K: 2,
    L: 4,
    waypoints: [
      [0, 0],
      [1, 1],
    ],
    walls: [],
    blocked: [],
  },
  frames: [
    {
      t: 0,
      v_b: 0,
      v_c: 0,
      tau_delta: { mode: 'unified', edges: [] },
      best: { path: [[0, 0]], fitness: 0 },
      walkers: [{ id: 0, cell: [0, 0], segment: 0, status: 'alive', fitness: 0 }],
    },
  ],
  footer: {
    solved: false,
    infeasible: false,
    solution: null,
    iterations_used: 0,
    wall_clock_s: 0,
    best_fitness: 0,
  },
}

describe('GridCanvas', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders an svg with the expected layer groups', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)
    playback.seek(0)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('[data-layer="walls"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="pheromone"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="best-path"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="walkers"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="waypoints"]').exists()).toBe(true)
  })

  it('hides a layer when its visibility flag flips off', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()
    playback.toggleLayer('pheromone')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-layer="pheromone"]').exists()).toBe(false)
  })

  it('renders walls on the boundary between adjacent cells', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', {
      ...tinyTrace,
      header: {
        ...tinyTrace.header,
        walls: [
          [
            [0, 0],
            [0, 1],
          ],
          [
            [0, 0],
            [1, 0],
          ],
        ],
      },
    })
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const lines = wrapper.findAll('[data-layer="walls"] line')
    expect(lines[0]?.attributes()).toMatchObject({ x1: '240', y1: '0', x2: '240', y2: '240' })
    expect(lines[1]?.attributes()).toMatchObject({ x1: '0', y1: '240', x2: '240', y2: '240' })
  })
})
