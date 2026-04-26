<template>
  <section class="space-y-3 p-3 text-zinc-100">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400">Run config</h2>
    <label class="block">
      <span class="text-xs">Puzzle</span>
      <select v-model="run.puzzleId" class="w-full bg-zinc-800 rounded px-2 py-1">
        <option v-for="p in run.puzzles" :key="p.id" :value="p.id">
          {{ p.id }} — N={{ p.N }} K={{ p.K }}
        </option>
      </select>
    </label>
    <fieldset class="space-y-1">
      <legend class="text-xs">Variant</legend>
      <label
        v-for="v in run.variants"
        :key="v.name"
        class="flex items-center gap-2 rounded bg-zinc-800 px-2 py-1 text-xs"
      >
        <input v-model="run.variant" type="radio" :value="v.name" />
        <span class="flex-1">{{ v.name }}</span>
        <HelpTooltip
          :label="`${v.name} description`"
          :text="variantDescription(v.name)"
        />
      </label>
    </fieldset>
    <label class="block">
      <span class="text-xs">Seed</span>
      <input
        v-model.number="run.seed"
        type="number"
        min="0"
        class="w-full bg-zinc-800 rounded px-2 py-1"
      />
    </label>

    <details>
      <summary class="cursor-pointer text-xs text-zinc-400">Advanced</summary>
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
      class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded py-2"
      :disabled="run.submitting || !run.puzzleId"
      @click="submit"
    >
      {{ run.submitting ? 'Solving…' : 'Run' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ApiClient, ApiError, api as defaultApi } from '../api/client'
import { useRunStore } from '../stores/run'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useNotificationsStore } from '../stores/notifications'
import HelpTooltip from './HelpTooltip.vue'

const props = defineProps<{ client?: ApiClient }>()
const client = props.client ?? defaultApi

const run = useRunStore()
const traceStore = useTraceStore()
const playback = usePlaybackStore()
const notifications = useNotificationsStore()

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

async function refresh(): Promise<void> {
  try {
    run.puzzles = await client.listPuzzles()
    run.variants = await client.listVariants()
    const first = run.puzzles[0]
    if (!run.puzzleId && first) run.puzzleId = first.id
  } catch (err) {
    const text = err instanceof ApiError ? err.detail : String(err)
    notifications.push({ kind: 'error', text })
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
</script>
