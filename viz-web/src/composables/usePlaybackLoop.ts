import { onUnmounted } from 'vue'
import { usePlaybackStore } from '../stores/playback'

export function usePlaybackLoop() {
  const store = usePlaybackStore()
  let raf = 0
  let active = true
  // Carries fractional speed across ticks so sub-1× rates advance every N frames.
  let accumulator = 0

  function advance(): void {
    if (!store.playing) {
      accumulator = 0
      return
    }
    accumulator += store.speed
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

  function tick(): void {
    if (!active) return
    advance()
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
    _tickForTesting(): void {
      advance()
    },
  }
}
