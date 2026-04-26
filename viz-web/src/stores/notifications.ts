import { defineStore } from 'pinia'
import { ref } from 'vue'

export type NotificationKind = 'info' | 'error'

export interface Notification {
  id: number
  kind: NotificationKind
  text: string
}

const MAX_ITEMS = 5

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])
  let nextId = 1

  function push(input: Omit<Notification, 'id'>): number {
    const id = nextId++
    items.value.push({ id, ...input })
    while (items.value.length > MAX_ITEMS) items.value.shift()
    return id
  }

  function dismiss(id: number): void {
    items.value = items.value.filter((n) => n.id !== id)
  }

  return { items, push, dismiss }
})
