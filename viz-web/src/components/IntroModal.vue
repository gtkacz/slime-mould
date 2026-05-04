<template>
  <Teleport to="body">
    <div
      v-if="open"
      data-test="intro-modal"
      class="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 py-8"
      role="presentation"
      @click.self="emit('close')"
      @keydown.esc.stop="emit('close')"
    >
      <section
        ref="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="intro-modal-title"
        tabindex="-1"
        class="flex max-h-[85vh] w-full max-w-2xl flex-col rounded border border-zinc-700 bg-zinc-900 text-zinc-100 shadow-xl"
      >
        <header class="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
          <h3 id="intro-modal-title" class="text-base font-semibold tracking-wide">
            Welcome to ZipMould Visualizer
          </h3>
          <button
            type="button"
            data-test="intro-close"
            class="rounded p-1.5 text-zinc-300 transition hover:scale-105 hover:bg-zinc-800 hover:text-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500 active:scale-95"
            aria-label="Close intro"
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

        <div class="space-y-5 overflow-y-auto px-5 py-4 text-sm leading-relaxed text-zinc-200">
          <section class="space-y-2">
            <h4 class="text-xs uppercase tracking-wide text-zinc-400">What is Zip?</h4>
            <p>
              <strong>Zip</strong> is a LinkedIn grid puzzle. You're given an
              <em>N&times;N</em> board with a handful of numbered cells called
              <em>waypoints</em> (1, 2, &hellip;, K) and an optional set of walled edges. The goal
              is to draw a single path that:
            </p>
            <ul class="list-disc space-y-1 pl-5 text-zinc-300">
              <li>visits <em>every</em> cell exactly once (a Hamiltonian path),</li>
              <li>moves only between 4-adjacent cells with no wall between them,</li>
              <li>passes through the waypoints in ascending numerical order,</li>
              <li>starts at waypoint 1 and ends at waypoint K.</li>
            </ul>
          </section>

          <section class="space-y-2">
            <h4 class="text-xs uppercase tracking-wide text-zinc-400">What is ZipMould?</h4>
            <p>
              <strong>ZipMould</strong> is a slime-mould-inspired solver for Zip. It adapts the
              biological foraging strategy formalized by Li et al. (2020) into a discrete
              ant-colony-style search: a population of walkers explores the grid, deposits
              <em>pheromone</em> on edges that lead to good partial solutions, and biases future
              walkers toward those edges.
            </p>
            <p class="text-zinc-300">
              Across iterations, pheromone concentration on productive edges grows, the population
              converges, and a Hamiltonian path satisfying the waypoint order emerges &mdash; or the
              puzzle is reported infeasible.
            </p>
          </section>

          <section class="space-y-2">
            <h4 class="text-xs uppercase tracking-wide text-zinc-400">Using this visualizer</h4>
            <p>
              Pick a puzzle, choose a variant, then <strong>Run</strong>. The center canvas replays
              the solver frame by frame, the left panel controls the run, and the right panel shows
              fitness, walker state, and final summary. Pheromone, walker positions, the current
              best path, and waypoints can each be toggled.
            </p>
          </section>
        </div>

        <footer class="flex justify-end border-t border-zinc-800 px-5 py-3">
          <button
            type="button"
            data-test="intro-acknowledge"
            class="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-300"
            @click="emit('close')"
          >
            Got it
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const dialog = ref<HTMLElement | null>(null)

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    await nextTick()
    dialog.value?.focus()
  },
  { immediate: true },
)
</script>
