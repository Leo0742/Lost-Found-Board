import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ProfileContactMethod, fetchMyProfile, generateLinkCode, getAuthMe, unlinkTelegram, updateMyProfile, UserProfile } from '../api/items'
import { EmptyState, LoadingGrid, SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

const initialsFrom = (name?: string | null, fallback = 'U') => {
  if (!name) return fallback
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return fallback
  return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join('')
}

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

const randomCustomId = () => `custom-${Math.random().toString(36).slice(2, 10)}`

export const ProfilePage = () => {
  const { t } = useSettings()
  const [loading, setLoading] = useState(true)
  const [linked, setLinked] = useState(false)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const [displayName, setDisplayName] = useState('')
  const [pickupLocation, setPickupLocation] = useState('')
  const [customContacts, setCustomContacts] = useState<ProfileContactMethod[]>([])
  const [visibilityMode, setVisibilityMode] = useState<'all' | 'one'>('all')
  const [visibilityMethodId, setVisibilityMethodId] = useState<string>('')

  const [showAddContact, setShowAddContact] = useState(false)
  const [newContactName, setNewContactName] = useState('')
  const [newContactValue, setNewContactValue] = useState('')

  const applyProfile = (next: UserProfile) => {
    setProfile(next)
    setDisplayName(next.display_name ?? '')
    setPickupLocation(next.pickup_location ?? '')
    setCustomContacts((next.contact_methods ?? []).filter((row) => row.id !== 'telegram'))
    const nextVisibility = next.contact_visibility === 'one' ? 'one' : 'all'
    setVisibilityMode(nextVisibility)
    setVisibilityMethodId(next.contact_visibility_method_id ?? '')
  }

  const fetchProfileWithAvatarSync = async () => {
    let latest = await fetchMyProfile({ bypassCache: true })
    applyProfile(latest)
    if (latest.telegram_avatar_url || latest.avatar_url) return
    for (let attempt = 0; attempt < 4; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 1200))
      latest = await fetchMyProfile({ bypassCache: true })
      applyProfile(latest)
      if (latest.telegram_avatar_url || latest.avatar_url) return
    }
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

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1800)
    return () => window.clearTimeout(timer)
  }, [copied])

  useEffect(() => {
    if (!linkCode || linked) return
    const interval = window.setInterval(() => {
      void (async () => {
        try {
          const me = await getAuthMe({ forceRefresh: true })
          if (!me.linked) return
          setLinked(true)
          await fetchProfileWithAvatarSync()
          setLinkCode(null)
          setCopied(false)
          setMessage(t('profile.linkDetected'))
        } catch {
          // wait for link
        }
      })()
    }, 3000)
    return () => window.clearInterval(interval)
  }, [linkCode, linked, t])

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
      || pickupLocation !== (profile.pickup_location ?? '')
      || JSON.stringify(customContacts) !== JSON.stringify(originalCustom)
      || visibilityMode !== (profile.contact_visibility === 'one' ? 'one' : 'all')
      || (visibilityMode === 'one' && visibilityMethodId !== (profile.contact_visibility_method_id ?? ''))
    )
  }, [customContacts, displayName, pickupLocation, profile, visibilityMethodId, visibilityMode])

  const onSave = async (event: FormEvent) => {
    event.preventDefault()
    if (!dirty) return
    setError(null)
    setMessage(null)
    try {
      const payloadMethodId = visibilityMode === 'one' ? visibilityMethodId || null : null
      const next = await updateMyProfile({
        display_name: displayName,
        pickup_location: pickupLocation,
        contact_methods: customContacts,
        contact_visibility: visibilityMode,
        contact_visibility_method_id: payloadMethodId,
        preferred_contact_method: null,
        preferred_contact_details: null,
      })
      applyProfile(next)
      setMessage(t('profile.saved'))
    } catch {
      setError(t('profile.saveFailed'))
    }
  }

  const avatarFallback = useMemo(
    () => initialsFrom(displayName || profile?.telegram_display_name || profile?.telegram_username || undefined),
    [displayName, profile?.telegram_display_name, profile?.telegram_username],
  )
  const shownAvatarUrl = normalizeAvatarUrl(profile?.telegram_avatar_url || profile?.avatar_url)
  const linkCommand = linkCode ? `/link ${linkCode}` : null

  return (
    <section className="stack">
      {loading ? <LoadingGrid count={2} /> : null}
      {error ? <p className="notice error">{error}</p> : null}
      {message ? <p className="notice success">{message}</p> : null}

      {!loading && linked && profile ? (
        <section className="dashboard-block stack profile-identity-card">
          <form className="form stack" onSubmit={onSave}>
            <div className="profile-identity-shell">
              <button
                className="profile-unlink-icon-button"
                type="button"
                title={t('profile.unlink')}
                aria-label={t('profile.unlink')}
                onClick={async () => { await unlinkTelegram(); await load() }}
              >
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
                  <path d="M12 2a1 1 0 0 1 1 1v9a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm6.36 3.64a1 1 0 0 1 1.41 1.41A8.97 8.97 0 0 1 21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9c0-1.88.57-3.63 1.55-5.09a1 1 0 1 1 1.66 1.12A6.98 6.98 0 0 0 5 12a7 7 0 1 0 12.36-4.95Z" fill="currentColor" />
                </svg>
              </button>

              <div className="profile-identity compact">
                {shownAvatarUrl ? (
                  <img className="profile-avatar" src={shownAvatarUrl ?? ''} alt={displayName || 'avatar'} />
                ) : (
                  <div className="profile-avatar profile-avatar-fallback" aria-hidden="true">{avatarFallback}</div>
                )}
                <div className="profile-identity-text stack" style={{ gap: '.25rem' }}>
                  <strong>{displayName || profile.telegram_display_name || profile.telegram_username || t('profile.unknown')}</strong>
                  <span className="subtle">{profile.telegram_username ? `@${String(profile.telegram_username).replace(/^@/, '')}` : t('profile.noUsername')}</span>
                </div>
              </div>
            </div>

            <label>{t('profile.displayName')}
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={120} />
            </label>
            <label>{t('profile.pickupLocation')}
              <input value={pickupLocation} onChange={(event) => setPickupLocation(event.target.value)} maxLength={160} placeholder={t('profile.pickupPlaceholder')} />
            </label>

            <div className="stack compact-stack">
              <strong>{t('profile.contactPrefs')}</strong>
              {allMethods.map((row) => (
                <div className="profile-contact-row" key={row.id}>
                  <span><strong>{row.name}</strong> <span className="subtle">{row.value}</span></span>
                  {row.id !== 'telegram' ? (
                    <button
                      type="button"
                      className="button-neutral button-sm"
                      onClick={() => {
                        setCustomContacts((prev) => prev.filter((entry) => entry.id !== row.id))
                        if (visibilityMethodId === row.id) {
                          setVisibilityMode('all')
                          setVisibilityMethodId('')
                        }
                      }}
                    >
                      Remove
                    </button>
                  ) : <span className="badge approved">Linked</span>}
                </div>
              ))}

              {!showAddContact ? (
                <button className="button-neutral button-sm" type="button" onClick={() => setShowAddContact(true)}>Add another contact method</button>
              ) : (
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
                  >
                    Add
                  </button>
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
        </section>
      ) : null}

      {!loading && !linked ? (
        <SectionCard title={t('profile.telegram')}>
          <div className="profile-identity compact">
            <div className="profile-avatar profile-avatar-fallback" aria-hidden="true">U</div>
            <div className="stack" style={{ gap: '.25rem' }}>
              <strong>{t('profile.unknown')}</strong>
              <span className="subtle">{t('profile.noUsername')}</span>
            </div>
          </div>
          <div className="stack compact-stack">
            <div className="profile-link-code compact">
              <button type="button" className="button-sm" onClick={async () => {
                const generated = await generateLinkCode()
                const command = `/link ${generated.code}`
                setLinkCode(generated.code)
                setCopied(false)
                setMessage(null)
                try {
                  await navigator.clipboard.writeText(command)
                  setCopied(true)
                } catch {
                  // command visible for manual copy
                }
              }}>{t('profile.generateCopy')}</button>
              {linkCommand ? (
                <button type="button" className="button-neutral button-sm" onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(linkCommand)
                    setError(null)
                    setCopied(true)
                  } catch {
                    setError(t('profile.copyFailed'))
                  }
                }}>{copied ? t('profile.copied') : t('profile.copyCommand')}</button>
              ) : null}
            </div>
            {linkCommand ? <code className="profile-link-command">{linkCommand}</code> : null}
            {linkCommand ? <span className="subtle">{t('profile.waitingForLink')}</span> : null}
          </div>
          <EmptyState title={t('profile.linkToEditTitle')} subtitle={t('profile.linkToEditSub')} action={<Link to="/"><button type="button" className="button-neutral">{t('nav.items')}</button></Link>} />
        </SectionCard>
      ) : null}
    </section>
  )
}
