import { defineStore } from 'pinia'
import { ref } from 'vue'

export type LayerKey = 'walls' | 'pheromone' | 'walkers' | 'bestPath' | 'waypoints'

export const usePlaybackStore = defineStore('playback', () => {
  const MAX_SPEED = 1024
  const MIN_SPEED = 0.001
  const index = ref(0)
  const total = ref(0)
  const playing = ref(false)
  const speed = ref(1)
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
    if (!Number.isFinite(v) || v < MIN_SPEED) {
      speed.value = MIN_SPEED
      return
    }
    speed.value = Math.min(v, MAX_SPEED)
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
    hoveredWalkerId,
    layers,
    setTotal,
    seek,
    step,
    togglePlay,
    setSpeed,
    toggleLayer,
    setHoveredWalkerId,
  }
})
