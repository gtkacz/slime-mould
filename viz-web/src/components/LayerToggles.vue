<template>
  <section class="p-3 text-zinc-100 text-sm space-y-1">
    <h2 class="text-sm uppercase tracking-wide text-zinc-400 mb-2">Layers</h2>
    <label v-for="key in keys" :key="key" class="flex items-center gap-2 text-xs">
      <input
        type="checkbox"
        :checked="store.layers[key]"
        :data-test="`toggle-${key}`"
        @change="store.toggleLayer(key)"
      />
      {{ key }}
    </label>
  </section>
</template>

<script setup lang="ts">
import { usePlaybackStore, type LayerKey } from '../stores/playback'

const store = usePlaybackStore()
const keys: LayerKey[] = ['walls', 'pheromone', 'walkers', 'bestPath', 'waypoints']
</script>
