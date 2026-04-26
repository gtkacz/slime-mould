<template>
  <svg
    v-if="trace"
    :viewBox="`0 0 ${size} ${size}`"
    class="bg-zinc-900 w-full h-full"
    role="img"
    aria-label="Solver grid"
  >
    <g v-if="layers.walls" data-layer="walls">
      <line
        v-for="(w, i) in trace.header.walls"
        :key="`wall-${i}`"
        :x1="cellPx(w[0][1])"
        :y1="cellPx(w[0][0])"
        :x2="cellPx(w[1][1])"
        :y2="cellPx(w[1][0])"
        stroke="#f87171"
        stroke-width="2"
      />
    </g>
    <g v-if="layers.pheromone" data-layer="pheromone">
      <rect
        v-for="(_value, i) in cells"
        :key="`p-${i}`"
        :x="((i % trace.header.N) * cellSize)"
        :y="(Math.floor(i / trace.header.N) * cellSize)"
        :width="cellSize"
        :height="cellSize"
        :fill="cells[i]"
        stroke="#3f3f46"
        stroke-width="0.5"
      />
    </g>
    <g v-if="layers.bestPath" data-layer="best-path">
      <polyline
        :points="bestPathPoints"
        fill="none"
        stroke="#fafafa"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
        opacity="0.85"
      />
    </g>
    <g v-if="layers.walkers" data-layer="walkers">
      <circle
        v-for="w in walkers"
        :key="`w-${w.id}`"
        :cx="cellCenterX(w.cell)"
        :cy="cellCenterY(w.cell)"
        :r="cellSize * 0.18"
        :fill="walkerColor(w.status)"
      />
    </g>
    <g v-if="layers.waypoints" data-layer="waypoints">
      <text
        v-for="(wp, i) in trace.header.waypoints"
        :key="`wp-${i}`"
        :x="cellCenterX(wp)"
        :y="cellCenterY(wp)"
        text-anchor="middle"
        dominant-baseline="middle"
        :font-size="cellSize * 0.55"
        font-weight="700"
        fill="#fde68a"
      >
        {{ i + 1 }}
      </text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useTraceReplay } from '../composables/useTraceReplay'
import type { WalkerStatus } from '../api/types'

const traceStore = useTraceStore()
const playback = usePlaybackStore()
const { trace } = storeToRefs(traceStore)
const { layers, index } = storeToRefs(playback)

const replay = useTraceReplay(trace, index)

const size = 480
const cellSize = computed(() => (trace.value ? size / trace.value.header.N : 0))

const cellPx = (i: number) => i * cellSize.value
const cellCenterX = (cell: [number, number]) => (cell[1] + 0.5) * cellSize.value
const cellCenterY = (cell: [number, number]) => (cell[0] + 0.5) * cellSize.value

function viridis(t: number): string {
  const u = Math.min(1, Math.max(0, t))
  const r = Math.round(255 * (0.267 + 1.084 * u - 0.351 * u * u))
  const g = Math.round(255 * (0.005 + 1.404 * u - 0.471 * u * u))
  const b = Math.round(255 * (0.329 + 0.718 * u - 0.851 * u * u))
  return `rgb(${r},${g},${b})`
}

const cells = computed<string[]>(() => {
  const t = trace.value
  if (!t) return []
  const cfg = t.config as { tau_max?: number; tau_signed?: boolean }
  const tauMax = (cfg.tau_max as number | undefined) ?? 10
  const tauMin = (cfg.tau_signed as boolean | undefined) ? -tauMax : 0
  const N = t.header.N
  const out = Array.from<string>({ length: N * N })
  const tau = replay.tau.value
  const halfL = 2 * t.header.L
  for (let i = 0; i < N * N; i++) {
    out[i] = viridis(0)
  }
  // crude per-cell aggregate: average tau over the four directional edges
  // adjacent to cell (r,c) where edge_id is r*N + c (rough mapping placeholder)
  // The real edge_of layout lives in solver/state.py; without exposing it,
  // we treat the first L slots as a flat per-edge field and average pairs
  // by column-major adjacency. This approximation is good enough for visual
  // contrast at small N; revisit if/when edge_of is exposed in the trace.
  for (let i = 0; i < halfL && i < tau.length; i++) {
    const cell = i % (N * N)
    const norm = ((tau[i] ?? 0) - tauMin) / Math.max(1e-9, tauMax - tauMin)
    out[cell] = viridis(norm)
  }
  return out
})

const bestPathPoints = computed(() =>
  replay.bestPath.value
    .map((c) => `${cellCenterX(c as [number, number])},${cellCenterY(c as [number, number])}`)
    .join(' '),
)

const walkers = computed(() => replay.walkers.value)

function walkerColor(status: WalkerStatus): string {
  if (status === 'alive') return '#34d399'
  if (status === 'dead-end') return '#f87171'
  return '#60a5fa'
}
</script>
