import type { RunRequest, RunResponse } from './types'

const CACHE_FORMAT_VERSION = 1
const CACHE_ROOT = 'zipmould:run-cache'
const CACHE_PREFIX = `${CACHE_ROOT}:v${CACHE_FORMAT_VERSION}:${__APP_VERSION__}:`
const INDEX_KEY = `${CACHE_PREFIX}index`
const TTL_MS = 30 * 24 * 60 * 60 * 1000
const MAX_ENTRIES = 40
const MAX_BYTES = 4_000_000

interface CacheIndexEntry {
  key: string
  createdAt: number
  lastAccessedAt: number
  bytes: number
}

interface CachedRunResponse {
  cacheFormatVersion: number
  appVersion: string
  request: NormalizedRunRequest
  response: RunResponse
  createdAt: number
  lastAccessedAt: number
  bytes: number
}

interface NormalizedRunRequest {
  puzzle_id: string
  variant: string
  seed: number
  config_overrides: unknown
}

function storage(): Storage | null {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

function normalizeValue(value: unknown): unknown {
  if (value === null) return null
  if (typeof value === 'string' || typeof value === 'boolean') return value
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (Array.isArray(value)) return value.map((item) => normalizeValue(item))
  if (typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const key of Object.keys(value).sort()) {
      const normalized = normalizeValue((value as Record<string, unknown>)[key])
      if (normalized !== undefined) out[key] = normalized
    }
    return out
  }
  return undefined
}

function normalizeRequest(req: RunRequest): NormalizedRunRequest {
  const overrides = normalizeValue(req.config_overrides ?? {})
  const normalizedOverrides =
    overrides && typeof overrides === 'object' && !Array.isArray(overrides) ? overrides : {}

  return {
    puzzle_id: req.puzzle_id,
    variant: req.variant,
    seed: req.seed,
    config_overrides: normalizedOverrides,
  }
}

function stableStringify(value: unknown): string {
  return JSON.stringify(normalizeValue(value))
}

function hashString(value: string): string {
  let hash = 0x811c9dc5
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i)
    hash = Math.imul(hash, 0x01000193)
  }
  return (hash >>> 0).toString(36)
}

function keyForRequest(req: RunRequest): {
  key: string
  request: NormalizedRunRequest
  requestJson: string
} {
  const request = normalizeRequest(req)
  const requestJson = stableStringify(request)
  return { key: `${CACHE_PREFIX}${hashString(requestJson)}`, request, requestJson }
}

function parseIndex(raw: string | null): CacheIndexEntry[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.filter((entry): entry is CacheIndexEntry => {
      if (!entry || typeof entry !== 'object') return false
      const candidate = entry as Partial<CacheIndexEntry>
      return (
        typeof candidate.key === 'string' &&
        typeof candidate.createdAt === 'number' &&
        typeof candidate.lastAccessedAt === 'number' &&
        typeof candidate.bytes === 'number'
      )
    })
  } catch {
    return []
  }
}

function readIndex(store: Storage): CacheIndexEntry[] {
  return parseIndex(store.getItem(INDEX_KEY))
}

function writeIndex(store: Storage, entries: CacheIndexEntry[]): void {
  store.setItem(INDEX_KEY, JSON.stringify(entries))
}

function sameRequest(a: NormalizedRunRequest, bJson: string): boolean {
  return stableStringify(a) === bJson
}

function isFresh(entry: CachedRunResponse, now: number): boolean {
  return now - entry.createdAt <= TTL_MS
}

function removeKey(store: Storage, key: string): void {
  store.removeItem(key)
}

function removeStaleVersions(store: Storage): void {
  for (let i = store.length - 1; i >= 0; i -= 1) {
    const key = store.key(i)
    if (key?.startsWith(`${CACHE_ROOT}:`) && !key.startsWith(CACHE_PREFIX)) {
      store.removeItem(key)
    }
  }
}

