<template>
  <div class="flex flex-col h-screen bg-zinc-950 text-zinc-100">
    <header class="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
      <h1 class="text-sm font-semibold tracking-wide">ZipMould Visualizer</h1>
      <div class="flex items-center gap-2">
        <span v-if="trace" class="text-xs text-zinc-400">
          {{ trace.puzzle_id }} · seed {{ trace.seed }}
        </span>
        <a
          v-if="traceId"
          :href="downloadUrl"
          download
          class="text-xs px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700"
        >Save trace</a>
      </div>
    </header>

    <div class="grid grid-cols-[300px_1fr_320px] flex-1 min-h-0">
      <aside class="overflow-y-auto border-r border-zinc-800">
        <ConfigPanel />
        <TracePicker />
        <LayerToggles />
      </aside>

      <main class="flex items-center justify-center p-4 min-h-0">
        <GridCanvas />
      </main>

      <aside class="overflow-y-auto border-l border-zinc-800">
        <FrameMeta />
        <FitnessChart />
        <WalkerTable />
        <FooterSummary />
      </aside>
    </div>

    <div class="left-2 z-10 pointer-events-none text-[10px] leading-none text-zinc-100/20" style="margin: 0ch 0ch 1ch 1ch;">
      v{{ appVersion }}
    </div>
    <ControlBar />
    <ErrorToasts />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import ConfigPanel from './components/ConfigPanel.vue'
import TracePicker from './components/TracePicker.vue'
import LayerToggles from './components/LayerToggles.vue'
import GridCanvas from './components/GridCanvas.vue'
import FrameMeta from './components/FrameMeta.vue'
import FitnessChart from './components/FitnessChart.vue'
import WalkerTable from './components/WalkerTable.vue'
import FooterSummary from './components/FooterSummary.vue'
import ControlBar from './components/ControlBar.vue'
import ErrorToasts from './components/ErrorToasts.vue'
import { useTraceStore } from './stores/trace'
import { api } from './api/client'
import { usePlaybackLoop } from './composables/usePlaybackLoop'

usePlaybackLoop()

const traceStore = useTraceStore()
const { trace, traceId } = storeToRefs(traceStore)
const downloadUrl = computed(() => (traceId.value ? api.downloadTraceUrl(traceId.value) : '#'))
const appVersion = __APP_VERSION__
</script>
