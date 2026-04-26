<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Walkers</h2>
    <table class="w-full text-xs">
      <thead>
        <tr class="text-zinc-500">
          <th class="text-left">id</th>
          <th class="text-left">cell</th>
          <th class="text-left">seg</th>
          <th class="text-left">status</th>
          <th class="text-right">
            <span class="inline-flex items-center justify-end gap-1">
              <span>fitness</span>
              <HelpTooltip
                label="fitness description"
                text="Fitness is path coverage plus waypoint progress, closeness to the next waypoint by Manhattan distance, and a success bonus for a complete valid solution."
              />
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="w in walkers" :key="w.id">
          <td>{{ w.id }}</td>
          <td>({{ w.cell[0] }},{{ w.cell[1] }})</td>
          <td>{{ w.segment }}</td>
          <td :class="statusClass(w.status)">{{ w.status }}</td>
          <td class="text-right tabular-nums">{{ w.fitness.toFixed(3) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import type { WalkerStatus } from '../api/types'
import HelpTooltip from './HelpTooltip.vue'

const { trace } = storeToRefs(useTraceStore())
const { index } = storeToRefs(usePlaybackStore())

const walkers = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return []
  const i = Math.min(index.value, t.frames.length - 1)
  return t.frames[i]?.walkers ?? []
})

function statusClass(s: WalkerStatus): string {
  if (s === 'alive') return 'text-emerald-400'
  if (s === 'dead-end') return 'text-red-400'
  return 'text-blue-400'
}
</script>
