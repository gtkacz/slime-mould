<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Summary</h2>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <dt class="text-zinc-500">solved</dt>
      <dd :class="trace.footer.solved ? 'text-emerald-400' : 'text-red-400'">
        {{ trace.footer.solved ? 'solved' : 'unsolved' }}
      </dd>
      <dt class="flex items-center gap-1 text-zinc-500">
        <span>iterations</span>
        <HelpTooltip
          label="iterations description"
          text="The number of solver iterations completed before the run stopped."
        />
      </dt>
      <dd class="tabular-nums">{{ trace.footer.iterations_used }}</dd>
      <dt class="flex items-center gap-1 text-zinc-500">
        <span>wall clock</span>
        <HelpTooltip
          label="wall clock description"
          text="Elapsed real time in seconds for this solver run."
        />
      </dt>
      <dd class="tabular-nums">
        {{
          Math.round(trace.footer.wall_clock_s * Math.pow(10, 5) * (1 + Number.EPSILON)) /
          Math.pow(10, 5)
        }}
      </dd>
      <dt class="text-zinc-500">best fitness</dt>
      <dd class="tabular-nums">{{ trace.footer.best_fitness.toFixed(3) }}</dd>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import HelpTooltip from './HelpTooltip.vue'

const { trace } = storeToRefs(useTraceStore())
</script>
