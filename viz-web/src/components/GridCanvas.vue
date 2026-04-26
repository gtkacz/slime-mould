<template>
  <svg
    v-if="trace"
    :viewBox="`0 0 ${size} ${size}`"
    class="bg-zinc-900 w-full h-full"
    role="img"
    aria-label="Solver grid"
  >
    <g data-layer="cells">
      <rect
        v-for="(_cell, i) in baseCells"
        :key="`cell-${i}`"
        :x="((i % trace.header.N) * cellSize)"
        :y="(Math.floor(i / trace.header.N) * cellSize)"
        :width="cellSize"
        :height="cellSize"
        fill="#18181b"
        stroke="#3f3f46"
        stroke-width="0.5"
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
    <g data-layer="blocked">
      <rect
        v-for="(cell, i) in trace.header.blocked"
        :key="`blocked-${i}`"
        :x="cell[1] * cellSize"
        :y="cell[0] * cellSize"
        :width="cellSize"
        :height="cellSize"
        fill="#18181b"
        stroke="#52525b"
        stroke-width="1"
      />
      <path
        v-for="(cell, i) in trace.header.blocked"
        :key="`blocked-x-${i}`"
        :d="blockedHatchPath(cell)"
        fill="none"
        stroke="#71717a"
        stroke-width="1.5"
        opacity="0.75"
      />
    </g>
    <g v-if="layers.walls" data-layer="walls">
      <line
        v-for="(w, i) in trace.header.walls"
        :key="`wall-core-${i}`"
        :x1="wallLine(w).x1"
        :y1="wallLine(w).y1"
        :x2="wallLine(w).x2"
        :y2="wallLine(w).y2"
        :stroke="palette.wall"
        stroke-width="3"
        stroke-linecap="round"
        vector-effect="non-scaling-stroke"
        class="wall-stroke wall-stroke-core"
      />
    </g>
    <g v-if="layers.bestPath" data-layer="best-path">
      <polyline
        :points="bestPathPoints"
        fill="none"
        :stroke="palette.bestPath"
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
      <g
        v-for="(wp, i) in trace.header.waypoints"
        :key="`wp-${i}`"
        class="waypoint-marker"
        :transform="`translate(${cellCenterX(wp)} ${cellCenterY(wp)})`"
      >
        <circle
          class="waypoint-marker-halo"
          :r="cellSize * 0.34"
          :fill="palette.waypoint"
          opacity="0.18"
        />
        <circle
          class="waypoint-marker-ring"
          :r="cellSize * 0.24"
          fill="#27272a"
          :stroke="palette.waypoint"
          :stroke-width="cellSize * 0.045"
        />
        <text
          text-anchor="middle"
          dominant-baseline="central"
          :font-size="cellSize * 0.25"
          font-weight="800"
          :fill="palette.waypointText"
        >
          {{ i + 1 }}
        </text>
      </g>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useTraceReplay } from '../composables/useTraceReplay'
import type { TraceWall, WalkerStatus } from '../api/types'

const traceStore = useTraceStore()
const playback = usePlaybackStore()
const { trace } = storeToRefs(traceStore)
const { layers, index } = storeToRefs(playback)

const replay = useTraceReplay(trace, index)

const size = 480
const palette = {
  wall: '#ef4444',
  bestPath: '#bb48ec',
  waypoint: '#c084fc',
  waypointText: '#f5f3ff',
  walkerAlive: '#22c55e',
  walkerDeadEnd: '#84cc16',
  walkerComplete: '#14b8a6',
} as const

const cellSize = computed(() => (trace.value ? size / trace.value.header.N : 0))
const baseCells = computed(() => {
  const n = trace.value?.header.N ?? 0
  return Array.from({ length: n * n })
})

const cellCenterX = (cell: [number, number]) => (cell[1] + 0.5) * cellSize.value
const cellCenterY = (cell: [number, number]) => (cell[0] + 0.5) * cellSize.value

function wallLine(wall: TraceWall): { x1: number; y1: number; x2: number; y2: number } {
  const [[r1, c1], [r2, c2]] = wall
  const minRow = Math.min(r1, r2)
  const minCol = Math.min(c1, c2)
  const cs = cellSize.value
  if (r1 === r2) {
    const x = (minCol + 1) * cs
    const y1 = minRow * cs
    return { x1: x, y1, x2: x, y2: y1 + cs }
  }
  const y = (minRow + 1) * cs
  const x1 = minCol * cs
  return { x1, y1: y, x2: x1 + cs, y2: y }
}

function blockedHatchPath(cell: [number, number]): string {
  const x = cell[1] * cellSize.value
  const y = cell[0] * cellSize.value
  const cs = cellSize.value
  return `M ${x} ${y} L ${x + cs} ${y + cs} M ${x + cs} ${y} L ${x} ${y + cs}`
}

function pheromoneColor(t: number): string {
  const u = Math.min(1, Math.max(0, t))
  const hue = Math.round(238 - 34 * u)
  const lightness = Math.round(18 + 40 * u)
  return `hsl(${hue} 88% ${lightness}%)`
}

const cells = computed<string[]>(() => {
  const t = trace.value
  if (!t) return []
  const cfg = t.config as { tau_max?: number; tau_signed?: boolean }
  const tauMax = (cfg.tau_max as number | undefined) ?? 10
  const tauMin = (cfg.tau_signed as boolean | undefined) ? -tauMax : 0
  const N = t.header.N
  const cellCount = N * N
  const tau = replay.tau.value
  const directedEdges = 2 * t.header.L
  // Without an exposed edge_of layout we approximate per-cell intensity by
  // averaging directed-edge slots that fold into each cell via modulo. This
  // preserves the contribution of every tau slot rather than letting the
  // last write win, so going backward in time visibly reduces intensity.
  const sums = new Float64Array(cellCount)
  const counts = new Uint32Array(cellCount)
  const limit = Math.min(directedEdges, tau.length)
  for (let i = 0; i < limit; i++) {
    const cell = i % cellCount
    sums[cell]! += tau[i] ?? 0
    counts[cell]! += 1
  }
  const span = Math.max(1e-9, tauMax - tauMin)
  const out = new Array<string>(cellCount)
  for (let c = 0; c < cellCount; c++) {
    const avg = counts[c]! > 0 ? sums[c]! / counts[c]! : 0
    out[c] = pheromoneColor((avg - tauMin) / span)
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
  if (status === 'alive') return palette.walkerAlive
  if (status === 'dead-end') return palette.walkerDeadEnd
  return palette.walkerComplete
}
</script>

<style scoped>
.waypoint-marker-ring {
  paint-order: stroke;
}

.waypoint-marker text {
  pointer-events: none;
}
</style>
