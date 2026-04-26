import { onUnmounted } from 'vue'
import { usePlaybackStore } from '../stores/playback'

export function usePlaybackLoop() {
  const store = usePlaybackStore()
  let raf = 0
  let active = true

  function tick(): void {
    if (!active) return
    if (store.playing) {
      const next = store.index + store.speed
      const last = Math.max(0, store.total - 1)
      if (next >= last) {
        store.seek(last)
        if (store.playing) store.togglePlay()
      } else {
        store.seek(next)
      }
    }
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
      if (!store.playing) return
      const next = store.index + store.speed
      const last = Math.max(0, store.total - 1)
      if (next >= last) {
        store.seek(last)
        if (store.playing) store.togglePlay()
      } else {
        store.seek(next)
      }
    },
  }
}
