const origin = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '')

export async function api(path, options = {}) {
  const { signal, ...request } = options
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (signal?.aborted) abort()
  signal?.addEventListener('abort', abort, { once: true })
  let timedOut = false
  const timeout = setTimeout(() => { timedOut = true; abort() }, 90_000)
  try {
    const response = await fetch(`${origin}/api/v1${path}`, {
      ...request,
      headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...options.headers },
      signal: controller.signal, cache: 'no-store',
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}). Please retry.`
      throw new Error(detail)
    }
    return data
  } catch (failure) {
    if (timedOut) throw new Error('This request took too long. Please retry.')
    throw failure
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', abort)
  }
}

export const statusLabels = { uploaded: 'Waiting to process', parsing: 'Reading your book', chunking: 'Organizing passages', embedding: 'Preparing for questions', ready: 'Ready to read', error: 'Needs attention' }
export const processing = status => ['parsing', 'chunking', 'embedding'].includes(status)
