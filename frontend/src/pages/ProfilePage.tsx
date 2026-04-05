import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ProfileAddress,
  ProfileContactMethod,
  UserProfile,
  fetchMyProfile,
  generateLinkCode,
  getAuthMe,
  unlinkTelegram,
  updateMyProfile,
} from '../api/items'
import { EmptyState, LoadingGrid, SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

const YANDEX_MAPS_API_KEY = __YANDEX_MAPS_API_KEY__
const YANDEX_MAPS_SUGGEST_API_KEY = __YANDEX_MAPS_SUGGEST_API_KEY__

const randomCustomId = () => `custom-${Math.random().toString(36).slice(2, 10)}`
const randomAddressId = () => `addr-${Math.random().toString(36).slice(2, 10)}`

const normalizeAvatarUrl = (value?: string | null) => {
  if (!value) return null
  if (value.startsWith('/media/')) return value
  if (/^https?:\/\//i.test(value)) {
    try {
      const parsed = new URL(value)
      if (parsed.pathname.startsWith('/media/')) return parsed.pathname
      return value
    } catch {
      return value
    }
  }
  return `/media/${value.replace(/^\/+/, '')}`
}

type MapPickerResult = {
  address_text: string
  latitude?: number | null
  longitude?: number | null
}

declare global {
  interface Window {
    ymaps?: {
      ready: (cb: () => void) => void
      Map: new (el: HTMLElement, state: unknown) => {
        events: { add: (name: string, cb: (event: { get: (key: string) => { getCoordinates: () => number[] } }) => void) => void }
        geoObjects: { removeAll: () => void; add: (obj: unknown) => void }
        setCenter: (coords: number[], zoom?: number) => void
      }
      Placemark: new (coords: number[]) => unknown
    }
  }
}

const useYandexSuggest = (query: string) => {
  const [items, setItems] = useState<string[]>([])
  useEffect(() => {
    if (!YANDEX_MAPS_SUGGEST_API_KEY || query.trim().length < 3) {
      setItems([])
      return
    }
    const controller = new AbortController()
    const timeout = window.setTimeout(async () => {
      try {
        const url = new URL('https://suggest-maps.yandex.ru/v1/suggest')
        url.searchParams.set('apikey', YANDEX_MAPS_SUGGEST_API_KEY)
        url.searchParams.set('text', query.trim())
        url.searchParams.set('lang', 'en_US')
        url.searchParams.set('results', '5')
        const response = await fetch(url.toString(), { signal: controller.signal })
        if (!response.ok) return
        const data = await response.json() as { results?: Array<{ title?: { text?: string }; subtitle?: { text?: string } }> }
        const next = (data.results ?? []).map((entry) => [entry.title?.text, entry.subtitle?.text].filter(Boolean).join(', ').trim()).filter(Boolean)
        setItems(next)
      } catch {
        setItems([])
      }
    }, 280)
    return () => {
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [query])
  return items
}

const MapAddressPicker = ({ onClose, onSelect }: { onClose: () => void; onSelect: (result: MapPickerResult) => void }) => {
  const mapRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<{
    events: { add: (name: string, cb: (event: { get: (key: string) => unknown }) => void) => void }
    geoObjects: { removeAll: () => void; add: (obj: unknown) => void }
    setCenter: (coords: number[], zoom?: number) => void
  } | null>(null)
  const [selected, setSelected] = useState<MapPickerResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [resolving, setResolving] = useState(false)

  const formatReadableAddress = (meta?: { Address?: { Components?: Array<{ kind?: string; name?: string }> }; text?: string }) => {
    const components = meta?.Address?.Components ?? []
    const find = (kinds: string[]) => components.find((row) => row.kind && kinds.includes(row.kind))?.name?.trim()
    const city = find(['locality', 'province', 'area']) ?? ''
    const street = find(['street']) ?? ''
    const house = find(['house']) ?? find(['premise']) ?? ''
    const compact = [city, street, house].filter(Boolean).join(', ')
    return compact || meta?.text || null
  }

  const resolvePoint = async (coords: [number, number]) => {
    setResolving(true)
    setError(null)
    try {
      const url = new URL('https://geocode-maps.yandex.ru/1.x/')
      url.searchParams.set('apikey', YANDEX_MAPS_API_KEY)
      url.searchParams.set('format', 'json')
      url.searchParams.set('geocode', `${coords[1]},${coords[0]}`)
      url.searchParams.set('results', '6')
      const response = await fetch(url.toString())
      if (!response.ok) throw new Error('geocode-failed')
      const payload = await response.json() as {
        response?: {
          GeoObjectCollection?: {
            featureMember?: Array<{
              GeoObject?: {
                metaDataProperty?: { GeocoderMetaData?: { text?: string; precision?: string; Address?: { Components?: Array<{ kind?: string; name?: string }> } } }
              }
            }>
          }
        }
      }
      const members = payload.response?.GeoObjectCollection?.featureMember ?? []
      const houseFirst = members.find((item) => {
        const parts = item.GeoObject?.metaDataProperty?.GeocoderMetaData?.Address?.Components ?? []
        return parts.some((part) => part.kind === 'house')
      }) ?? members[0]
      const geoMeta = houseFirst?.GeoObject?.metaDataProperty?.GeocoderMetaData
      const formatted = formatReadableAddress(geoMeta)
      if (!formatted) throw new Error('no-address')
      setSelected({ address_text: formatted, latitude: coords[0], longitude: coords[1] })
    } catch {
      setError('Could not resolve this point to a real address. Try another building or type manually.')
      setSelected(null)
    } finally {
      setResolving(false)
    }
  }

  useEffect(() => {
    if (!YANDEX_MAPS_API_KEY || !mapRef.current) return
    const mountMap = () => {
      if (!window.ymaps || !mapRef.current) return
      const map = new window.ymaps.Map(mapRef.current, { center: [55.751244, 37.618423], zoom: 14 })
      mapInstanceRef.current = map
      map.events.add('click', async (event) => {
        const rawCoords = event.get('coords') as unknown
        if (!Array.isArray(rawCoords) || rawCoords.length < 2) return
        const coords: [number, number] = [Number(rawCoords[0]), Number(rawCoords[1])]
        if (!Number.isFinite(coords[0]) || !Number.isFinite(coords[1])) return
        map.geoObjects.removeAll()
        map.geoObjects.add(new window.ymaps!.Placemark(coords))
        await resolvePoint(coords)
      })
    }

    if (!window.ymaps) {
      const script = document.createElement('script')
      script.src = `https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(YANDEX_MAPS_API_KEY)}&lang=en_US`
      script.async = true
      script.onload = () => window.ymaps?.ready(mountMap)
      script.onerror = () => setError('Could not load Yandex Maps. Manual mode is still available.')
      document.body.appendChild(script)
      return
    }
    window.ymaps.ready(mountMap)
  }, [])

  const useGeolocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.')
      return
    }
    navigator.geolocation.getCurrentPosition((position) => {
      const coords: [number, number] = [position.coords.latitude, position.coords.longitude]
      const map = mapInstanceRef.current
      map?.setCenter(coords, 17)
      map?.geoObjects.removeAll()
      map?.geoObjects.add(new window.ymaps!.Placemark(coords))
      void resolvePoint(coords)
    }, () => setError('Unable to get your location.'))
  }

  return (
    <div className="profile-address-modal-backdrop">
      <div className="profile-address-modal">
        <h3>Select address on map</h3>
        {!YANDEX_MAPS_API_KEY ? <p className="notice">Set YANDEX_MAPS_API_KEY in .env to enable map selection.</p> : null}
        <div ref={mapRef} className="profile-map" />
        <div className="actions-row">
          <button type="button" className="button-neutral button-sm" onClick={useGeolocation}>Use geolocation</button>
          <button type="button" className="button-neutral button-sm" onClick={onClose}>Cancel</button>
          <button type="button" className="button-sm" disabled={!selected?.address_text || resolving} onClick={() => selected && onSelect(selected)}>Use selected address</button>
        </div>
        {resolving ? <p className="subtle">Resolving address…</p> : null}
        {selected?.address_text ? <p className="subtle">Selected: {selected.address_text}</p> : <p className="subtle">Click a building/house on map to resolve city, street, house.</p>}
        {error ? <p className="notice error">{error}</p> : null}
      </div>
    </div>
  )
}

export const ProfilePage = () => {
  const { t } = useSettings()
  const [loading, setLoading] = useState(true)
  const [linked, setLinked] = useState(false)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [displayName, setDisplayName] = useState('')
  const [customContacts, setCustomContacts] = useState<ProfileContactMethod[]>([])
  const [visibilityMode, setVisibilityMode] = useState<'all' | 'one'>('all')
  const [visibilityMethodId, setVisibilityMethodId] = useState<string>('')

  const [addresses, setAddresses] = useState<ProfileAddress[]>([])
  const [addressVisibilityMode, setAddressVisibilityMode] = useState<'all' | 'one'>('all')
  const [addressVisibilityId, setAddressVisibilityId] = useState<string>('')

  const [showAddContact, setShowAddContact] = useState(false)
  const [newContactName, setNewContactName] = useState('')
  const [newContactValue, setNewContactValue] = useState('')

  const [showAddAddress, setShowAddAddress] = useState(false)
  const [showMapPicker, setShowMapPicker] = useState(false)
  const [addressLabel, setAddressLabel] = useState('')
  const [addressText, setAddressText] = useState('')
  const [addressExtra, setAddressExtra] = useState('')
  const [addressLat, setAddressLat] = useState<number | null>(null)
  const [addressLon, setAddressLon] = useState<number | null>(null)
  const suggestions = useYandexSuggest(addressText)

  const applyProfile = (next: UserProfile) => {
    setProfile(next)
    setDisplayName(next.display_name ?? '')
    setCustomContacts((next.contact_methods ?? []).filter((row) => row.id !== 'telegram'))
    setVisibilityMode(next.contact_visibility === 'one' ? 'one' : 'all')
    setVisibilityMethodId(next.contact_visibility_method_id ?? '')
    setAddresses(next.profile_addresses ?? [])
    setAddressVisibilityMode(next.address_visibility === 'one' ? 'one' : 'all')
    setAddressVisibilityId(next.address_visibility_address_id ?? '')
  }

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const me = await getAuthMe({ forceRefresh: true })
      setLinked(me.linked)
      if (!me.linked) {
        setProfile(null)
        return
      }
      applyProfile(await fetchMyProfile({ bypassCache: true }))
    } catch {
      setError(t('profile.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const allMethods = useMemo(() => {
    const telegram = profile?.telegram_username
      ? [{ id: 'telegram', name: 'Telegram', value: `@${String(profile.telegram_username).replace(/^@/, '')}` }]
      : []
    return [...telegram, ...customContacts]
  }, [customContacts, profile?.telegram_username])

  const dirty = useMemo(() => {
    if (!profile) return false
    const originalCustom = (profile.contact_methods ?? []).filter((row) => row.id !== 'telegram')
    return (
      displayName !== (profile.display_name ?? '')
      || JSON.stringify(customContacts) !== JSON.stringify(originalCustom)
      || visibilityMode !== (profile.contact_visibility === 'one' ? 'one' : 'all')
      || (visibilityMode === 'one' && visibilityMethodId !== (profile.contact_visibility_method_id ?? ''))
      || JSON.stringify(addresses) !== JSON.stringify(profile.profile_addresses ?? [])
      || addressVisibilityMode !== (profile.address_visibility === 'one' ? 'one' : 'all')
      || (addressVisibilityMode === 'one' && addressVisibilityId !== (profile.address_visibility_address_id ?? ''))
    )
  }, [addresses, addressVisibilityId, addressVisibilityMode, customContacts, displayName, profile, visibilityMethodId, visibilityMode])

  const onSave = async (event: FormEvent) => {
    event.preventDefault()
    if (!dirty) return
    setError(null)
    setMessage(null)
    try {
      const next = await updateMyProfile({
        display_name: displayName,
        pickup_location: addresses[0]?.address_text ?? null,
        contact_methods: customContacts,
        contact_visibility: visibilityMode,
        contact_visibility_method_id: visibilityMode === 'one' ? visibilityMethodId || null : null,
        profile_addresses: addresses,
        address_visibility: addressVisibilityMode,
        address_visibility_address_id: addressVisibilityMode === 'one' ? addressVisibilityId || null : null,
        preferred_contact_method: null,
        preferred_contact_details: null,
      })
      applyProfile(next)
      setMessage(t('profile.saved'))
    } catch {
      setError(t('profile.saveFailed'))
    }
  }

  const addManualAddress = () => {
    const label = addressLabel.trim() || 'Address'
    const text = addressText.trim()
    if (!text) return
    setAddresses((prev) => [...prev, { id: randomAddressId(), label, address_text: text, latitude: addressLat, longitude: addressLon, extra_details: addressExtra.trim() || null }])
    setAddressLabel('')
    setAddressText('')
    setAddressExtra('')
    setAddressLat(null)
    setAddressLon(null)
    setShowAddAddress(false)
  }

  return (
    <section className="stack">
      {loading ? <LoadingGrid count={2} /> : null}
      {error ? <p className="notice error">{error}</p> : null}
      {message ? <p className="notice success">{message}</p> : null}

      {!loading && linked && profile ? (
        <section className="dashboard-block stack profile-identity-card">
          <form className="form stack" onSubmit={onSave}>
            <div className="profile-identity compact">
              {normalizeAvatarUrl(profile?.telegram_avatar_url || profile?.avatar_url)
                ? <img className="profile-avatar" src={normalizeAvatarUrl(profile?.telegram_avatar_url || profile?.avatar_url) ?? ''} alt={displayName || 'avatar'} />
                : <div className="profile-avatar profile-avatar-fallback" aria-hidden="true">U</div>}
              <div className="profile-identity-text stack" style={{ gap: '.25rem' }}>
                <strong>{displayName || profile.telegram_display_name || profile.telegram_username || t('profile.unknown')}</strong>
                <span className="subtle">{profile.telegram_username ? `@${String(profile.telegram_username).replace(/^@/, '')}` : t('profile.noUsername')}</span>
              </div>
              <button className="button-neutral button-sm" type="button" onClick={async () => { await unlinkTelegram(); await load() }}>{t('profile.unlink')}</button>
            </div>

            <label>{t('profile.displayName')}<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={120} /></label>

            <div className="stack compact-stack">
              <strong>Saved addresses</strong>
              {(addresses.length === 0) ? <p className="subtle">No saved addresses yet.</p> : null}
              {addresses.map((row) => (
                <div className="profile-contact-row" key={row.id}>
                  <span><strong>{row.label}</strong> <span className="subtle">{row.address_text}</span>{row.extra_details ? <span className="subtle"> · {row.extra_details}</span> : null}</span>
                  <button
                    type="button"
                    className="button-neutral button-sm"
                    onClick={() => {
                      setAddresses((prev) => prev.filter((entry) => entry.id !== row.id))
                      if (addressVisibilityId === row.id) {
                        setAddressVisibilityMode('all')
                        setAddressVisibilityId('')
                      }
                    }}
                  >
                    Remove
                  </button>
                </div>
              ))}

              {!showAddAddress ? (
                <button className="button-neutral button-sm" type="button" onClick={() => setShowAddAddress(true)}>Add another address</button>
              ) : (
                <div className="stack profile-add-address-inline">
                  <label>Label<input value={addressLabel} maxLength={40} placeholder="Home, Dorm, Work" onChange={(e) => setAddressLabel(e.target.value)} /></label>
                  <label>Address text
                    <input value={addressText} maxLength={255} placeholder="Type address manually" list="yandex-suggest" onChange={(e) => setAddressText(e.target.value)} />
                    <datalist id="yandex-suggest">{suggestions.map((entry) => <option key={entry} value={entry} />)}</datalist>
                  </label>
                  <label>Extra details (optional)
                    <textarea value={addressExtra} maxLength={500} rows={2} placeholder="Apartment, entrance, floor, comment" onChange={(e) => setAddressExtra(e.target.value)} />
                  </label>
                  <div className="actions-row">
                    <button type="button" className="button-neutral button-sm" onClick={() => setShowMapPicker(true)} disabled={!YANDEX_MAPS_API_KEY}>Select on map</button>
                    <button type="button" className="button-sm" onClick={addManualAddress}>Save address</button>
                    <button type="button" className="button-neutral button-sm" onClick={() => setShowAddAddress(false)}>Cancel</button>
                  </div>
                  {!YANDEX_MAPS_API_KEY ? <p className="subtle">Map/geocoder disabled until YANDEX_MAPS_API_KEY is configured.</p> : null}
                  {YANDEX_MAPS_API_KEY && !YANDEX_MAPS_SUGGEST_API_KEY ? <p className="subtle">Autocomplete is optional. Add YANDEX_MAPS_SUGGEST_API_KEY to enable suggestions.</p> : null}
                </div>
              )}

              <label>Address visibility
                <select value={addressVisibilityMode} onChange={(event) => setAddressVisibilityMode(event.target.value as 'all' | 'one')}>
                  <option value="all">Expose all addresses</option>
                  <option value="one">Expose one address</option>
                </select>
              </label>
              {addressVisibilityMode === 'one' ? (
                <label>Exposed address
                  <select value={addressVisibilityId} onChange={(event) => setAddressVisibilityId(event.target.value)}>
                    <option value="">Select address</option>
                    {addresses.map((row) => <option key={row.id} value={row.id}>{row.label}: {row.address_text}</option>)}
                  </select>
                </label>
              ) : null}
            </div>

            <div className="stack compact-stack">
              <strong>{t('profile.contactPrefs')}</strong>
              {allMethods.map((row) => (
                <div className="profile-contact-row" key={row.id}>
                  <span><strong>{row.name}</strong> <span className="subtle">{row.value}</span></span>
                  {row.id !== 'telegram' ? <button type="button" className="button-neutral button-sm" onClick={() => setCustomContacts((prev) => prev.filter((entry) => entry.id !== row.id))}>Remove</button> : <span className="badge approved">Linked</span>}
                </div>
              ))}

              {!showAddContact ? <button className="button-neutral button-sm" type="button" onClick={() => setShowAddContact(true)}>Add another contact method</button> : (
                <div className="profile-add-contact-inline">
                  <input value={newContactName} maxLength={40} placeholder="Contact name" onChange={(e) => setNewContactName(e.target.value)} />
                  <input value={newContactValue} maxLength={255} placeholder="Contact value" onChange={(e) => setNewContactValue(e.target.value)} />
                  <button
                    type="button"
                    className="button-sm"
                    onClick={() => {
                      const name = newContactName.trim()
                      const value = newContactValue.trim()
                      if (!name || !value) return
                      setCustomContacts((prev) => [...prev, { id: randomCustomId(), name, value }])
                      setNewContactName('')
                      setNewContactValue('')
                      setShowAddContact(false)
                    }}
                  >Add</button>
                </div>
              )}

              <label>Contact visibility
                <select value={visibilityMode} onChange={(event) => setVisibilityMode(event.target.value as 'all' | 'one')}>
                  <option value="all">Expose all contacts</option>
                  <option value="one">Expose one contact</option>
                </select>
              </label>
              {visibilityMode === 'one' ? (
                <label>Exposed contact
                  <select value={visibilityMethodId} onChange={(event) => setVisibilityMethodId(event.target.value)}>
                    <option value="">Select contact</option>
                    {allMethods.map((row) => <option key={row.id} value={row.id}>{row.name}: {row.value}</option>)}
                  </select>
                </label>
              ) : null}
            </div>

            {dirty ? <button type="submit">{t('profile.save')}</button> : null}
          </form>
          {showMapPicker ? (
            <MapAddressPicker
              onClose={() => setShowMapPicker(false)}
              onSelect={(result) => {
                setAddressText(result.address_text)
                setAddressLat(result.latitude ?? null)
                setAddressLon(result.longitude ?? null)
                setShowMapPicker(false)
                setShowAddAddress(true)
              }}
            />
          ) : null}
        </section>
      ) : null}

      {!loading && !linked ? (
        <SectionCard title={t('profile.telegram')}>
          <div className="stack compact-stack">
            <button type="button" className="button-sm" onClick={async () => {
              const generated = await generateLinkCode()
              setLinkCode(generated.code)
            }}>{t('profile.generateCopy')}</button>
            {linkCode ? <code className="profile-link-command">/link {linkCode}</code> : null}
          </div>
          <EmptyState title={t('profile.linkToEditTitle')} subtitle={t('profile.linkToEditSub')} action={<Link to="/"><button type="button" className="button-neutral">{t('nav.items')}</button></Link>} />
        </SectionCard>
      ) : null}
    </section>
  )
}