function compactIndex(store: Storage, now: number): CacheIndexEntry[] {
  removeStaleVersions(store)

  const existing = readIndex(store)
  const live: CacheIndexEntry[] = []
  for (const entry of existing) {
    const raw = store.getItem(entry.key)
    if (!raw) continue
    try {
      const cached = JSON.parse(raw) as CachedRunResponse
      if (isFresh(cached, now)) live.push({ ...entry, bytes: raw.length })
      else removeKey(store, entry.key)
    } catch {
      removeKey(store, entry.key)
    }
  }
  return live
}

function enforceLimits(store: Storage, entries: CacheIndexEntry[]): CacheIndexEntry[] {
  const sorted = [...entries].sort((a, b) => b.lastAccessedAt - a.lastAccessedAt)
  let total = sorted.reduce((sum, entry) => sum + entry.bytes, 0)
  const kept: CacheIndexEntry[] = []

  for (const entry of sorted) {
    const wouldExceedCount = kept.length >= MAX_ENTRIES
    const wouldExceedBytes = total > MAX_BYTES && kept.length > 0
    if (wouldExceedCount || wouldExceedBytes) {
      removeKey(store, entry.key)
      total -= entry.bytes
      continue
    }
    kept.push(entry)
  }

  return kept
}

function removeOldest(store: Storage, entries: CacheIndexEntry[]): CacheIndexEntry[] {
  const sorted = [...entries].sort((a, b) => a.lastAccessedAt - b.lastAccessedAt)
  const oldest = sorted[0]
  if (!oldest) return []
  removeKey(store, oldest.key)
  return sorted.slice(1)
}

export class RunResponseCache {
  get(req: RunRequest): RunResponse | null {
    const store = storage()
    if (!store) return null

    const now = Date.now()
    const { key, requestJson } = keyForRequest(req)
    const raw = store.getItem(key)
    if (!raw) return null

    try {
      const cached = JSON.parse(raw) as CachedRunResponse
      if (
        cached.cacheFormatVersion !== CACHE_FORMAT_VERSION ||
        cached.appVersion !== __APP_VERSION__ ||
        !sameRequest(cached.request, requestJson) ||
        !isFresh(cached, now)
      ) {
        removeKey(store, key)
        writeIndex(
          store,
          readIndex(store).filter((entry) => entry.key !== key),
        )
        return null
      }

      cached.lastAccessedAt = now
      const nextRaw = JSON.stringify(cached)
      store.setItem(key, nextRaw)
      const index = readIndex(store).filter((entry) => entry.key !== key)
      index.push({
        key,
        createdAt: cached.createdAt,
        lastAccessedAt: now,
        bytes: nextRaw.length,
      })
      writeIndex(store, enforceLimits(store, index))
      return cached.response
    } catch {
      removeKey(store, key)
      return null
    }
  }

  set(req: RunRequest, response: RunResponse): void {
    const store = storage()
    if (!store) return

    const now = Date.now()
    const { key, request } = keyForRequest(req)
    const cached: CachedRunResponse = {
      cacheFormatVersion: CACHE_FORMAT_VERSION,
      appVersion: __APP_VERSION__,
      request,
      response,
      createdAt: now,
      lastAccessedAt: now,
      bytes: 0,
    }
    cached.bytes = JSON.stringify(cached).length
    const finalRaw = JSON.stringify(cached)
    if (finalRaw.length > MAX_BYTES) return

    try {
      let index = compactIndex(store, now).filter((entry) => entry.key !== key)
      index.push({ key, createdAt: now, lastAccessedAt: now, bytes: finalRaw.length })
      index = enforceLimits(store, index)
      store.setItem(key, finalRaw)
      writeIndex(store, index)
    } catch {
      try {
        let index = removeOldest(store, compactIndex(store, now)).filter(
          (entry) => entry.key !== key,
        )
        index.push({ key, createdAt: now, lastAccessedAt: now, bytes: finalRaw.length })
        index = enforceLimits(store, index)
        store.setItem(key, finalRaw)
        writeIndex(store, index)
      } catch {
        // Cache failures should never block running the solver.
      }
    }
  }

  clear(): void {
    const store = storage()
    if (!store) return
    for (let i = store.length - 1; i >= 0; i -= 1) {
      const key = store.key(i)
      if (key?.startsWith(CACHE_PREFIX)) store.removeItem(key)
    }
  }
}

export const runResponseCache = new RunResponseCache()
