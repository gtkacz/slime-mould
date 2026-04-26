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
    <label class="block">
      <span class="text-xs">Variant</span>
      <select v-model="run.variant" class="w-full bg-zinc-800 rounded px-2 py-1">
        <option v-for="v in run.variants" :key="v.name" :value="v.name">{{ v.name }}</option>
      </select>
    </label>
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
        <div v-for="key in advancedKeys" :key="key" class="flex items-center gap-2">
          <span class="text-xs w-32">{{ key }}</span>
          <input
            class="flex-1 bg-zinc-800 rounded px-2 py-1 text-xs"
            :value="run.overrides[key] ?? variantDefault(key)"
            @input="onOverride(key, ($event.target as HTMLInputElement).value)"
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

const props = defineProps<{ client?: ApiClient }>()
const client = props.client ?? defaultApi

const run = useRunStore()
const traceStore = useTraceStore()
const playback = usePlaybackStore()
const notifications = useNotificationsStore()

const advancedKeys = ['alpha', 'beta', 'iter_cap', 'population', 'tau_max', 'z']

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
