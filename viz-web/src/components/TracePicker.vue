<template>
  <section class="p-3 text-zinc-100 space-y-2">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400">Load trace</h2>
    <label
      class="block border border-dashed border-zinc-600 rounded p-4 text-center cursor-pointer hover:bg-zinc-800"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <span class="text-xs">Drop a .cbor file here, or click to browse.</span>
      <input
        type="file"
        accept=".cbor,application/cbor"
        class="hidden"
        @change="onChange"
      />
    </label>
  </section>
</template>

<script setup lang="ts">
import { ApiClient, api as defaultApi } from '../api/client'
import { useFileLoader } from '../composables/useFileLoader'
import { usePlaybackStore } from '../stores/playback'
import { useTraceStore } from '../stores/trace'

const props = defineProps<{ client?: ApiClient }>()
const loader = useFileLoader(props.client ?? defaultApi)
const playback = usePlaybackStore()
const traceStore = useTraceStore()

async function handle(file: File | undefined): Promise<void> {
  if (!file) return
  await loader.load(file)
  if (traceStore.trace) {
    playback.setTotal(traceStore.trace.frames.length)
    playback.seek(0)
  }
}

function onDrop(e: DragEvent): void {
  void handle(e.dataTransfer?.files?.[0])
}

function onChange(e: Event): void {
  void handle((e.target as HTMLInputElement).files?.[0])
}
</script>
