import { FormEvent, useEffect, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { createItem, uploadItemImage, getAuthMe, generateLinkCode } from '../api/items'
import { ItemStatus } from '../types/item'

const formatBackendValidationError = (error: unknown): string => {
  if (!axios.isAxiosError(error)) return 'Could not create item. Please review the form.'
  const detail = error.response?.data?.detail
  if (!Array.isArray(detail) || detail.length === 0) return 'Could not create item. Please review the form.'
  const messages = detail
    .map((issue: { loc?: Array<string | number>; msg?: string }) => {
      const field = issue.loc?.[issue.loc.length - 1]
      if (!field || !issue.msg) return null
      return `${String(field)}: ${issue.msg}`
    })
    .filter((message: string | null): message is string => Boolean(message))
  return messages.length > 0 ? messages.join('; ') : 'Could not create item. Please review the form.'
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
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const navigate = useNavigate()

  const loadAuth = async () => {
    const me = await getAuthMe()
    setLinkedUserId(me.identity?.telegram_user_id ?? null)
    if (me.identity?.telegram_username) setTelegramUsername(`@${me.identity.telegram_username}`)
  }

  useEffect(() => {
    loadAuth().catch(() => setError('Could not initialize auth session.'))
  }, [])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    if (!linkedUserId) {
      setError('Connect Telegram first so ownership is server-side and synced with bot.')
      return
    }
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
      navigate(`/items/${item.id}`)
    } catch (err) {
      setError(formatBackendValidationError(err))
    }
  }

  return (
    <section>
      <h1>Post Lost or Found Item</h1>
      {!linkedUserId ? (
        <article className="card">
          <h3>Connect Telegram first</h3>
          <p>Ownership is now server-side and Telegram-linked. Generate a code and send it to the bot.</p>
          <button
            type="button"
            onClick={async () => {
              const data = await generateLinkCode()
              setLinkCode(data.code)
            }}
          >Generate link code</button>
          {linkCode ? <p>Send to bot: <strong>/link {linkCode}</strong></p> : null}
        </article>
      ) : null}
      <form className="form" onSubmit={onSubmit}>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as ItemStatus)}>
            <option value="lost">Lost</option>
            <option value="found">Found</option>
          </select>
        </label>
        <label>
          Title
          <input required minLength={3} maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Category
          <input required minLength={2} maxLength={60} value={category} onChange={(e) => setCategory(e.target.value)} />
        </label>
        <label>
          Location
          <input required minLength={2} maxLength={120} value={location} onChange={(e) => setLocation(e.target.value)} />
        </label>
        <label>
          Description
          <textarea required minLength={5} maxLength={2000} rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label>
          Contact name
          <input required minLength={2} maxLength={80} value={contactName} onChange={(e) => setContactName(e.target.value)} />
        </label>
        <label>
          Telegram username (optional)
          <input maxLength={80} value={telegramUsername} onChange={(e) => setTelegramUsername(e.target.value)} placeholder="@username" />
        </label>
        <label>
          Photo (optional)
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => {
              const file = e.target.files?.[0] || null
              setPhotoFile(file)
              if (!file) return setPhotoPreview(null)
              const reader = new FileReader()
              reader.onload = () => setPhotoPreview(String(reader.result))
              reader.readAsDataURL(file)
            }}
          />
        </label>
        {photoPreview ? <div><img src={photoPreview} alt="Selected preview" style={{ maxWidth: '280px', borderRadius: '8px' }} /></div> : null}
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" disabled={!linkedUserId}>Create item</button>
      </form>
    </section>
  )
}
