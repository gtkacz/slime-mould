import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import TracePicker from '../TracePicker.vue'
import { ApiClient } from '../../api/client'

describe('TracePicker', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uploads when a file is selected via the input', async () => {
    const client = new ApiClient()
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
    const spy = vi
      .spyOn(client, 'uploadTrace')
      .mockResolvedValue({ trace_id: 'x', trace: fakeTrace })

    const wrapper = mount(TracePicker, { props: { client } })
    const input = wrapper.get<HTMLInputElement>('input[type="file"]')
    const file = new File([new Uint8Array([0xa0])], 'tiny.cbor', { type: 'application/cbor' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')

    expect(spy).toHaveBeenCalledTimes(1)
  })
})
