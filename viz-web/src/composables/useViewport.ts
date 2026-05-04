import { onMounted, onUnmounted, ref, type Ref } from 'vue'

const SMALL_SCREEN_BREAKPOINT_PX = 1024

export interface ViewportState {
  isSmall: Ref<boolean>
}

export function useViewport(): ViewportState {
  const isSmall = ref(false)

  let media: MediaQueryList | null = null

  function update(): void {
    isSmall.value = media?.matches ?? false
  }

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    media = window.matchMedia(`(max-width: ${SMALL_SCREEN_BREAKPOINT_PX - 1}px)`)
    update()
    media.addEventListener('change', update)
  })

  onUnmounted(() => {
    media?.removeEventListener('change', update)
    media = null
  })

  return { isSmall }
}
