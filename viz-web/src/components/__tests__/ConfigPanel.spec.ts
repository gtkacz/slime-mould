import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConfigPanel from '../ConfigPanel.vue'
import { ApiClient } from '../../api/client'
import { useTraceStore } from '../../stores/trace'
import { useRunStore } from '../../stores/run'
import type { PuzzleSummary, VariantSummary } from '../../api/types'

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

const puzzles: PuzzleSummary[] = [
  { id: 'level_10', name: 'Ten Forks', difficulty: 'Hard', N: 8, K: 4 },
  { id: 'level_2', name: 'Small Start', difficulty: 'Easy', N: 4, K: 2 },
  { id: 'bonus_a', name: 'Wide Bend', difficulty: 'Medium', N: 6, K: 3 },
]

const variants: VariantSummary[] = [
  { name: 'zipmould-uni-positive', config_path: 'x', defaults: {} },
  { name: 'zipmould-strat-signed', config_path: 'x', defaults: {} },
]

async function flush(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0))
}

function text(selector: string): string {
  return document.body.querySelector(selector)?.textContent ?? ''
}

describe('ConfigPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.history.replaceState({}, '', '/')
  })

  afterEach(() => {
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

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
    await flush()
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="run"]').trigger('click')
    await flush()

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
    await flush()
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
    await flush()
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

  it('opens the puzzle picker and selects a puzzle', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)

    const wrapper = mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="open-puzzle-picker"]').trigger('click')
    await wrapper.vm.$nextTick()
    expect(text('[role="dialog"]')).toContain('level_2')

    const options = [...document.body.querySelectorAll('[data-test="puzzle-option"]')]
    expect(options.map((option) => option.textContent)).toEqual([
      expect.stringContaining('level_2'),
      expect.stringContaining('level_10'),
      expect.stringContaining('bonus_a'),
    ])
    ;(options[1] as HTMLButtonElement).click()
    await wrapper.vm.$nextTick()

    expect(useRunStore().puzzleId).toBe('level_10')
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(wrapper.text()).toContain('level_10')
  })

  it('filters picker results by text, difficulty, size, and waypoint count', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)

    const wrapper = mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()
    await wrapper.get('[data-test="open-puzzle-picker"]').trigger('click')

    const search = document.body.querySelector('[data-test="puzzle-search"]') as HTMLInputElement
    search.value = 'wide'
    search.dispatchEvent(new Event('input'))
    await wrapper.vm.$nextTick()
    expect(text('[role="dialog"]')).toContain('bonus_a')
    expect(text('[role="dialog"]')).not.toContain('level_2')

    search.value = ''
    search.dispatchEvent(new Event('input'))
    const difficulty = document.body.querySelector(
      '[data-test="puzzle-difficulty-filter"]',
    ) as HTMLSelectElement
    difficulty.value = 'Easy'
    difficulty.dispatchEvent(new Event('change'))
    await wrapper.vm.$nextTick()
    expect(text('[role="dialog"]')).toContain('level_2')
    expect(text('[role="dialog"]')).not.toContain('level_10')

    difficulty.value = ''
    difficulty.dispatchEvent(new Event('change'))
    const size = document.body.querySelector('[data-test="puzzle-size-filter"]') as HTMLSelectElement
    size.value = '8'
    size.dispatchEvent(new Event('change'))
    await wrapper.vm.$nextTick()
    expect(text('[role="dialog"]')).toContain('level_10')
    expect(text('[role="dialog"]')).not.toContain('bonus_a')

    size.value = ''
    size.dispatchEvent(new Event('change'))
    const waypoint = document.body.querySelector(
      '[data-test="puzzle-waypoint-filter"]',
    ) as HTMLSelectElement
    waypoint.value = '3'
    waypoint.dispatchEvent(new Event('change'))
    await wrapper.vm.$nextTick()
    expect(text('[role="dialog"]')).toContain('bonus_a')
    expect(text('[role="dialog"]')).not.toContain('level_2')
  })

  it('clears filters from the picker empty state', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)

    const wrapper = mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()
    await wrapper.get('[data-test="open-puzzle-picker"]').trigger('click')

    const search = document.body.querySelector('[data-test="puzzle-search"]') as HTMLInputElement
    search.value = 'no match'
    search.dispatchEvent(new Event('input'))
    await wrapper.vm.$nextTick()

    expect(text('[role="dialog"]')).toContain('No puzzles match')
    ;(document.body.querySelector('[data-test="clear-puzzle-filters"]') as HTMLButtonElement).click()
    await wrapper.vm.$nextTick()
    expect(document.body.querySelectorAll('[data-test="puzzle-option"]')).toHaveLength(3)
  })

  it('hydrates valid URL params without auto-running the solver', async () => {
    window.history.replaceState(
      {},
      '',
      '/?puzzle_id=bonus_a&seed=42&variant=zipmould-strat-signed',
    )
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)
    const runSpy = vi.spyOn(client, 'runSolve').mockResolvedValue({ trace_id: 't1', trace: fakeTrace })

    mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()

    const run = useRunStore()
    expect(run.puzzleId).toBe('bonus_a')
    expect(run.seed).toBe(42)
    expect(run.variant).toBe('zipmould-strat-signed')
    expect(runSpy).not.toHaveBeenCalled()
  })

  it('ignores invalid URL params and replaces the query with current controls', async () => {
    window.history.replaceState(
      {},
      '',
      '/?puzzle_id=missing&seed=-5&variant=unknown',
    )
    const run = useRunStore()
    run.seed = 123
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)

    mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()

    expect(run.puzzleId).toBe('level_10')
    expect(run.seed).toBe(123)
    expect(run.variant).toBe('zipmould-uni-positive')
    expect(window.location.search).toBe(
      '?puzzle_id=level_10&seed=123&variant=zipmould-uni-positive',
    )
  })

  it('updates query params with replaceState when puzzle, seed, or variant changes', async () => {
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)
    const replaceSpy = vi.spyOn(window.history, 'replaceState')

    const wrapper = mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()
    await wrapper.get('[data-test="open-puzzle-picker"]').trigger('click')
    ;(
      [...document.body.querySelectorAll('[data-test="puzzle-option"]')][2] as HTMLButtonElement
    ).click()
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="seed-input"]').setValue(987)
    await wrapper.get('input[value="zipmould-strat-signed"]').setValue(true)
    await wrapper.vm.$nextTick()

    expect(replaceSpy).toHaveBeenCalled()
    expect(window.location.search).toBe(
      '?puzzle_id=bonus_a&seed=987&variant=zipmould-strat-signed',
    )
  })

  it('copies the current normalized URL as a share link', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })
    const client = new ApiClient()
    vi.spyOn(client, 'listPuzzles').mockResolvedValue(puzzles)
    vi.spyOn(client, 'listVariants').mockResolvedValue(variants)

    const wrapper = mount(ConfigPanel, { props: { client }, attachTo: document.body })
    await flush()
    await wrapper.get('[data-test="seed-input"]').setValue(456)
    await wrapper.get('[data-test="share-link"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(
      expect.stringContaining('?puzzle_id=level_10&seed=456&variant=zipmould-uni-positive'),
    )
  })
})
