<template>
  <section v-if="trace" class="p-3 text-zinc-100">
    <h2 class="mb-2 flex items-center gap-1 text-sm uppercase tracking-wide text-zinc-400">
      <span>Fitness</span>
      <HelpTooltip
        label="fitness description"
        text="Fitness is path coverage plus waypoint progress, closeness to the next waypoint by Manhattan distance, and a success bonus for a complete valid solution."
      />
    </h2>
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full">
      <path :d="pathFor('v_b')" fill="none" stroke="#34d399" stroke-width="1.5" />
      <path :d="pathFor('v_c')" fill="none" stroke="#60a5fa" stroke-width="1.5" />
      <line :x1="cursorX" :x2="cursorX" :y1="0" :y2="H" stroke="#fde68a" stroke-dasharray="2 2" />
    </svg>
    <div class="text-xs flex gap-3 mt-1">
      <span class="text-emerald-400 font-serif">V<sub>b</sub></span>
      <span class="text-blue-400 font-serif">V<sub>c</sub></span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import HelpTooltip from './HelpTooltip.vue'

const W = 280
const H = 80

const { trace } = storeToRefs(useTraceStore())
const { index } = storeToRefs(usePlaybackStore())

function range(values: number[]): { lo: number; hi: number } {
  if (!values.length) return { lo: 0, hi: 1 }
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  return { lo, hi: hi === lo ? lo + 1 : hi }
}

const ranges = computed(() => {
  const t = trace.value
  if (!t) return { lo: 0, hi: 1 }
  return range([
    ...t.frames.map((f) => f.v_b),
    ...t.frames.map((f) => f.v_c),
  ])
})

function pathFor(key: 'v_b' | 'v_c'): string {
  const t = trace.value
  if (!t || !t.frames.length) return ''
  const { lo, hi } = ranges.value
  return t.frames
    .map((f, i) => {
      const x = (i / Math.max(1, t.frames.length - 1)) * W
      const y = H - ((f[key] - lo) / (hi - lo)) * H
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

const cursorX = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return 0
  return (index.value / Math.max(1, t.frames.length - 1)) * W
})
</script>
