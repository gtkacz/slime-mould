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
    expect(wrapper.find('svg').attributes('viewBox')).toBe('0 0 480 554')
    expect(wrapper.find('[data-layer="cells"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="walls"]').exists()).toBe(true)
    expect(wrapper.find('[data-layer="blocked"]').exists()).toBe(true)
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
    expect(wrapper.find('[data-layer="pheromone-legend"]').exists()).toBe(false)
    expect(wrapper.find('[data-layer="cells"]').exists()).toBe(true)
  })

  it('renders walker ids on the grid', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const marker = wrapper.find('[data-layer="walkers"] .walker-marker')
    expect(marker.exists()).toBe(true)
    expect(marker.attributes('transform')).toBe('translate(120 120)')
    expect(marker.find('circle').attributes('fill')).toBe('#22c55e')
    expect(marker.find('text').text()).toBe('0')
  })

  it('adds grid item tooltips for visible overlays', async () => {
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
        ],
      },
    })
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const pheromone = wrapper.find('[data-layer="pheromone"] rect')
    expect(pheromone.attributes('aria-label')).toBe('Pheromone at (0, 0): 0')
    await pheromone.trigger('pointerenter')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Pheromone at (0, 0): 0')
    await pheromone.trigger('pointerleave')

    const wall = wrapper.find('[data-layer="walls"] line')
    expect(wall.attributes('aria-label')).toBe('Wall')
    await wall.trigger('pointerenter')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Wall')
    await wall.trigger('pointerleave')

    const bestPath = wrapper.find('[data-layer="best-path"] polyline')
    expect(bestPath.attributes('aria-label')).toBe('Best path: solver did not succeed')
    await bestPath.trigger('pointerenter')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Best path: solver did not succeed')
    await bestPath.trigger('pointerleave')

    const walker = wrapper.find('[data-layer="walkers"] .walker-marker')
    expect(walker.attributes('aria-label')).toBe('Walker ID 0: alive')
    await walker.trigger('pointerenter')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Walker ID 0: alive')
    await walker.trigger('pointerleave')

    const waypoint = wrapper.find('[data-layer="waypoints"] .waypoint-marker')
    expect(waypoint.attributes('aria-label')).toBe('Waypoint 1')
    await waypoint.trigger('pointerenter')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Waypoint 1')
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
    expect(lines).toHaveLength(2)
    expect(lines[0]?.attributes()).toMatchObject({
      x1: '240',
      y1: '0',
      x2: '240',
      y2: '240',
      stroke: '#ff3f14',
      'stroke-width': '5',
      'vector-effect': 'non-scaling-stroke',
    })
    expect(lines[1]?.attributes()).toMatchObject({
      x1: '0',
      y1: '240',
      x2: '240',
      y2: '240',
      stroke: '#ff3f14',
      'stroke-width': '5',
      'vector-effect': 'non-scaling-stroke',
    })
  })

  it('renders blocked cells as excluded board squares', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', {
      ...tinyTrace,
      header: {
        ...tinyTrace.header,
        blocked: [[1, 0]],
      },
    })
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const blocked = wrapper.find('[data-layer="blocked"] rect')
    expect(blocked.attributes()).toMatchObject({
      x: '0',
      y: '240',
      width: '240',
      height: '240',
      fill: '#18181b',
    })
  })

  it('renders waypoints as high-contrast numbered badges', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const markers = wrapper.findAll('[data-layer="waypoints"] .waypoint-marker')
    expect(markers).toHaveLength(2)
    expect(markers[0]?.attributes('transform')).toBe('translate(120 120)')
    const halo = markers[0]?.find('.waypoint-marker-halo')
    const ring = markers[0]?.find('.waypoint-marker-ring')
    expect(Number(halo?.attributes('r'))).toBeCloseTo(81.6)
    expect(halo?.attributes()).toMatchObject({
      fill: '#c084fc',
      opacity: '0.18',
    })
    expect(Number(ring?.attributes('r'))).toBeCloseTo(57.6)
    expect(Number(ring?.attributes('stroke-width'))).toBeCloseTo(10.8)
    expect(ring?.attributes()).toMatchObject({
      fill: '#27272a',
      stroke: '#c084fc',
    })
    expect(markers[0]?.find('text').text()).toBe('1')
    expect(markers[1]?.find('text').text()).toBe('2')
  })

  it('keeps major overlay categories on separate hue ranges', async () => {
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
        ],
      },
    })
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-layer="pheromone"] rect').attributes('fill')).toBe(
      'hsl(173 88% 38%)',
    )
    expect(wrapper.find('[data-layer="best-path"] polyline').attributes('stroke')).toBe('#f43f5e')
    expect(wrapper.find('[data-layer="waypoints"] .waypoint-marker-ring').attributes('stroke')).toBe(
      '#c084fc',
    )
    expect(wrapper.find('[data-layer="walls"] line').attributes('stroke')).toBe('#ff3f14')
    expect(wrapper.find('[data-layer="walkers"] circle').attributes('fill')).toBe('#22c55e')
  })

  it('renders a pheromone color legend using the same ramp endpoints', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const legend = wrapper.find('[data-layer="pheromone-legend"]')
    expect(legend.exists()).toBe(true)
    expect(legend.attributes('transform')).toBe('translate(0 502)')
    expect(legend.find('rect').attributes()).toMatchObject({
      width: '112',
      height: '8',
      fill: 'url(#pheromone-gradient)',
    })
    const stops = wrapper.findAll('#pheromone-gradient stop')
    expect(stops.map((stop) => stop.attributes('stop-color'))).toEqual([
      'hsl(190 88% 18%)',
      'hsl(173 88% 38%)',
      'hsl(156 88% 58%)',
    ])
    expect(legend.text()).toContain('pheromone')
    expect(legend.text()).toContain('-10')
    expect(legend.text()).toContain('10')
  })

  it('renders a walker color legend for status colors', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', tinyTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    const legend = wrapper.find('[data-layer="walker-legend"]')
    expect(legend.exists()).toBe(true)
    expect(legend.attributes('transform')).toBe('translate(150 502)')
    expect(legend.text()).toContain('walkers')
    expect(legend.text()).toContain('alive')
    expect(legend.text()).toContain('dead-end')
    expect(legend.text()).toContain('complete')
    expect(legend.findAll('circle').map((circle) => circle.attributes('fill'))).toEqual([
      '#22c55e',
      '#008020',
      '#00e755',
    ])
  })

  it('uses the default best path color before the final frame', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    traceStore.set('id', {
      ...tinyTrace,
      frames: [
        tinyTrace.frames[0]!,
        {
          ...tinyTrace.frames[0]!,
          t: 1,
          best: {
            path: [
              [0, 0],
              [0, 1],
            ],
            fitness: 1,
          },
        },
      ],
    })
    playback.setTotal(2)
    playback.seek(0)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-layer="best-path"] polyline').attributes('stroke')).toBe('#ae43ff')
    expect(wrapper.find('[data-layer="best-path"] polyline').attributes('aria-label')).toBe(
      'Best path',
    )
  })

  it('colors the final best path by solver outcome', async () => {
    const traceStore = useTraceStore()
    const playback = usePlaybackStore()
    const solvedTrace = {
      ...tinyTrace,
      footer: {
        ...tinyTrace.footer,
        solved: true,
      },
    }
    traceStore.set('id', solvedTrace)
    playback.setTotal(1)

    const wrapper = mount(GridCanvas)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-layer="best-path"] polyline').attributes('stroke')).toBe('#14b85a')
    expect(wrapper.find('[data-layer="best-path"] polyline').attributes('aria-label')).toBe(
      'Best path: solver succeeded',
    )
  })
})
