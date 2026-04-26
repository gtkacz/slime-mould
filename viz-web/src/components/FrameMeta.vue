<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Frame</h2>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <dt class="flex items-center gap-1 text-zinc-500">
        <span>t =</span>
        <HelpTooltip
          label="t description"
          text="Solver iteration captured by the current trace frame."
        />
      </dt>
      <dd class="tabular-nums">t = {{ frame?.t ?? '-' }}</dd>
      <dt class="flex items-center gap-1 text-zinc-500">
        <span class="font-serif">V<sub>b</sub></span>
        <HelpTooltip
          label="V b description"
          text="Oscillator term used during pheromone updates; it decays with run progress."
        />
      </dt>
      <dd class="tabular-nums">{{ frame?.v_b.toFixed(3) ?? '-' }}</dd>
      <dt class="flex items-center gap-1 text-zinc-500">
        <span class="font-serif">V<sub>c</sub></span>
        <HelpTooltip
          label="V c description"
          text="Contraction term used during pheromone updates; it linearly shrinks as the iteration cap approaches."
        />
      </dt>
      <dd class="tabular-nums">{{ frame?.v_c.toFixed(3) ?? '-' }}</dd>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'
import HelpTooltip from './HelpTooltip.vue'

const { trace } = storeToRefs(useTraceStore())
const { index } = storeToRefs(usePlaybackStore())

const frame = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return null
  return t.frames[Math.min(index.value, t.frames.length - 1)] ?? null
})
</script>
