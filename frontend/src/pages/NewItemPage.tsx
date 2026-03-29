import { FormEvent, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { createItem } from '../api/items'
import { ItemStatus } from '../types/item'

const formatBackendValidationError = (error: unknown): string => {
  if (!axios.isAxiosError(error)) {
    return 'Could not create item. Please review the form.'
  }

  const detail = error.response?.data?.detail
  if (!Array.isArray(detail) || detail.length === 0) {
    return 'Could not create item. Please review the form.'
  }

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
  const navigate = useNavigate()

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      const item = await createItem({
        title: title.trim(),
        description: description.trim(),
        category: category.trim(),
        location: location.trim(),
        status,
        contact_name: contactName.trim(),
        telegram_username: telegramUsername.trim() || undefined
      })
      navigate(`/items/${item.id}`)
    } catch (err) {
      setError(formatBackendValidationError(err))
    }
  }

  return (
    <section>
      <h1>Post Lost or Found Item</h1>
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
          <textarea
            required
            minLength={5}
            maxLength={2000}
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label>
          Contact name
          <input required minLength={2} maxLength={80} value={contactName} onChange={(e) => setContactName(e.target.value)} />
        </label>
        <label>
          Telegram username (optional)
          <input
            maxLength={80}
            value={telegramUsername}
            onChange={(e) => setTelegramUsername(e.target.value)}
            placeholder="@username"
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit">Create item</button>
      </form>
    </section>
  )
}
