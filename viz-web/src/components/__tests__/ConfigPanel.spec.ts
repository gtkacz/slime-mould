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
})
