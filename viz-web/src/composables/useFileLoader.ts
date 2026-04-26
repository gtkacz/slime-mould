import { ApiClient, ApiError, api as defaultApi } from '../api/client'
import { useTraceStore } from '../stores/trace'
import { useNotificationsStore } from '../stores/notifications'

export function useFileLoader(client: ApiClient = defaultApi) {
  const traceStore = useTraceStore()
  const notifications = useNotificationsStore()

  async function load(file: File): Promise<void> {
    try {
      const resp = await client.uploadTrace(file)
      traceStore.set(resp.trace_id, resp.trace)
    } catch (err) {
      const text =
        err instanceof ApiError
          ? `${err.kind}: ${err.detail}`
          : err instanceof Error
            ? err.message
            : 'unknown error loading trace'
      notifications.push({ kind: 'error', text })
      throw err
    }
  }

  return { load }
}
