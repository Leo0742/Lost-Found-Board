import { FormEvent, useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { Link, useNavigate } from 'react-router-dom'
import { createItem, uploadItemImage, getAuthMe, fetchCategories, suggestCategory, fetchMyProfile } from '../api/items'
import { ItemStatus } from '../types/item'
import { SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

const formatBackendValidationError = (error: unknown): string => {
  if (!axios.isAxiosError(error)) return 'Could not create item. Please review the form.'
  const detail = error.response?.data?.detail
  if (!Array.isArray(detail) || detail.length === 0) return 'Could not create item. Please review the form.'
  return detail.map((issue: { loc?: Array<string | number>; msg?: string }) => {
    const field = issue.loc?.[issue.loc.length - 1]
    return field && issue.msg ? `${String(field)}: ${issue.msg}` : null
  }).filter(Boolean).join('; ') || 'Could not create item. Please review the form.'
}

export const NewItemPage = () => {
  const { t } = useSettings()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('Accessories')
  const [location, setLocation] = useState('')
  const [status, setStatus] = useState<ItemStatus>('lost')
  const [contactName, setContactName] = useState('')
  const [telegramUsername, setTelegramUsername] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [categories, setCategories] = useState<string[]>(['Other'])
  const [profileAddresses, setProfileAddresses] = useState<Array<{ id: string; label: string; address_text: string }>>([])
  const [categoryHint, setCategoryHint] = useState<{ category: string; confidence: number } | null>(null)
  const navigate = useNavigate()

  const refreshAuthState = useCallback(async () => {
    const me = await getAuthMe({ forceRefresh: true })
    setLinkedUserId(me.identity?.telegram_user_id ?? null)
    if (me.identity?.telegram_username) {
      setTelegramUsername(`@${me.identity.telegram_username}`)
    }
    if (me.linked && me.identity?.telegram_user_id) {
      const profile = await fetchMyProfile()
      if (!contactName && profile.display_name) {
        setContactName(profile.display_name)
      }
      if (!location && profile.pickup_location) {
        setLocation(profile.pickup_location)
      }
      setProfileAddresses((profile.profile_addresses ?? []).map((row) => ({ id: row.id, label: row.label, address_text: row.address_text })))
      if (!telegramUsername && profile.telegram_username) {
        setTelegramUsername(`@${String(profile.telegram_username).replace(/^@/, '')}`)
      }
      const exposedContacts = profile.exposed_contact_methods ?? []
      if (!contactName && exposedContacts.length > 0) {
        const primary = exposedContacts[0]
        setContactName(`${primary.name}: ${primary.value}`.slice(0, 80))
      } else if (profile.preferred_contact_method && profile.preferred_contact_details && !contactName) {
        setContactName(`${profile.preferred_contact_method}: ${profile.preferred_contact_details}`.slice(0, 80))
      }
    }
  }, [contactName, location, telegramUsername])

  useEffect(() => {
    refreshAuthState().catch(() => setError(t('new.authInitFailed')))
    fetchCategories().then((data) => {
      if (data.length > 0) setCategories(data)
    }).catch(() => setCategories(['Other']))
  }, [refreshAuthState, t])

  useEffect(() => {
    const normalized = title.trim()
    if (normalized.length < 3) {
      setCategoryHint(null)
      return
    }
    const timer = setTimeout(() => {
      suggestCategory(normalized)
        .then((suggestion) => {
          setCategoryHint({ category: suggestion.category, confidence: suggestion.confidence })
          if (suggestion.confidence >= 0.45 && suggestion.category !== 'Other') {
            setCategory(suggestion.category)
          }
        })
        .catch(() => setCategoryHint(null))
    }, 260)
    return () => clearTimeout(timer)
  }, [title])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    if (!linkedUserId) return setError(t('new.connectFirst'))
    try {
      const item = await createItem({
        title: title.trim(),
        description: description.trim(),
        category: category.trim(),
        location: location.trim(),
        status,
        contact_name: contactName.trim(),
        telegram_username: telegramUsername.trim() || undefined,
        ...(photoFile ? await uploadItemImage(photoFile) : {}),
      })
      setSuccess(t('new.created'))
      setTimeout(() => navigate(`/items/${item.id}`), 450)
    } catch (err) {
      setError(formatBackendValidationError(err))
    }
  }

  return (
    <section className="stack">
      {!linkedUserId ? (
        <SectionCard title={t('new.profileRequiredTitle')} subtitle={t('new.profileRequiredSubtitle')}>
          <div className="actions-row">
            <Link to="/profile"><button type="button">{t('new.goProfile')}</button></Link>
          </div>
        </SectionCard>
      ) : null}

      <div className="new-item-main">
        <SectionCard title={t('new.form.title')} subtitle={t('new.form.subtitle')}>
          <form className="form stack" onSubmit={onSubmit}>
            <label>{t('new.reportType')}<select value={status} onChange={(e) => setStatus(e.target.value as ItemStatus)}><option value="lost">{t('board.status.lost')}</option><option value="found">{t('board.status.found')}</option></select></label>
            <label>{t('new.title')}<input required minLength={3} maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
            <label>
              {t('board.filter.category')}
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {categories.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            {categoryHint && categoryHint.category !== 'Other' ? (
              <p className="notice">
                {t('new.suggested')}: <strong>{categoryHint.category}</strong> ({Math.round(categoryHint.confidence * 100)}%)
                {' '}<button type="button" className="button-ghost" onClick={() => setCategory(categoryHint.category)}>{t('new.useSuggestion')}</button>
              </p>
            ) : null}
            <label>{t('board.filter.location')}<input required minLength={2} maxLength={120} value={location} onChange={(e) => setLocation(e.target.value)} /></label>
            {profileAddresses.length > 0 ? (
              <label>Use saved profile address
                <select value="" onChange={(e) => { if (e.target.value) setLocation(e.target.value) }}>
                  <option value="">Select saved address</option>
                  {profileAddresses.map((address) => <option key={address.id} value={address.address_text}>{address.label}: {address.address_text}</option>)}
                </select>
              </label>
            ) : null}
            <label>{t('new.description')}<textarea required minLength={5} maxLength={2000} rows={5} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
            <label>{t('new.contactName')}<input required minLength={2} maxLength={80} value={contactName} onChange={(e) => setContactName(e.target.value)} /></label>
            <label>{t('new.telegramOptional')}<input maxLength={80} value={telegramUsername} onChange={(e) => setTelegramUsername(e.target.value)} placeholder="@username" /></label>
            <label>{t('new.photoOptional')}
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => {
                const file = e.target.files?.[0] || null
                setPhotoFile(file)
                if (!file) return setPhotoPreview(null)
                const reader = new FileReader(); reader.onload = () => setPhotoPreview(String(reader.result)); reader.readAsDataURL(file)
              }} />
            </label>
            {photoPreview ? <img src={photoPreview} alt={t('new.previewAlt')} className="detail-image" /> : null}
            {error ? <p className="notice error">{error}</p> : null}
            {success ? <p className="notice success">{success}</p> : null}
            <div className="actions-row"><button type="submit" disabled={!linkedUserId}>{t('new.create')}</button><button className="button-neutral" type="button" onClick={() => navigate('/')}>{t('common.cancel')}</button></div>
          </form>
        </SectionCard>
      </div>
    </section>
  )
}
