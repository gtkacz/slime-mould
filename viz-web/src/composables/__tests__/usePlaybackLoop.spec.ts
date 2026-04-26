import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePlaybackLoop } from '../usePlaybackLoop'
import { usePlaybackStore } from '../../stores/playback'

describe('usePlaybackLoop', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('advances index by speed per tick when playing', () => {
    const store = usePlaybackStore()
    store.setTotal(100)
    store.setSpeed(4)
    const loop = usePlaybackLoop()

    store.togglePlay()
    loop._tickForTesting()
    expect(store.index).toBe(4)
    loop._tickForTesting()
    expect(store.index).toBe(8)
  })

  it('stops at the last frame and pauses', () => {
    const store = usePlaybackStore()
    store.setTotal(3)
    store.setSpeed(8)
    const loop = usePlaybackLoop()

    store.togglePlay()
    loop._tickForTesting()
    expect(store.index).toBe(2)
    expect(store.playing).toBe(false)
  })

  it('does nothing when paused', () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const loop = usePlaybackLoop()
    loop._tickForTesting()
    expect(store.index).toBe(0)
  })

  it('treats speed as frames per second', () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    store.setSpeed(0.05)
    const loop = usePlaybackLoop()

    store.togglePlay()
    loop._tickForTesting(10_000)
    expect(store.index).toBe(0)
    loop._tickForTesting(10_000)
    expect(store.index).toBe(1)
  })
})
