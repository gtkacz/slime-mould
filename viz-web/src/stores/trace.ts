import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Trace } from '../api/types'

export const useTraceStore = defineStore('trace', () => {
  const trace = ref<Trace | null>(null)
  const traceId = ref<string | null>(null)

  function set(id: string, value: Trace): void {
    traceId.value = id
    trace.value = value
  }

  function clear(): void {
    trace.value = null
    traceId.value = null
  }

  return { trace, traceId, set, clear }
})
