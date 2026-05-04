import { defineStore } from 'pinia'
import { ref } from 'vue'

export type LayerKey = 'walls' | 'pheromone' | 'walkers' | 'bestPath' | 'waypoints'

export const SPEED_PRESETS: readonly number[] = [
  0.001, 0.005, 0.01, 0.05, 0.25, 1, 5, 10, 15, 30, 45, 60, 120,
]

export const AUTO_TARGET_SECONDS = 5

export function pickAutoSpeed(total: number): number {
  if (total <= 1) return 1
  const ideal = (total - 1) / AUTO_TARGET_SECONDS
  let best = SPEED_PRESETS[0]!
  let bestDistance = Infinity
  for (const candidate of SPEED_PRESETS) {
    const distance = Math.abs(Math.log(candidate) - Math.log(ideal))
    if (distance < bestDistance) {
      bestDistance = distance
      best = candidate
    }
  }
  return best
}

export const usePlaybackStore = defineStore('playback', () => {
  const MAX_SPEED = 1024
  const MIN_SPEED = 0.001
  const index = ref(0)
  const total = ref(0)
  const playing = ref(false)
  const speed = ref(1)
  const autoSpeed = ref(true)
  const hoveredWalkerId = ref<number | null>(null)
  const layers = ref<Record<LayerKey, boolean>>({
    walls: true,
    pheromone: true,
    walkers: true,
    bestPath: true,
    waypoints: true,
  })

  function setTotal(n: number): void {
    total.value = Math.max(0, Math.floor(n))
    index.value = Math.min(index.value, Math.max(0, total.value - 1))
    if (autoSpeed.value && total.value > 0) {
      speed.value = pickAutoSpeed(total.value)
    }
  }

  function seek(i: number): void {
    if (total.value === 0) {
      index.value = 0
      return
    }
    index.value = Math.min(Math.max(0, Math.floor(i)), total.value - 1)
  }

  function step(delta: number): void {
    seek(index.value + delta)
  }

  function togglePlay(): void {
    if (playing.value) {
      playing.value = false
      return
    }
    if (total.value > 0 && index.value >= total.value - 1) {
      index.value = 0
    }
    playing.value = true
  }

  function setSpeed(v: number): void {
    autoSpeed.value = false
    if (!Number.isFinite(v) || v < MIN_SPEED) {
      speed.value = MIN_SPEED
      return
    }
    speed.value = Math.min(v, MAX_SPEED)
  }

  function enableAutoSpeed(): void {
    autoSpeed.value = true
    if (total.value > 0) speed.value = pickAutoSpeed(total.value)
  }

  function toggleLayer(key: LayerKey): void {
    layers.value[key] = !layers.value[key]
  }

  function setHoveredWalkerId(id: number | null): void {
    hoveredWalkerId.value = id
  }

  return {
    MAX_SPEED,
    MIN_SPEED,
    index,
    total,
    playing,
    speed,
    autoSpeed,
    hoveredWalkerId,
    layers,
    setTotal,
    seek,
    step,
    togglePlay,
    setSpeed,
    enableAutoSpeed,
    toggleLayer,
    setHoveredWalkerId,
  }
})
