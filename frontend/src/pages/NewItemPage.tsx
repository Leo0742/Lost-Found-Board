import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { createItem, uploadItemImage, getAuthMe, generateLinkCode, fetchCategories, suggestCategory } from '../api/items'
import { ItemStatus } from '../types/item'
import { EmptyState, PageHero, SectionCard } from '../components/ui'

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
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [isCheckingLink, setIsCheckingLink] = useState(false)
  const [categories, setCategories] = useState<string[]>(['Other'])
  const [categoryHint, setCategoryHint] = useState<{ category: string; confidence: number } | null>(null)
  const navigate = useNavigate()

  const refreshAuthState = useCallback(async (options?: { silent?: boolean; forceRefresh?: boolean }) => {
    if (!options?.silent) setIsCheckingLink(true)
    try {
      const me = await getAuthMe({ forceRefresh: options?.forceRefresh ?? false })
      setLinkedUserId(me.identity?.telegram_user_id ?? null)
      if (me.identity?.telegram_username) {
        setTelegramUsername(`@${me.identity.telegram_username}`)
      }
      if (me.identity?.telegram_user_id) {
        setLinkCode(null)
      }
      return me
    } finally {
      if (!options?.silent) setIsCheckingLink(false)
    }
  }, [])

  useEffect(() => {
    refreshAuthState().catch(() => setError('Could not initialize auth session.'))
    fetchCategories().then((data) => {
      if (data.length > 0) setCategories(data)
    }).catch(() => setCategories(['Other']))
  }, [refreshAuthState])

  useEffect(() => {
    if (!linkCode || linkedUserId) return
    const interval = window.setInterval(() => {
      refreshAuthState({ silent: true, forceRefresh: true }).catch(() => undefined)
    }, 2500)
    return () => window.clearInterval(interval)
  }, [linkCode, linkedUserId, refreshAuthState])

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

  const completionScore = useMemo(() => {
    const fields = [title, description, category, location, contactName, photoFile ? 'yes' : '']
    return Math.round((fields.filter((field) => field.trim().length > 0).length / fields.length) * 100)
  }, [title, description, category, location, contactName, photoFile])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    if (!linkedUserId) return setError('Connect Telegram first so ownership is server-side and synced with bot.')
    try {
      const item = await createItem({
        title: title.trim(),
        description: description.trim(),
        category: category.trim(),
        location: location.trim(),
        status,
        contact_name: contactName.trim(),
        telegram_username: telegramUsername.trim() || undefined,
        ...(photoFile ? await uploadItemImage(photoFile) : {})
      })
      setSuccess('Report created successfully. Redirecting...')
      setTimeout(() => navigate(`/items/${item.id}`), 450)
    } catch (err) {
      setError(formatBackendValidationError(err))
    }
  }

  return (
    <section className="stack">
      <PageHero
        title="Create a high-quality report"
        subtitle="Structured entry improves smart matching, moderation trust, and claim success rates."
        stats={[{ label: 'Completion', value: `${completionScore}%` }, { label: 'Ownership', value: linkedUserId ? 'Linked' : 'Not linked' }]}
      />

      <div className="layout-split">
        <SectionCard title="Report form" subtitle="Complete each block for the best match confidence.">
          <form className="form stack" onSubmit={onSubmit}>
            <label>Report type<select value={status} onChange={(e) => setStatus(e.target.value as ItemStatus)}><option value="lost">Lost item</option><option value="found">Found item</option></select></label>
            <label>Title<input required minLength={3} maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {categories.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            {categoryHint && categoryHint.category !== 'Other' ? (
              <p className="notice">
                Suggested category from title: <strong>{categoryHint.category}</strong> ({Math.round(categoryHint.confidence * 100)}%)
                {' '}<button type="button" className="button-ghost" onClick={() => setCategory(categoryHint.category)}>Use suggestion</button>
              </p>
            ) : null}
            <label>Location<input required minLength={2} maxLength={120} value={location} onChange={(e) => setLocation(e.target.value)} /></label>
            <label>Description<textarea required minLength={5} maxLength={2000} rows={5} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
            <label>Contact name<input required minLength={2} maxLength={80} value={contactName} onChange={(e) => setContactName(e.target.value)} /></label>
            <label>Telegram username (optional)<input maxLength={80} value={telegramUsername} onChange={(e) => setTelegramUsername(e.target.value)} placeholder="@username" /></label>
            <label>Photo (optional)
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => {
                const file = e.target.files?.[0] || null
                setPhotoFile(file)
                if (!file) return setPhotoPreview(null)
                const reader = new FileReader(); reader.onload = () => setPhotoPreview(String(reader.result)); reader.readAsDataURL(file)
              }} />
            </label>
            {photoPreview ? <img src={photoPreview} alt="Selected preview" className="detail-image" /> : null}
            {error ? <p className="notice error">{error}</p> : null}
            {success ? <p className="notice success">{success}</p> : null}
            <div className="actions-row"><button type="submit" disabled={!linkedUserId}>Create report</button><button className="button-neutral" type="button" onClick={() => navigate('/')}>Cancel</button></div>
          </form>
        </SectionCard>

        <div className="stack sticky-side">
          <SectionCard title="Submission checklist" subtitle="Aim for high confidence matching.">
            <div className="timeline-list">
              <div className="timeline-item">Clear title and category</div>
              <div className="timeline-item">Exact location context</div>
              <div className="timeline-item">Distinctive description details</div>
              <div className="timeline-item">Photo for visual verification</div>
            </div>
          </SectionCard>

          {!linkedUserId ? (
            <SectionCard title="Link Telegram" subtitle="Required for secure ownership and synced bot actions.">
              <button type="button" onClick={async () => setLinkCode((await generateLinkCode()).code)}>Generate secure link code</button>
              {linkCode ? <p className="notice">Send this in Telegram: <strong>/link {linkCode}</strong></p> : null}
              {linkCode ? (
                <div className="actions-row">
                  <button
                    type="button"
                    className="button-neutral"
                    disabled={isCheckingLink}
                    onClick={() => refreshAuthState({ forceRefresh: true }).catch(() => setError('Could not refresh link status.'))}
                  >
                    {isCheckingLink ? 'Checking…' : 'I linked my Telegram'}
                  </button>
                </div>
              ) : null}
            </SectionCard>
          ) : <EmptyState title="Telegram linked" subtitle="You can submit and manage this report across web and bot." />}
        </div>
      </div>
    </section>
  )
}
