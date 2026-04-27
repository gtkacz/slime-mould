<template>
  <section class="space-y-3 p-3 text-zinc-100">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400">Run config</h2>
    <div class="space-y-1">
      <span class="text-xs">Puzzle</span>
      <div class="flex items-stretch gap-1.5">
        <button
          type="button"
          data-test="open-puzzle-picker"
          class="min-w-0 flex-1 rounded bg-zinc-800 px-2 py-2 text-left transition hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
          @click="pickerOpen = true"
        >
          <span v-if="selectedPuzzle" class="block min-w-0">
            <span class="flex items-center gap-2 text-xs text-zinc-300">
              <span class="block truncate text-sm">{{ selectedPuzzle.name }}</span>
              <span :class="difficultyChipClass(selectedPuzzle.difficulty)">
                {{ selectedPuzzle.difficulty }}
              </span>
            </span>
            <span class="mt-1 flex min-w-0 flex-wrap items-center gap-1.5 text-xs text-zinc-400">
              <span class="truncate">{{ selectedPuzzle.id }}</span>
            </span>
          </span>
          <span v-else class="text-sm text-zinc-400">Choose puzzle</span>
        </button>
        <button
          ref="randomPuzzleButton"
          type="button"
          data-test="random-puzzle"
          class="grid w-10 shrink-0 place-items-center rounded bg-zinc-800 text-zinc-200 transition hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500 disabled:opacity-50"
          aria-label="Select random puzzle"
          :aria-describedby="randomPuzzleTooltipOpen ? randomPuzzleTooltipId : undefined"
          :disabled="run.puzzles.length === 0"
          @mouseenter="randomPuzzleTooltipOpen = true"
          @mouseleave="randomPuzzleTooltipOpen = false"
          @focus="randomPuzzleTooltipOpen = true"
          @blur="randomPuzzleTooltipOpen = false"
          @click="selectRandomPuzzle"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M16 3h5v5" />
            <path d="M4 20 21 3" />
            <path d="M21 16v5h-5" />
            <path d="M15 15 21 21" />
            <path d="M4 4l5 5" />
          </svg>
        </button>
      </div>
    </div>
    <fieldset class="space-y-1">
      <legend class="text-xs">Variant</legend>
      <label v-for="v in run.variants" :key="v.name" :class="variantRowClass(v.name)">
        <input v-model="run.variant" type="radio" :value="v.name" />
        <span class="flex-1">{{ v.name }}</span>
        <HelpTooltip :label="`${v.name} description`" :text="variantDescription(v.name)" />
      </label>
    </fieldset>
    <div class="space-y-1">
      <span :id="seedLabelId" class="text-xs">Seed</span>
      <div class="flex items-stretch gap-1.5">
        <input
          v-model.number="run.seed"
          data-test="seed-input"
          type="number"
          min="0"
          :aria-labelledby="seedLabelId"
          class="min-w-0 flex-1 rounded bg-zinc-800 px-2 py-1 text-sm tabular-nums transition hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
        />
        <button
          ref="randomSeedButton"
          type="button"
          data-test="random-seed"
          class="grid w-9 shrink-0 place-items-center rounded bg-zinc-800 text-zinc-200 transition hover:bg-zinc-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500 disabled:opacity-50"
          aria-label="Randomize seed"
          :aria-describedby="randomSeedTooltipOpen ? randomSeedTooltipId : undefined"
          @mouseenter="randomSeedTooltipOpen = true"
          @mouseleave="randomSeedTooltipOpen = false"
          @focus="randomSeedTooltipOpen = true"
          @blur="randomSeedTooltipOpen = false"
          @click="randomizeSeed"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M16 3h5v5" />
            <path d="M4 20 21 3" />
            <path d="M21 16v5h-5" />
            <path d="M15 15 21 21" />
            <path d="M4 4l5 5" />
          </svg>
        </button>
      </div>
    </div>
    <button
      type="button"
      data-test="share-link"
      class="w-full rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-200 transition hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
      @click="shareLink"
    >
      Share link
    </button>

    <details>
      <summary class="cursor-pointer text-xs text-zinc-400 transition hover:text-zinc-100">
        Advanced
      </summary>
      <div class="mt-2 space-y-1">
        <div
          v-for="param in advancedParams"
          :key="param.key"
          class="grid grid-cols-[2rem_1rem_minmax(0,1fr)] items-center gap-2"
        >
          <span class="font-serif text-sm leading-none" v-html="param.symbol"></span>
          <HelpTooltip :label="`${param.name} description`" :text="param.description" />
          <input
            class="w-full min-w-0 bg-zinc-800 rounded px-2 py-1 text-xs"
            :aria-label="param.name"
            :value="run.overrides[param.key] ?? variantDefault(param.key)"
            @input="onOverride(param.key, ($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>
    </details>

    <button
      data-test="run"
      class="w-full rounded bg-blue-600 py-2 transition hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-300 disabled:opacity-50"
      :disabled="run.submitting || !run.puzzleId"
      @click="submit"
    >
      {{ run.submitting ? 'Solving…' : 'Run' }}
    </button>

    <PuzzlePickerDialog
      :open="pickerOpen"
      :puzzles="run.puzzles"
      @close="pickerOpen = false"
      @select="selectPuzzle"
    />
    <Teleport to="body">
      <div
        v-if="randomPuzzleTooltipOpen"
        :id="randomPuzzleTooltipId"
        ref="randomPuzzleTooltip"
        role="tooltip"
        class="z-50 max-w-64 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs leading-snug text-zinc-100 shadow"
        :style="randomPuzzleTooltipStyles"
      >
        Select random puzzle
      </div>
      <div
        v-if="randomSeedTooltipOpen"
        :id="randomSeedTooltipId"
        ref="randomSeedTooltip"
        role="tooltip"
        class="z-50 max-w-64 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs leading-snug text-zinc-100 shadow"
        :style="randomSeedTooltipStyles"
      >
        Randomize seed
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ApiClient, ApiError, api as defaultApi } from '../api/client'
import { useRunStore } from '../stores/run'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useNotificationsStore } from '../stores/notifications'
import { useRunUrlSync } from '../composables/useRunUrlSync'
import HelpTooltip from './HelpTooltip.vue'
import PuzzlePickerDialog from './PuzzlePickerDialog.vue'

