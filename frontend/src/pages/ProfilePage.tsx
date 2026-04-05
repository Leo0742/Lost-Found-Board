import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMyProfile, generateLinkCode, getAuthMe, unlinkTelegram, updateMyProfile, UserProfile } from '../api/items'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

const initialsFrom = (name?: string | null, fallback = 'U') => {
  if (!name) return fallback
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return fallback
  return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join('')
}

export const ProfilePage = () => {
  const { t, language, theme } = useSettings()
  const [loading, setLoading] = useState(true)
  const [linked, setLinked] = useState(false)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [role, setRole] = useState<'admin' | 'moderator' | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const [displayName, setDisplayName] = useState('')
  const [preferredContactMethod, setPreferredContactMethod] = useState('telegram')
  const [preferredContactDetails, setPreferredContactDetails] = useState('')
  const [pickupLocation, setPickupLocation] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const me = await getAuthMe({ forceRefresh: true })
      setLinked(me.linked)
      setRole(me.role ?? null)
      if (!me.linked) {
        setProfile(null)
        return
      }
      const meProfile = await fetchMyProfile({ bypassCache: true })
      setProfile(meProfile)
      setDisplayName(meProfile.display_name ?? '')
      setPreferredContactMethod(meProfile.preferred_contact_method ?? 'telegram')
      setPreferredContactDetails(meProfile.preferred_contact_details ?? '')
      setPickupLocation(meProfile.pickup_location ?? '')
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
          const meProfile = await fetchMyProfile({ bypassCache: true })
          setLinked(true)
          setRole(me.role ?? null)
          setProfile(meProfile)
          setDisplayName(meProfile.display_name ?? '')
          setPreferredContactMethod(meProfile.preferred_contact_method ?? 'telegram')
          setPreferredContactDetails(meProfile.preferred_contact_details ?? '')
          setPickupLocation(meProfile.pickup_location ?? '')
          setLinkCode(null)
          setCopied(false)
          setMessage(t('profile.linkDetected'))
        } catch {
          // keep polling until linked or code cleared
        }
      })()
    }, 3000)
    return () => window.clearInterval(interval)
  }, [linkCode, linked, t])

  const onSave = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)
    try {
      const next = await updateMyProfile({
        display_name: displayName,
        preferred_contact_method: preferredContactMethod,
        preferred_contact_details: preferredContactDetails,
        pickup_location: pickupLocation,
      })
      setProfile(next)
      setMessage(t('profile.saved'))
    } catch {
      setError(t('profile.saveFailed'))
    }
  }

  const avatarFallback = useMemo(
    () => initialsFrom(displayName || profile?.telegram_display_name || profile?.telegram_username || undefined),
    [displayName, profile?.telegram_display_name, profile?.telegram_username],
  )
  const shownAvatarUrl = profile?.telegram_avatar_url || profile?.avatar_url

  return (
    <section className="stack">
      <PageHero
        title={t('profile.title')}
        subtitle={t('profile.subtitle')}
        stats={[
          { label: t('profile.stats.telegram'), value: linked ? t('profile.linked') : t('profile.unlinked') },
          { label: t('profile.stats.language'), value: language === 'ru' ? 'Русский' : 'English' },
          { label: t('profile.stats.theme'), value: theme },
          { label: t('profile.stats.role'), value: role ?? 'member' },
        ]}
      />

      {loading ? <LoadingGrid count={3} /> : null}
      {error ? <p className="notice error">{error}</p> : null}
      {message ? <p className="notice success">{message}</p> : null}

      {!loading ? (
        <div className="layout-split">
          <SectionCard title={t('profile.identity')} subtitle={t('profile.identitySub')}>
            <div className="profile-identity">
              {shownAvatarUrl ? (
                <img className="profile-avatar" src={shownAvatarUrl ?? ''} alt={displayName || 'avatar'} />
              ) : (
                <div className="profile-avatar profile-avatar-fallback" aria-hidden="true">{avatarFallback}</div>
              )}
              <div className="stack" style={{ gap: '.35rem' }}>
                <strong>{displayName || profile?.telegram_display_name || profile?.telegram_username || t('profile.unknown')}</strong>
                <span className="subtle">{profile?.telegram_username ? `@${String(profile.telegram_username).replace(/^@/, '')}` : t('profile.noUsername')}</span>
                <span className={`badge ${linked ? 'approved' : 'pending'}`}>{linked ? t('profile.linked') : t('profile.unlinked')}</span>
              </div>
            </div>
          </SectionCard>

          <SectionCard title={t('profile.telegram')} subtitle={t('profile.telegramSub')}>
            {!linked ? (
              <div className="stack">
                <p className="subtle">{t('profile.telegramUnlinked')}</p>
                <button type="button" onClick={async () => {
                  const generated = await generateLinkCode()
                  setLinkCode(generated.code)
                  setCopied(false)
                  setMessage(null)
                }}>{t('profile.generateCode')}</button>
                {linkCode ? (
                  <div className="notice profile-link-code">
                    <span>{t('profile.sendCode')} <strong>/link {linkCode}</strong></span>
                    <button
                      type="button"
                      className="button-neutral"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(`/link ${linkCode}`)
                          setError(null)
                          setCopied(true)
                        } catch {
                          setError(t('profile.copyFailed'))
                        }
                      }}
                    >
                      {copied ? t('profile.copied') : t('profile.copyCommand')}
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="stack">
                <p className="subtle">{t('profile.telegramLinked')}</p>
                <p className="subtle">{profile?.telegram_username ? `@${String(profile.telegram_username).replace(/^@/, '')}` : t('profile.noUsername')}</p>
                <button className="button-danger" type="button" onClick={async () => { await unlinkTelegram(); await load() }}>{t('profile.unlink')}</button>
              </div>
            )}
          </SectionCard>
        </div>
      ) : null}

      {!loading && linked ? (
        <SectionCard title={t('profile.contactPrefs')} subtitle={t('profile.contactPrefsSub')}>
          <form className="form stack" onSubmit={onSave}>
            <label>{t('profile.displayName')}
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={120} />
            </label>
            <label>{t('profile.contactMethod')}
              <select value={preferredContactMethod} onChange={(event) => setPreferredContactMethod(event.target.value)}>
                <option value="telegram">Telegram</option>
                <option value="phone">Phone</option>
                <option value="email">Email</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            <label>{t('profile.contactDetails')}
              <input value={preferredContactDetails} onChange={(event) => setPreferredContactDetails(event.target.value)} maxLength={255} placeholder={t('profile.contactPlaceholder')} />
            </label>
            <label>{t('profile.pickupLocation')}
              <input value={pickupLocation} onChange={(event) => setPickupLocation(event.target.value)} maxLength={160} placeholder={t('profile.pickupPlaceholder')} />
            </label>
            <button type="submit">{t('profile.save')}</button>
          </form>
        </SectionCard>
      ) : null}

      {!loading && !linked ? (
        <EmptyState title={t('profile.linkToEditTitle')} subtitle={t('profile.linkToEditSub')} action={<Link to="/"><button type="button" className="button-neutral">{t('nav.items')}</button></Link>} />
      ) : null}
    </section>
  )
}
