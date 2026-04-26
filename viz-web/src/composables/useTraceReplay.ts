import { computed, ref, watch, type Ref } from 'vue'
import type { Frame, Trace } from '../api/types'

export interface UseTraceReplayOptions {
  checkpointInterval?: number
}

const DEFAULT_CHECKPOINT_INTERVAL = 64

function tauLength(trace: Trace): number {
  const stripes = trace.frames.some((f) => f.tau_delta.mode === 'stratified')
    ? Math.max(2, trace.header.K)
    : 1
  return stripes * 2 * trace.header.L
}

function flatIndex(edgeId: number, stripe: number, halfL: number, mode: 'unified' | 'stratified'): number {
  const s = mode === 'unified' || stripe < 0 ? 0 : stripe
  return s * halfL + edgeId
}

function applyDelta(buf: Float32Array, frame: Frame, halfL: number): void {
  for (const [edgeId, stripe, delta] of frame.tau_delta.edges) {
    const idx = flatIndex(edgeId, stripe, halfL, frame.tau_delta.mode)
    buf[idx] = (buf[idx] ?? 0) + delta
  }
}

export function useTraceReplay(
  trace: Ref<Trace | null>,
  index: Ref<number>,
  opts: UseTraceReplayOptions = {},
) {
  const interval = opts.checkpointInterval ?? DEFAULT_CHECKPOINT_INTERVAL
  const checkpoints = ref<Float32Array[]>([])
  const tau = ref<Float32Array>(new Float32Array(0))
  const lastIndex = ref(-1)

  function rebuildCheckpoints(t: Trace): void {
    const length = tauLength(t)
    const halfL = 2 * t.header.L
    const cps: Float32Array[] = []
    const buf = new Float32Array(length)
    cps.push(new Float32Array(buf))
    for (let i = 0; i < t.frames.length; i++) {
      applyDelta(buf, t.frames[i]!, halfL)
      if ((i + 1) % interval === 0) cps.push(new Float32Array(buf))
    }
    checkpoints.value = cps
  }

  function seek(t: Trace, target: number): void {
    const length = tauLength(t)
    const halfL = 2 * t.header.L
    const cpIdx = Math.min(Math.floor(target / interval), checkpoints.value.length - 1)
    const buf = new Float32Array(checkpoints.value[cpIdx] ?? new Float32Array(length))
    const start = cpIdx * interval
    for (let i = start; i < target; i++) {
      applyDelta(buf, t.frames[i]!, halfL)
    }
    tau.value = buf
    lastIndex.value = target
  }

  function step(t: Trace, target: number): void {
    if (target === lastIndex.value + 1 && lastIndex.value >= 0) {
      const next = new Float32Array(tau.value)
      applyDelta(next, t.frames[lastIndex.value]!, 2 * t.header.L)
      tau.value = next
      lastIndex.value = target
    } else {
      seek(t, target)
    }
  }

  watch(
    trace,
    (t) => {
      if (!t) {
        checkpoints.value = []
        tau.value = new Float32Array(0)
        lastIndex.value = -1
        return
      }
      rebuildCheckpoints(t)
      seek(t, Math.min(Math.max(index.value, 0), t.frames.length))
    },
    { immediate: true },
  )

  watch(index, (target) => {
    const t = trace.value
    if (!t || t.frames.length === 0) return
    const clamped = Math.min(Math.max(target, 0), t.frames.length)
    if (clamped === lastIndex.value) return
    if (clamped > lastIndex.value && clamped - lastIndex.value <= 1) {
      step(t, clamped)
    } else {
      seek(t, clamped)
    }
  }, { flush: 'sync' })

  const frame = computed<Frame | null>(() => {
    const t = trace.value
    if (!t || t.frames.length === 0) return null
    const i = Math.min(Math.max(index.value, 0), t.frames.length - 1)
    return t.frames[i] ?? null
  })

  const walkers = computed(() => frame.value?.walkers ?? [])
  const bestPath = computed(() => frame.value?.best.path ?? [])

  return { tau, frame, walkers, bestPath }
}
