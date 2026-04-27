import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePlaybackStore } from '../playback'

describe('playback store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('clamps the frame index to [0, total-1]', () => {
    const s = usePlaybackStore()
    s.setTotal(10)
    s.seek(-5)
    expect(s.index).toBe(0)
    s.seek(99)
    expect(s.index).toBe(9)
  })

  it('step advances by one within bounds', () => {
    const s = usePlaybackStore()
    s.setTotal(3)
    s.step(1)
    s.step(1)
    s.step(1)
    expect(s.index).toBe(2)
    s.step(-1)
    expect(s.index).toBe(1)
  })

  it('toggles play and clamps speed values', () => {
    const s = usePlaybackStore()
    expect(s.playing).toBe(false)
    s.togglePlay()
    expect(s.playing).toBe(true)
    s.setSpeed(0)
    expect(s.speed).toBe(s.MIN_SPEED)
    s.setSpeed(0.5)
    expect(s.speed).toBe(0.5)
    s.setSpeed(99999)
    expect(s.speed).toBeLessThanOrEqual(s.MAX_SPEED)
  })

  it('restarts from the first frame when play is pressed at the end', () => {
    const s = usePlaybackStore()
    s.setTotal(3)
    s.seek(2)

    s.togglePlay()

    expect(s.index).toBe(0)
    expect(s.playing).toBe(true)
  })

  it('layer visibility flags default to true and toggle', () => {
    const s = usePlaybackStore()
    expect(s.layers.pheromone).toBe(true)
    s.toggleLayer('pheromone')
    expect(s.layers.pheromone).toBe(false)
  })

  it('tracks the hovered walker id', () => {
    const s = usePlaybackStore()
    expect(s.hoveredWalkerId).toBeNull()
    s.setHoveredWalkerId(4)
    expect(s.hoveredWalkerId).toBe(4)
    s.setHoveredWalkerId(null)
    expect(s.hoveredWalkerId).toBeNull()
  })
})
