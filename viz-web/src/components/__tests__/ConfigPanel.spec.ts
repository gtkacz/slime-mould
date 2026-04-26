import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConfigPanel from '../ConfigPanel.vue'
import { ApiClient } from '../../api/client'
import { useTraceStore } from '../../stores/trace'

const fakeTrace = {
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
}

describe('ConfigPanel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('submits a run and writes the trace into the store', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue([
      { id: 'level_1', name: 'Lvl 1', difficulty: 'Easy', N: 2, K: 1 },
    ])
    vi.spyOn(client, 'listVariants').mockResolvedValue([
      { name: 'zipmould-uni-positive', config_path: 'x', defaults: {} },
    ])
    const runSpy = vi
      .spyOn(client, 'runSolve')
      .mockResolvedValue({ trace_id: 't1', trace: fakeTrace })

    const wrapper = mount(ConfigPanel, { props: { client } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="run"]').trigger('click')
    await new Promise((r) => setTimeout(r, 0))

    expect(runSpy).toHaveBeenCalled()
    const store = useTraceStore()
    expect(store.traceId).toBe('t1')
  })

  it('renders math-like advanced variable labels without changing input text', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue([
      { id: 'level_1', name: 'Lvl 1', difficulty: 'Easy', N: 2, K: 1 },
    ])
    vi.spyOn(client, 'listVariants').mockResolvedValue([
      {
        name: 'zipmould-uni-positive',
        config_path: 'x',
        defaults: { alpha: 1, beta: 2 },
      },
    ])

    const wrapper = mount(ConfigPanel, { props: { client } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    const advanced = wrapper.find('details')
    expect(advanced.text()).toContain('α')
    expect(advanced.text()).toContain('β')
    expect(advanced.text()).toContain('Imax')
    expect(advanced.text()).toContain('τmax')
    expect(advanced.text()).toContain('ζ')
    expect(advanced.text()).not.toContain('alpha')
    expect(advanced.findAll('.font-serif')).toHaveLength(6)
    expect(advanced.text()).not.toContain('Pheromone influence exponent')
    await advanced.find('button[aria-label="alpha description"]').trigger('focus')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Pheromone influence exponent')
    expect(wrapper.findAll('input').map((input) => input.attributes('value'))).toContain('1')
  })

  it('shows descriptions for each algorithm variant', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue([
      { id: 'level_1', name: 'Lvl 1', difficulty: 'Easy', N: 2, K: 1 },
    ])
    vi.spyOn(client, 'listVariants').mockResolvedValue([
      { name: 'zipmould-uni-positive', config_path: 'x', defaults: {} },
      { name: 'zipmould-strat-signed', config_path: 'x', defaults: {} },
    ])

    const wrapper = mount(ConfigPanel, { props: { client } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('Single shared pheromone field')
    await wrapper
      .find('button[aria-label="zipmould-uni-positive description"]')
      .trigger('focus')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Single shared pheromone field')
    await wrapper
      .find('button[aria-label="zipmould-strat-signed description"]')
      .trigger('focus')
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Separate pheromone fields per waypoint segment')
  })
})