const props = defineProps<{ client?: ApiClient }>()
const client = props.client ?? defaultApi

const run = useRunStore()
const traceStore = useTraceStore()
const playback = usePlaybackStore()
const notifications = useNotificationsStore()
const pickerOpen = ref(false)
const urlSync = useRunUrlSync(run)
const randomPuzzleButton = ref<HTMLElement | null>(null)
const randomPuzzleTooltip = ref<HTMLElement | null>(null)
const randomPuzzleTooltipOpen = ref(false)
const randomPuzzleTooltipId = `random-puzzle-tooltip-${Math.random().toString(36).slice(2)}`
const randomSeedButton = ref<HTMLElement | null>(null)
const randomSeedTooltip = ref<HTMLElement | null>(null)
const randomSeedTooltipOpen = ref(false)
const seedLabelId = `seed-label-${Math.random().toString(36).slice(2)}`
const randomSeedTooltipId = `random-seed-tooltip-${Math.random().toString(36).slice(2)}`

const { floatingStyles: randomPuzzleTooltipStyles } = useFloating(
  randomPuzzleButton,
  randomPuzzleTooltip,
  {
    placement: 'right',
    whileElementsMounted: autoUpdate,
    middleware: [offset(8), flip(), shift({ padding: 8 })],
  },
)
const { floatingStyles: randomSeedTooltipStyles } = useFloating(
  randomSeedButton,
  randomSeedTooltip,
  {
    placement: 'right',
    whileElementsMounted: autoUpdate,
    middleware: [offset(8), flip(), shift({ padding: 8 })],
  },
)

const selectedPuzzle = computed(() => run.puzzles.find((puzzle) => puzzle.id === run.puzzleId))

function difficultyChipClass(difficulty: string): string {
  const normalized = difficulty.toLowerCase()
  const base = 'rounded-xl px-2 py-0.5 text-[11px] font-medium ring-1'
  if (normalized.includes('easy'))
    return `${base} bg-emerald-500/15 text-emerald-200 ring-emerald-400/25`
  if (normalized.includes('medium'))
    return `${base} bg-amber-500/15 text-amber-200 ring-amber-400/25`
  if (normalized.includes('hard')) return `${base} bg-rose-500/15 text-rose-200 ring-rose-400/25`
  return `${base} bg-sky-500/15 text-sky-200 ring-sky-400/25`
}

function variantRowClass(name: string): string {
  const base =
    'flex items-center gap-2 rounded px-2 py-1 text-xs transition hover:bg-zinc-700 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-zinc-500'
  if (run.variant === name) {
    return `${base} bg-blue-500/15 text-blue-100 ring-1 ring-blue-400/25`
  }
  return `${base} bg-zinc-800 text-zinc-100`
}

