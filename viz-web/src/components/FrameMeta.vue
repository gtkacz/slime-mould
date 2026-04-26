<template>
  <section v-if="trace" class="p-3 text-zinc-100 text-sm">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Frame</h2>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <dt class="text-zinc-500">t =</dt>
      <dd class="tabular-nums">t = {{ frame?.t ?? '-' }}</dd>
      <dt class="text-zinc-500">V_b</dt>
      <dd class="tabular-nums">{{ frame?.v_b.toFixed(3) ?? '-' }}</dd>
      <dt class="text-zinc-500">V_c</dt>
      <dd class="tabular-nums">{{ frame?.v_c.toFixed(3) ?? '-' }}</dd>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraceStore } from '../stores/trace'
import { usePlaybackStore } from '../stores/playback'

const { trace } = storeToRefs(useTraceStore())
const { index } = storeToRefs(usePlaybackStore())

const frame = computed(() => {
  const t = trace.value
  if (!t || !t.frames.length) return null
  return t.frames[Math.min(index.value, t.frames.length - 1)] ?? null
})
</script>
