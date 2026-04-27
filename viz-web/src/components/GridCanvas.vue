<template>
  <svg
    v-if="trace"
    :viewBox="`0 0 ${size} ${canvasHeight}`"
    class="bg-zinc-900 w-full h-full"
    role="img"
    aria-label="Solver grid"
  >
    <defs>
      <linearGradient id="pheromone-gradient" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" :stop-color="pheromoneColor(0)" />
        <stop offset="50%" :stop-color="pheromoneColor(0.5)" />
        <stop offset="100%" :stop-color="pheromoneColor(1)" />
      </linearGradient>
    </defs>
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
        fill-opacity="1"
        stroke="#3f3f46"
        stroke-width="0.95"
        class="pheromone-cell"
        :aria-label="pheromoneTooltip(i)"
        @pointerenter="showPheromoneTooltip($event, i)"
        @pointermove="movePointerTooltip($event)"
        @pointerleave="clearPheromoneHover"
      />
    </g>
    <rect
      v-if="hoveredPheromoneCell !== null"
      data-layer="pheromone-hover"
      :x="((hoveredPheromoneCell % trace.header.N) * cellSize)"
      :y="(Math.floor(hoveredPheromoneCell / trace.header.N) * cellSize)"
      :width="cellSize"
      :height="cellSize"
      :fill="cells[hoveredPheromoneCell]"
      stroke="#f8fafc"
      stroke-width="2"
      class="pheromone-hover-cell"
      pointer-events="none"
    />
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
        stroke-width="5"
        stroke-linecap="round"
        vector-effect="non-scaling-stroke"
        class="wall-stroke wall-stroke-core"
        aria-label="Wall"
        @pointerenter="showPointerTooltip($event, 'Wall')"
        @pointermove="movePointerTooltip($event)"
        @pointerleave="hideTooltip"
      />
    </g>
    <g v-if="layers.bestPath" data-layer="best-path">
      <polyline
        :points="bestPathPoints"
        fill="none"
        :stroke="bestPathStroke"
        stroke-width="5"
        stroke-linecap="round"
        stroke-linejoin="round"
        opacity="0.85"
        class="best-path-line"
        :aria-label="bestPathTooltip"
        @pointerenter="showPointerTooltip($event, bestPathTooltip)"
        @pointermove="movePointerTooltip($event)"
        @pointerleave="hideTooltip"
      />
    </g>
    <g v-if="layers.walkers" data-layer="walkers">
      <g
        v-for="w in walkers"
        :key="`w-${w.id}`"
        class="walker-marker"
        :transform="`translate(${cellCenterX(w.cell)} ${cellCenterY(w.cell)})`"
        :aria-label="walkerTooltip(w)"
        @pointerenter="showPointerTooltip($event, walkerTooltip(w))"
        @pointermove="movePointerTooltip($event)"
        @pointerleave="hideTooltip"
      >
        <circle :r="cellSize * 0.125" :fill="walkerColor(w.status)" />
        <text
          text-anchor="middle"
          dominant-baseline="central"
          :font-size="walkerLabelSize"
          font-weight="800"
          :fill="walkerLabelColor(w.status)"
        >
          {{ w.id }}
        </text>
      </g>
    </g>
    <g v-if="layers.waypoints" data-layer="waypoints">
      <g
        v-for="(wp, i) in trace.header.waypoints"
        :key="`wp-${i}`"
        class="waypoint-marker"
        :transform="`translate(${cellCenterX(wp)} ${cellCenterY(wp)})`"
        :aria-label="waypointTooltip(i)"
        @pointerenter="showPointerTooltip($event, waypointTooltip(i))"
        @pointermove="movePointerTooltip($event)"
        @pointerleave="hideTooltip"
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
    <g
      v-if="layers.pheromone"
      data-layer="pheromone-legend"
      :transform="`translate(${legend.x} ${legend.y})`"
    >
      <rect
        :width="legend.width"
        :height="legend.height"
        fill="url(#pheromone-gradient)"
        stroke="#3f3f46"
        stroke-width="0.75"
      />
      <text :x="0" y="-5" fill="#d4d4d8" font-size="10" font-weight="700">
        pheromone
      </text>
      <text :x="0" :y="legend.height + 11" fill="#a1a1aa" font-size="9">
        {{ formatLegendValue(tauBounds.min) }}
      </text>
      <text
        :x="legend.width"
        :y="legend.height + 11"
        text-anchor="end"
        fill="#a1a1aa"
        font-size="9"
      >
        {{ formatLegendValue(tauBounds.max) }}
      </text>
    </g>
    <g
      v-if="layers.walkers"
      data-layer="walker-legend"
      :transform="`translate(${walkerLegend.x} ${walkerLegend.y})`"
    >
      <text :x="0" y="-5" fill="#d4d4d8" font-size="10" font-weight="700">
        walkers
      </text>
      <g
        v-for="(item, i) in walkerLegendItems"
        :key="item.status"
        :transform="`translate(${i * walkerLegend.itemWidth} 0)`"
      >
        <circle
          :cx="5"
          :cy="4"
          :r="4"
          :fill="item.color"
          stroke="#3f3f46"
          stroke-width="0.75"
        />
        <text x="14" y="7" fill="#a1a1aa" font-size="9">
          {{ item.label }}
        </text>
      </g>
    </g>
  </svg>
  <Teleport to="body">
    <div
      v-if="tooltipOpen"
      ref="floating"
      role="tooltip"
      class="z-50 max-w-64 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs leading-snug text-zinc-100 shadow"
      :style="floatingStyles"
    >
      {{ tooltipText }}
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue'
import { computed, nextTick, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import { useTraceReplay } from '../composables/useTraceReplay'
import type { TraceWall, WalkerSnapshot, WalkerStatus } from '../api/types'

const traceStore = useTraceStore()
const playback = usePlaybackStore()
const { trace } = storeToRefs(traceStore)
const { layers, index } = storeToRefs(playback)

const replay = useTraceReplay(trace, index)
type TooltipReference = {
  getBoundingClientRect: () => DOMRect
}

const tooltipOpen = ref(false)
const tooltipText = ref('')
const reference = ref<TooltipReference | null>(null)
const floating = ref<HTMLElement | null>(null)
const pointerX = ref(0)
const pointerY = ref(0)
const hoveredPheromoneCell = ref<number | null>(null)

const { floatingStyles, update } = useFloating(reference, floating, {
  placement: 'top',
  whileElementsMounted: autoUpdate,
  middleware: [offset(12), flip(), shift({ padding: 8 })],
})

const size = 480
const canvasHeight = size + 74
const legend = {
  x: 0,
  y: size + 22,
  width: 112,
  height: 8,
} as const
const walkerLegend = {
  x: 150,
  y: size + 22,
  itemWidth: 74,
} as const

const palette = {
  wall: '#ff3f14',
  bestPath: '#ae43ff',
  bestPathSolved: '#00672d',
  bestPathUnsolved: '#f32525',
  waypoint: '#c084fc',
  waypointText: '#f5f3ff',
  walkerAlive: '#22c55e',
  walkerDeadEnd: '#808000',
  walkerComplete: '#00e755',
} as const

const cellSize = computed(() => (trace.value ? size / trace.value.header.N : 0))
const baseCells = computed(() => {
  const n = trace.value?.header.N ?? 0
  return Array.from({ length: n * n })
})

const tauBounds = computed(() => {
  const cfg = trace.value?.config as { tau_max?: number; tau_signed?: boolean } | undefined
  const max = cfg?.tau_max ?? 10
  const min = cfg?.tau_signed ? -max : 0
  return { min, max }
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
  const hue = Math.round(190 - 34 * u)
  const lightness = Math.round(18 + 40 * u)
  return `hsl(${hue} 88% ${lightness}%)`
}

const cellPheromones = computed<number[]>(() => {
  const t = trace.value
  if (!t) return []
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
  const out = new Array<number>(cellCount)
  for (let c = 0; c < cellCount; c++) {
    const avg = counts[c]! > 0 ? sums[c]! / counts[c]! : 0
    out[c] = avg
  }
  return out
})

const cells = computed<string[]>(() => {
  const { min: tauMin, max: tauMax } = tauBounds.value
  const span = Math.max(1e-9, tauMax - tauMin)
  return cellPheromones.value.map((value) => pheromoneColor((value - tauMin) / span))
})

function pheromoneTooltip(index: number): string {
  const n = trace.value?.header.N ?? 0
  const row = n > 0 ? Math.floor(index / n) : 0
  const col = n > 0 ? index % n : 0
  return `Pheromone at (${row}, ${col}): ${formatPheromoneValue(cellPheromones.value[index] ?? 0)}`
}

function waypointTooltip(index: number): string {
  return `Waypoint ${index + 1}`
}

function formatPheromoneValue(value: number): string {
  if (Number.isInteger(value)) return value.toString()
  const rounded = value.toFixed(4)
  return rounded.replace(/\.?0+$/, '')
}

const isLastFrame = computed(() => {
  const frameCount = trace.value?.frames.length ?? 0
  return frameCount > 0 && index.value === frameCount - 1
})

const bestPathStroke = computed(() => {
  if (!isLastFrame.value) return palette.bestPath
  return trace.value?.footer.solved ? palette.bestPathSolved : palette.bestPathUnsolved
})

const bestPathTooltip = computed(() => {
  if (!isLastFrame.value) return 'Best path'
  return trace.value?.footer.solved ? 'Best path: solver succeeded' : 'Best path: solver did not succeed'
})

function walkerTooltip(walker: WalkerSnapshot): string {
  return `Walker #${walker.id}: ${walker.status}`
}

function setPointerReference(event: PointerEvent): void {
  pointerX.value = event.clientX
  pointerY.value = event.clientY
  reference.value = {
    getBoundingClientRect: () => new DOMRect(pointerX.value, pointerY.value, 0, 0),
  }
}

function showPointerTooltip(event: PointerEvent, text: string): void {
  tooltipText.value = text
  setPointerReference(event)
  tooltipOpen.value = true
  void nextTick(update)
}

function showPheromoneTooltip(event: PointerEvent, index: number): void {
  hoveredPheromoneCell.value = index
  showPointerTooltip(event, pheromoneTooltip(index))
}

function movePointerTooltip(event: PointerEvent): void {
  if (!tooltipOpen.value) return
  setPointerReference(event)
  void update()
}

function hideTooltip(): void {
  tooltipOpen.value = false
}

function clearPheromoneHover(): void {
  hoveredPheromoneCell.value = null
  hideTooltip()
}

const bestPathPoints = computed(() =>
  replay.bestPath.value
    .map((c) => `${cellCenterX(c as [number, number])},${cellCenterY(c as [number, number])}`)
    .join(' '),
)

const walkers = computed(() => replay.walkers.value)
const walkerLabelSize = computed(() => Math.max(5, Math.min(14, cellSize.value * 0.1)))

const walkerLegendItems = computed(() => [
  { status: 'dead-end' as const, label: 'dead-end', color: palette.walkerDeadEnd },
  { status: 'complete' as const, label: 'complete', color: palette.walkerComplete },
])

function walkerColor(status: WalkerStatus): string {
  if (status === 'alive') return palette.walkerAlive
  if (status === 'dead-end') return palette.walkerDeadEnd
  return palette.walkerComplete
}

function walkerLabelColor(status: WalkerStatus): string {
  return status === 'dead-end' ? '#00de38' : '#64ee9e'
}

function formatLegendValue(value: number): string {
  return Number.isInteger(value) ? value.toString() : value.toFixed(2)
}
</script>

<style scoped>
.pheromone-cell,
.wall-stroke,
.best-path-line,
.walker-marker,
.waypoint-marker {
  cursor: help;
}

.pheromone-cell,
.wall-stroke,
.best-path-line,
.walker-marker circle,
.waypoint-marker-halo,
.waypoint-marker-ring,
.pheromone-hover-cell {
  transition:
    opacity 120ms ease,
    stroke-width 120ms ease,
    filter 120ms ease,
    transform 120ms ease;
}

.pheromone-hover-cell {
  stroke: #f8fafc;
  stroke-width: 2;
  filter: brightness(1.22);
}

.wall-stroke:hover,
.best-path-line:hover {
  filter: brightness(1.1);
  opacity: 100%;
  stroke-width: 10;
}

.walker-marker:hover circle {
  filter: brightness(1.25);
  opacity: 100%;
  transform: scale(1.25);
}

.waypoint-marker:hover .waypoint-marker-halo {
  opacity: 0.32;
}

.waypoint-marker:hover .waypoint-marker-ring {
  filter: brightness(1.2);
}

.waypoint-marker-ring {
  paint-order: stroke;
}

.waypoint-marker text {
  pointer-events: none;
}

.walker-marker text {
  paint-order: stroke;
  pointer-events: none;
}
</style>
