<template>
  <div class="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
    <div
      v-for="n in store.items"
      :key="n.id"
      :class="[
        'rounded px-4 py-2 shadow text-sm',
        n.kind === 'error' ? 'bg-red-700 text-white' : 'bg-zinc-700 text-zinc-100',
      ]"
      @click="store.dismiss(n.id)"
    >
      {{ n.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNotificationsStore } from '../stores/notifications'

const store = useNotificationsStore()
</script>
