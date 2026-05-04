import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PuzzleSummary, VariantSummary } from '../api/types'

export const DEFAULT_SEED = 42

export const useRunStore = defineStore('run', () => {
  const puzzles = ref<PuzzleSummary[]>([])
  const variants = ref<VariantSummary[]>([])
  const submitting = ref(false)
  const puzzleId = ref<string>('')
  const variant = ref<string>('zipmould-uni-positive')
  const seed = ref<number>(DEFAULT_SEED)
  const overrides = ref<Record<string, unknown>>({})

  return {
    puzzles,
    variants,
    submitting,
    puzzleId,
    variant,
    seed,
    overrides,
  }
})