const advancedParams = [
  {
    key: 'alpha',
    name: 'alpha',
    symbol: '&alpha;',
    description: 'Pheromone influence exponent used when choosing the next move.',
  },
  {
    key: 'beta',
    name: 'beta',
    symbol: '&beta;',
    description: 'Heuristic influence exponent used when choosing the next move.',
  },
  {
    key: 'iter_cap',
    name: 'iteration cap',
    symbol: 'I<sub>max</sub>',
    description: 'Maximum number of solver iterations before the run stops.',
  },
  {
    key: 'population',
    name: 'population',
    symbol: 'n',
    description: 'Number of walkers sampled in each iteration.',
  },
  {
    key: 'tau_max',
    name: 'maximum pheromone',
    symbol: '&tau;<sub>max</sub>',
    description: 'Upper bound used when clamping pheromone values.',
  },
  {
    key: 'z',
    name: 'zeta',
    symbol: '&zeta;',
    description: 'Exploration pressure parameter for stochastic path selection.',
  },
] as const

const variantDescriptions: Record<string, string> = {
  'zipmould-uni-signed':
    'Single shared pheromone field with signed reinforcement, so good moves can be boosted and poor moves can be discouraged.',
  'zipmould-uni-positive':
    'Single shared pheromone field with positive-only reinforcement. This is the tuned default and usually the fastest ZipMould variant.',
  'zipmould-strat-signed':
    'Separate pheromone fields per waypoint segment with signed reinforcement, preserving segment-specific memory and penalties.',
  'zipmould-strat-positive':
    'Separate pheromone fields per waypoint segment with positive-only reinforcement, emphasizing segment-specific successful moves.',
}

function variantDescription(name: string): string {
  return variantDescriptions[name] ?? 'Algorithm variant loaded from the server.'
}

function variantDefault(key: string): unknown {
  const v = run.variants.find((x) => x.name === run.variant)
  return v?.defaults[key]
}

function onOverride(key: string, value: string): void {
  if (value === '') {
    const next = { ...run.overrides }
    delete next[key]
    run.overrides = next
    return
  }
  const num = Number(value)
  run.overrides = { ...run.overrides, [key]: Number.isFinite(num) ? num : value }
}

function selectPuzzle(puzzleId: string): void {
  run.puzzleId = puzzleId
}

function selectRandomPuzzle(): void {
  if (run.puzzles.length === 0) return
  const index = Math.floor(Math.random() * run.puzzles.length)
  const puzzle = run.puzzles[index]
  if (puzzle) selectPuzzle(puzzle.id)
}

function randomizeSeed(): void {
  run.seed = Math.floor(Math.random() * 1e9)
}

watch(
  () => run.puzzleId,
  (puzzleId) => {
    if (!traceStore.trace || traceStore.trace.puzzle_id === puzzleId) return
    traceStore.clear()
    playback.setTotal(0)
  },
)

async function refresh(): Promise<void> {
  try {
    run.puzzles = await client.listPuzzles()
    run.variants = await client.listVariants()
    const first = run.puzzles[0]
    if (!run.puzzleId && first) run.puzzleId = first.id
    urlSync.hydrate()
    urlSync.start()
  } catch (err) {
    const text = err instanceof ApiError ? err.detail : String(err)
    notifications.push({ kind: 'error', text })
  }
}

async function shareLink(): Promise<void> {
  const url = urlSync.update()
  try {
    await navigator.clipboard.writeText(url)
    notifications.push({ kind: 'info', text: 'Share link copied.' })
  } catch {
    notifications.push({ kind: 'error', text: 'Could not copy share link.' })
  }
}

async function submit(): Promise<void> {
  if (run.submitting) return
  run.submitting = true
  try {
    const resp = await client.runSolve({
      puzzle_id: run.puzzleId,
      variant: run.variant,
      seed: run.seed,
      config_overrides: run.overrides,
    })
    traceStore.set(resp.trace_id, resp.trace)
    playback.setTotal(resp.trace.frames.length)
    playback.seek(0)
  } catch (err) {
    const text = err instanceof ApiError ? `${err.kind}: ${err.detail}` : String(err)
    notifications.push({ kind: 'error', text })
  } finally {
    run.submitting = false
  }
}

onMounted(refresh)
onUnmounted(urlSync.stop)
</script>
