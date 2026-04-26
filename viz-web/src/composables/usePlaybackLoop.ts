import { onUnmounted } from 'vue'
import { usePlaybackStore } from '../stores/playback'

export function usePlaybackLoop() {
  const store = usePlaybackStore()
  let raf = 0
  let active = true
  let lastTimestamp: number | null = null
  // Carries fractional frames across ticks so sub-1 fps rates advance precisely.
  let accumulator = 0

  function advance(deltaMs: number): void {
    if (!store.playing) {
      accumulator = 0
      return
    }
    accumulator += store.speed * (deltaMs / 1000)
    const stepBy = Math.floor(accumulator)
    if (stepBy <= 0) return
    accumulator -= stepBy
    const next = store.index + stepBy
    const last = Math.max(0, store.total - 1)
    if (next >= last) {
      store.seek(last)
      if (store.playing) store.togglePlay()
      accumulator = 0
    } else {
      store.seek(next)
    }
  }

  function tick(timestamp: number): void {
    if (!active) return
    const deltaMs = lastTimestamp === null ? 0 : timestamp - lastTimestamp
    lastTimestamp = timestamp
    advance(Math.max(0, deltaMs))
    raf = requestAnimationFrame(tick)
  }

  if (typeof requestAnimationFrame !== 'undefined') {
    raf = requestAnimationFrame(tick)
  }

  onUnmounted(() => {
    active = false
    if (raf) cancelAnimationFrame(raf)
  })

  return {
    _tickForTesting(deltaMs = 1000): void {
      advance(deltaMs)
    },
  }
}
