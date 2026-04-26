<template>
  <span class="inline-flex">
    <button
      :id="buttonId"
      ref="reference"
      type="button"
      class="inline-flex h-4 w-4 items-center justify-center text-zinc-500 hover:text-zinc-100"
      :aria-describedby="open ? tooltipId : undefined"
      :aria-label="label"
      @mouseenter="open = true"
      @mouseleave="open = false"
      @focus="open = true"
      @blur="open = false"
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
        <path d="M9.1 9a3 3 0 1 1 5.8 1c-.4.8-1 1.2-1.7 1.7-.7.5-1.2 1-1.2 2.3" />
        <path d="M12 17h.01" />
      </svg>
    </button>
    <Teleport to="body">
      <div
        v-if="open"
        :id="tooltipId"
        ref="floating"
        role="tooltip"
        class="z-50 max-w-64 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs leading-snug text-zinc-100 shadow"
        :style="floatingStyles"
      >
        {{ text }}
      </div>
    </Teleport>
  </span>
</template>

<script setup lang="ts">
import { flip, offset, shift, useFloating, autoUpdate } from '@floating-ui/vue'
import { ref } from 'vue'

defineProps<{
  text: string
  label: string
}>()

const open = ref(false)
const reference = ref<HTMLElement | null>(null)
const floating = ref<HTMLElement | null>(null)
const id = Math.random().toString(36).slice(2)
const buttonId = `help-button-${id}`
const tooltipId = `help-tooltip-${id}`

const { floatingStyles } = useFloating(reference, floating, {
  placement: 'right',
  whileElementsMounted: autoUpdate,
  middleware: [offset(8), flip(), shift({ padding: 8 })],
})
</script>
