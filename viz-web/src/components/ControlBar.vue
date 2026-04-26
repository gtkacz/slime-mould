<template>
  <div class="flex items-center gap-3 px-3 py-2 bg-zinc-800 text-zinc-100 border-t border-zinc-700">
    <button
      data-test="step-back"
      aria-label="Step back"
      title="Step back"
      class="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600 inline-flex items-center justify-center text-base disabled:opacity-50"
      :disabled="store.total === 0"
      @click="store.step(-1)"
    >
      <IconStepBack />
    </button>
    <button
      data-test="play"
      :aria-label="store.playing ? 'Pause' : 'Play'"
      :title="store.playing ? 'Pause' : 'Play'"
      class="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 inline-flex items-center justify-center text-base disabled:opacity-50"
      :disabled="store.total === 0"
      @click="store.togglePlay"
    >
      <IconPause v-if="store.playing" />
      <IconPlay v-else />
    </button>
    <button
      data-test="step-fwd"
      aria-label="Step forward"
      title="Step forward"
      class="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600 inline-flex items-center justify-center text-base disabled:opacity-50"
      :disabled="store.total === 0"
      @click="store.step(1)"
    >
      <IconStepForward />
    </button>
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
      data-test="speed-preset"
      aria-label="Playback speed preset"
      class="bg-zinc-700 px-2 py-1 rounded text-xs"
      :value="presetValue"
      @change="onPreset"
    >
      <option v-for="p in presets" :key="p.value" :value="p.value">{{ p.label }}</option>
      <option value="custom">Custom</option>
    </select>
    <input
      data-test="speed-custom"
      type="number"
      aria-label="Custom playback speed"
      title="Custom playback speed (frames per second)"
      class="bg-zinc-700 px-2 py-1 rounded text-xs w-20 tabular-nums"
      :min="store.MIN_SPEED"
      :max="store.MAX_SPEED"
      step="0.001"
      :value="speedDisplay"
      @change="onCustom"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePlaybackStore } from '../stores/playback'
import IconPlay from './icons/IconPlay.vue'
import IconPause from './icons/IconPause.vue'
import IconStepBack from './icons/IconStepBack.vue'
import IconStepForward from './icons/IconStepForward.vue'

interface SpeedPreset {
  label: string
  value: number
}

const store = usePlaybackStore()

const presets: readonly SpeedPreset[] = [
  { label: '0.001 fps', value: 0.001 },
  { label: '0.005 fps', value: 0.005 },
  { label: '0.01 fps', value: 0.01 },
  { label: '0.05 fps', value: 0.05 },
  { label: '0.25 fps', value: 0.25 },
  { label: '1 fps', value: 1 },
  { label: '4 fps', value: 4 },
  { label: '16 fps', value: 16 },
]

const presetValue = computed<string>(() => {
  const match = presets.find((p) => Math.abs(p.value - store.speed) < 1e-9)
  return match ? String(match.value) : 'custom'
})

const speedDisplay = computed<string>(() => {
  const v = store.speed
  return Number.isInteger(v) ? String(v) : String(Number(v.toFixed(3)))
})

function onScrub(e: Event): void {
  const v = Number((e.target as HTMLInputElement).value)
  store.seek(v)
}

function onPreset(e: Event): void {
  const raw = (e.target as HTMLSelectElement).value
  if (raw === 'custom') return
  const v = Number(raw)
  if (Number.isFinite(v)) store.setSpeed(v)
}

function onCustom(e: Event): void {
  const v = Number((e.target as HTMLInputElement).value)
  if (Number.isFinite(v)) store.setSpeed(v)
}
</script>
