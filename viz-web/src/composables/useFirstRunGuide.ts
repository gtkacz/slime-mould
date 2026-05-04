import { onMounted, ref, type Ref } from 'vue'

const STORAGE_KEY = 'zipmould.viz.introSeen.v1'

export interface FirstRunGuide {
  open: Ref<boolean>
  show: () => void
  dismiss: () => void
}

function readSeen(): boolean {
  try {
    return window.localStorage?.getItem(STORAGE_KEY) === '1'
  } catch {
    return true
  }
}

function writeSeen(): void {
  try {
    window.localStorage?.setItem(STORAGE_KEY, '1')
  } catch {
    /* storage unavailable; nothing to persist */
  }
}

export function useFirstRunGuide(): FirstRunGuide {
  const open = ref(false)

  onMounted(() => {
    if (!readSeen()) open.value = true
  })

  function show(): void {
    open.value = true
  }

  function dismiss(): void {
    open.value = false
    writeSeen()
  }

  return { open, show, dismiss }
}
