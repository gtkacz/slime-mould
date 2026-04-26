import { defineStore } from 'pinia'
import { ref } from 'vue'

export type LayerKey = 'walls' | 'pheromone' | 'walkers' | 'bestPath' | 'waypoints'

export const usePlaybackStore = defineStore('playback', () => {
  const MAX_SPEED = 1024
  const index = ref(0)
  const total = ref(0)
  const playing = ref(false)
  const speed = ref(1)
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
    playing.value = !playing.value
  }

  function setSpeed(v: number): void {
    if (!Number.isFinite(v) || v < 1) {
      speed.value = 1
      return
    }
    speed.value = Math.min(Math.floor(v), MAX_SPEED)
  }

  function toggleLayer(key: LayerKey): void {
    layers.value[key] = !layers.value[key]
  }

  return {
    MAX_SPEED,
    index,
    total,
    playing,
    speed,
    layers,
    setTotal,
    seek,
    step,
    togglePlay,
    setSpeed,
    toggleLayer,
  }
})
