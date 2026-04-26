<template>
  <div class="flex items-center gap-3 px-3 py-2 bg-zinc-800 text-zinc-100 border-t border-zinc-700">
    <button
      data-test="step-back"
      class="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600"
      :disabled="store.total === 0"
      @click="store.step(-1)"
    >⏮</button>
    <button
      data-test="play"
      class="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500"
      :disabled="store.total === 0"
      @click="store.togglePlay"
    >{{ store.playing ? '⏸' : '▶' }}</button>
    <button
      data-test="step-fwd"
      class="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600"
      :disabled="store.total === 0"
      @click="store.step(1)"
    >⏭</button>
    <input
      data-test="scrub"
      type="range"
      class="flex-1"
      :min="0"
      :max="Math.max(0, store.total - 1)"
      :value="store.index"
      :disabled="store.total === 0"
      @input="onScrub"
    />
    <span class="text-xs tabular-nums w-24 text-right">
      {{ store.index }} / {{ Math.max(0, store.total - 1) }}
    </span>
    <select
      class="bg-zinc-700 px-2 py-1 rounded"
      :value="store.speed"
      @change="onSpeed"
    >
      <option :value="1">1×</option>
      <option :value="4">4×</option>
      <option :value="16">16×</option>
      <option :value="64">max</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { usePlaybackStore } from '../stores/playback'

const store = usePlaybackStore()

function onScrub(e: Event): void {
  const v = Number((e.target as HTMLInputElement).value)
  store.seek(v)
}

function onSpeed(e: Event): void {
  const v = Number((e.target as HTMLSelectElement).value)
  store.setSpeed(v)
}
</script>
