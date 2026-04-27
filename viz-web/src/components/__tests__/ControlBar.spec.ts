import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ControlBar from '../ControlBar.vue'
import { usePlaybackStore } from '../../stores/playback'

describe('ControlBar', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('toggles play state when play button clicked', async () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const wrapper = mount(ControlBar)
    await wrapper.get('[data-test="play"]').trigger('click')
    expect(store.playing).toBe(true)
    await wrapper.get('[data-test="play"]').trigger('click')
    expect(store.playing).toBe(false)
  })

  it('steps forward and backward', async () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const wrapper = mount(ControlBar)
    await wrapper.get('[data-test="step-fwd"]').trigger('click')
    expect(store.index).toBe(1)
    await wrapper.get('[data-test="step-back"]').trigger('click')
    expect(store.index).toBe(0)
  })

  it('scrubs via the range input', async () => {
    const store = usePlaybackStore()
    store.setTotal(10)
    const wrapper = mount(ControlBar)
    const input = wrapper.get<HTMLInputElement>('[data-test="scrub"]')
    input.element.value = '5'
    await input.trigger('input')
    expect(store.index).toBe(5)
  })

  it('previews playback duration from total frames and fps', async () => {
    const store = usePlaybackStore()
    store.setTotal(121)
    store.setSpeed(4)
    const wrapper = mount(ControlBar)

    expect(wrapper.get('[data-test="duration-preview"]').text()).toBe('30 s')

    store.setSpeed(16)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-test="duration-preview"]').text()).toBe('7.5 s')
  })
})
