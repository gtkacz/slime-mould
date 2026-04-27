import { watch, type WatchStopHandle } from 'vue'
import type { PuzzleSummary, VariantSummary } from '../api/types'

interface RunUrlState {
  puzzleId: string
  seed: number
  variant: string
  puzzles: PuzzleSummary[]
  variants: VariantSummary[]
}

export function hydrateRunFromUrl(run: RunUrlState, win: Window = window): void {
  const params = new URL(win.location.href).searchParams
  const puzzleId = params.get('puzzle_id')
  const seed = params.get('seed')
  const variant = params.get('variant')

  if (puzzleId && run.puzzles.some((puzzle) => puzzle.id === puzzleId)) {
    run.puzzleId = puzzleId
  }

  if (variant && run.variants.some((candidate) => candidate.name === variant)) {
    run.variant = variant
  }

  if (seed !== null) {
    const parsed = Number(seed)
    if (Number.isInteger(parsed) && parsed >= 0) {
      run.seed = parsed
    }
  }
}

export function updateRunUrl(run: RunUrlState, win: Window = window): string {
  const url = new URL(win.location.href)

  if (run.puzzleId) {
    url.searchParams.set('puzzle_id', run.puzzleId)
  } else {
    url.searchParams.delete('puzzle_id')
  }

  if (Number.isInteger(run.seed) && run.seed >= 0) {
    url.searchParams.set('seed', String(run.seed))
  } else {
    url.searchParams.delete('seed')
  }

  if (run.variant) {
    url.searchParams.set('variant', run.variant)
  } else {
    url.searchParams.delete('variant')
  }

  win.history.replaceState(win.history.state, '', url)
  return url.href
}

export function useRunUrlSync(run: RunUrlState, win: Window = window): {
  hydrate: () => void
  start: () => void
  stop: () => void
  update: () => string
} {
  let stopWatch: WatchStopHandle | undefined

  function hydrate(): void {
    hydrateRunFromUrl(run, win)
  }

  function update(): string {
    return updateRunUrl(run, win)
  }

  function start(): void {
    stopWatch?.()
    stopWatch = watch(
      () => [run.puzzleId, run.seed, run.variant] as const,
      () => update(),
      { immediate: true },
    )
  }

  function stop(): void {
    stopWatch?.()
    stopWatch = undefined
  }

  return { hydrate, start, stop, update }
}
