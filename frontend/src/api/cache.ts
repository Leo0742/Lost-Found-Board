type CacheEntry<T> = {
  value?: T
  inFlight?: Promise<T>
  expiresAt: number
}

const cache = new Map<string, CacheEntry<unknown>>()

export const cachedCall = async <T>(key: string, ttlMs: number, loader: () => Promise<T>): Promise<T> => {
  const now = Date.now()
  const entry = cache.get(key) as CacheEntry<T> | undefined
  if (entry?.value !== undefined && entry.expiresAt > now) return entry.value
  if (entry?.inFlight) return entry.inFlight

  const inFlight = loader().then((value) => {
    cache.set(key, { value, expiresAt: Date.now() + ttlMs })
    return value
  }).finally(() => {
    const current = cache.get(key) as CacheEntry<T> | undefined
    if (current?.inFlight) cache.set(key, { value: current.value, expiresAt: current.expiresAt })
  })

  cache.set(key, { ...entry, inFlight, expiresAt: entry?.expiresAt ?? 0 })
  return inFlight
}

export const invalidateCache = (prefix: string) => {
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) cache.delete(key)
  }
}
