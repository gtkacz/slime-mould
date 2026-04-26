import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationsStore } from '../notifications'

describe('notifications store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('pushes and dismisses messages', () => {
    const store = useNotificationsStore()
    const id = store.push({ kind: 'error', text: 'boom' })
    expect(store.items).toHaveLength(1)
    store.dismiss(id)
    expect(store.items).toHaveLength(0)
  })

  it('caps at 5 messages, dropping the oldest', () => {
    const store = useNotificationsStore()
    for (let i = 0; i < 7; i++) store.push({ kind: 'info', text: `n${i}` })
    expect(store.items).toHaveLength(5)
    expect(store.items[0]?.text).toBe('n2')
  })
})
