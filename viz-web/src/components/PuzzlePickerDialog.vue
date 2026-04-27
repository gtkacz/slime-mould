<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 py-8"
      role="presentation"
      @click.self="emit('close')"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="puzzle-picker-title"
        class="flex max-h-[85vh] w-full max-w-2xl flex-col rounded border border-zinc-700 bg-zinc-900 text-zinc-100 shadow-xl"
      >
        <header class="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
          <h3 id="puzzle-picker-title" class="text-sm font-semibold">Choose puzzle</h3>
          <button
            type="button"
            class="rounded p-1.5 text-zinc-300 transition hover:scale-105 hover:bg-zinc-800 hover:text-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500 active:scale-95"
            aria-label="Close puzzle picker"
            @click="emit('close')"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </header>

        <div class="space-y-3 border-b border-zinc-800 p-4">
          <label class="block">
            <span class="text-xs text-zinc-400">Search</span>
            <input
              v-model="search"
              data-test="puzzle-search"
              class="mt-1 w-full rounded bg-zinc-800 px-2 py-1 text-sm transition hover:bg-zinc-700 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-zinc-500"
              type="search"
              placeholder="Puzzle ID or name"
            />
          </label>

          <div class="grid grid-cols-3 gap-2">
            <label class="block">
              <span class="text-xs text-zinc-400">Difficulty</span>
              <select
                v-model="difficulty"
                data-test="puzzle-difficulty-filter"
                class="mt-1 w-full rounded bg-zinc-800 px-2 py-1 text-sm transition hover:bg-zinc-700 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-zinc-500"
              >
                <option value="">Any</option>
                <option v-for="value in difficulties" :key="value" :value="value">
                  {{ value }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs text-zinc-400">Grid Size (NxN)</span>
              <select
                v-model.number="size"
                data-test="puzzle-size-filter"
                class="mt-1 w-full rounded bg-zinc-800 px-2 py-1 text-sm transition hover:bg-zinc-700 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-zinc-500"
              >
                <option value="">Any</option>
                <option v-for="value in sizes" :key="value" :value="value">
                  {{ value }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs text-zinc-400">Amount of Waypoints (K)</span>
              <select
                v-model.number="waypoints"
                data-test="puzzle-waypoint-filter"
                class="mt-1 w-full rounded bg-zinc-800 px-2 py-1 text-sm transition hover:bg-zinc-700 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-zinc-500"
              >
                <option value="">Any</option>
                <option v-for="value in waypointCounts" :key="value" :value="value">
                  {{ value }}
                </option>
              </select>
            </label>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto">
          <button
            v-for="puzzle in filteredPuzzles"
            :key="puzzle.id"
            type="button"
            data-test="puzzle-option"
            class="grid w-full grid-cols-[minmax(0,1fr)_auto] gap-3 border-b border-zinc-800 px-4 py-3 text-left transition hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-zinc-500"
            @click="selectPuzzle(puzzle.id)"
          >
            <span class="min-w-0">
              <span class="block truncate text-sm font-medium">{{ puzzle.name }}</span>
              <span class="block truncate text-xs text-zinc-400">{{ puzzle.id }}</span>
            </span>
            <span class="flex items-center gap-2 text-xs text-zinc-300">
              <span :class="difficultyChipClass(puzzle.difficulty)">{{ puzzle.difficulty }}</span>
            </span>
          </button>

          <div v-if="filteredPuzzles.length === 0" class="space-y-3 px-4 py-8 text-center">
            <p class="text-sm text-zinc-300">No puzzles match the current filters.</p>
            <button
              type="button"
              data-test="clear-puzzle-filters"
              class="rounded bg-zinc-800 px-3 py-1 text-sm transition hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
              @click="clearFilters"
            >
              Clear filters
            </button>
          </div>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PuzzleSummary } from '../api/types'

const props = defineProps<{
  open: boolean
  puzzles: PuzzleSummary[]
}>()

const emit = defineEmits<{
  close: []
  select: [puzzleId: string]
}>()

const search = ref('')
const difficulty = ref('')
const size = ref<number | ''>('')
const waypoints = ref<number | ''>('')

function uniqueSortedNumbers(values: number[]): number[] {
  return [...new Set(values)].sort((a, b) => a - b)
}

function comparePuzzleId(a: string, b: string): number {
  const aMatch = a.match(/\d+/)
  const bMatch = b.match(/\d+/)
  if (aMatch && bMatch) {
    const numeric = Number(aMatch[0]) - Number(bMatch[0])
    if (numeric !== 0) return numeric
  }
  if (aMatch && !bMatch) return -1
  if (!aMatch && bMatch) return 1
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
}

const sortedPuzzles = computed(() =>
  [...props.puzzles].sort((a, b) => comparePuzzleId(a.id, b.id)),
)

const difficulties = computed(() =>
  [...new Set(props.puzzles.map((puzzle) => puzzle.difficulty))]
)
const sizes = computed(() => uniqueSortedNumbers(props.puzzles.map((puzzle) => puzzle.N)))
const waypointCounts = computed(() => uniqueSortedNumbers(props.puzzles.map((puzzle) => puzzle.K)))

function difficultyChipClass(difficulty: string): string {
  const normalized = difficulty.toLowerCase()
  const base = 'rounded-xl px-2 py-0.5 text-[11px] font-medium ring-1'
  if (normalized.includes('easy')) return `${base} bg-emerald-500/15 text-emerald-200 ring-emerald-400/25`
  if (normalized.includes('medium')) return `${base} bg-amber-500/15 text-amber-200 ring-amber-400/25`
  if (normalized.includes('hard')) return `${base} bg-rose-500/15 text-rose-200 ring-rose-400/25`
  return `${base} bg-sky-500/15 text-sky-200 ring-sky-400/25`
}

const filteredPuzzles = computed(() => {
  const query = search.value.trim().toLowerCase()
  return sortedPuzzles.value.filter((puzzle) => {
    const matchesSearch =
      !query ||
      puzzle.id.toLowerCase().includes(query) ||
      puzzle.name.toLowerCase().includes(query)
    const matchesDifficulty = !difficulty.value || puzzle.difficulty === difficulty.value
    const matchesSize = size.value === '' || puzzle.N === size.value
    const matchesWaypoints = waypoints.value === '' || puzzle.K === waypoints.value
    return matchesSearch && matchesDifficulty && matchesSize && matchesWaypoints
  })
})

function clearFilters(): void {
  search.value = ''
  difficulty.value = ''
  size.value = ''
  waypoints.value = ''
}

function selectPuzzle(puzzleId: string): void {
  emit('select', puzzleId)
  emit('close')
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) clearFilters()
  },
)
</script>
