<template>
  <div class="flex flex-col h-screen bg-zinc-950 text-zinc-100">
    <header class="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
      <div class="flex items-center gap-2">
        <h1 class="text-sm font-semibold tracking-wide">ZipMould Visualizer</h1>
        <button
          type="button"
          data-test="open-intro"
          class="grid h-6 w-6 place-items-center rounded-full text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
          aria-label="About ZipMould Visualizer"
          title="About ZipMould Visualizer"
          @click="intro.show"
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
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
        </button>
      </div>
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

    <footer
      class="flex items-center justify-between gap-3 border-t border-zinc-800 bg-zinc-950 px-4 py-1.5 text-[10px] leading-none text-zinc-500"
    >
      <span class="font-mono tracking-wide text-zinc-100/30">v{{ appVersion }}</span>
      <div class="flex items-center gap-3">
        <span data-test="copyright">
          &copy; 2026&ndash;{{ currentYear }} Gabriel Mitelman Tkacz &middot; MIT License
        </span>
        <a
          :href="sourceCodeUrl"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View source on GitHub"
          title="View source on GitHub"
          class="inline-flex items-center justify-center rounded p-0.5 text-zinc-400 transition hover:text-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            class="h-4 w-4"
            fill="currentColor"
          >
            <path
              d="M12 .5C5.65.5.5 5.65.5 12.02c0 5.1 3.29 9.42 7.86 10.95.57.1.78-.25.78-.55 0-.27-.01-.99-.01-1.94-3.2.7-3.87-1.37-3.87-1.37-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.72-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.17.91-.25 1.89-.38 2.86-.38.97 0 1.95.13 2.86.38 2.18-1.48 3.14-1.17 3.14-1.17.62 1.58.23 2.75.11 3.04.74.8 1.18 1.82 1.18 3.08 0 4.42-2.69 5.39-5.26 5.68.41.36.78 1.06.78 2.13 0 1.54-.01 2.78-.01 3.16 0 .31.21.66.79.55C20.21 21.43 23.5 17.12 23.5 12.02 23.5 5.65 18.35.5 12 .5Z"
            />
          </svg>
        </a>
      </div>
    </footer>

    <ControlBar />
    <ErrorToasts />
    <IntroModal :open="intro.open.value" @close="intro.dismiss" />
    <SmallScreenWarning />
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
import IntroModal from './components/IntroModal.vue'
import SmallScreenWarning from './components/SmallScreenWarning.vue'
import { useTraceStore } from './stores/trace'
import { api } from './api/client'
import { usePlaybackLoop } from './composables/usePlaybackLoop'
import { useFirstRunGuide } from './composables/useFirstRunGuide'

usePlaybackLoop()

const traceStore = useTraceStore()
const { trace, traceId } = storeToRefs(traceStore)
const downloadUrl = computed(() => (traceId.value ? api.downloadTraceUrl(traceId.value) : '#'))
const appVersion = __APP_VERSION__
const intro = useFirstRunGuide()
const currentYear = new Date().getFullYear()
const sourceCodeUrl = 'https://github.com/gtkacz/slime-mould'
</script>
