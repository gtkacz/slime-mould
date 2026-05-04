<template>
  <Teleport to="body">
    <div
      v-if="visible"
      data-test="small-screen-warning"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-950/95 px-6 py-8"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="small-screen-title"
    >
      <section
        class="w-full max-w-md rounded border border-zinc-800 bg-zinc-900 p-6 text-zinc-100 shadow-xl"
      >
        <div class="mb-4 flex items-center gap-3">
          <span
            aria-hidden="true"
            class="grid h-9 w-9 place-items-center rounded-full bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/25"
          >
            <svg
              viewBox="0 0 24 24"
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
              <path
                d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
              />
            </svg>
          </span>
          <h2 id="small-screen-title" class="text-base font-semibold tracking-wide">
            Small screen detected
          </h2>
        </div>
        <p class="text-sm leading-relaxed text-zinc-300">
          ZipMould Visualizer was designed for desktop-class displays. On phones and small tablets,
          panels overflow, the canvas shrinks below readability, and several controls become
          unreachable.
        </p>
        <p class="mt-3 text-sm leading-relaxed text-zinc-400">
          Please open this page on a laptop or larger screen for the intended experience.
        </p>
        <div class="mt-6 flex justify-end">
          <button
            type="button"
            data-test="small-screen-dismiss"
            class="rounded bg-zinc-800 px-3 py-1.5 text-xs text-zinc-200 transition hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500"
            @click="dismiss"
          >
            Continue anyway
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useViewport } from '../composables/useViewport'

const { isSmall } = useViewport()
const dismissed = ref(false)
const visible = computed(() => isSmall.value && !dismissed.value)

watch(isSmall, (small) => {
  if (!small) dismissed.value = false
})

function dismiss(): void {
  dismissed.value = true
}
</script>
