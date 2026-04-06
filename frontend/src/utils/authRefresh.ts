const AUTH_UPDATED_EVENT = 'lfb:auth-updated'

export const emitAuthUpdated = () => {
  window.dispatchEvent(new Event(AUTH_UPDATED_EVENT))
}

export const onAuthUpdated = (listener: () => void) => {
  const handler = () => listener()
  window.addEventListener(AUTH_UPDATED_EVENT, handler)
  return () => window.removeEventListener(AUTH_UPDATED_EVENT, handler)
}
