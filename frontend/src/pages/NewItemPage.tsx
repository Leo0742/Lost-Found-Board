import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createItem } from '../api/items'
import { ItemStatus } from '../types/item'

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
        title,
        description,
        category,
        location,
        status,
        contact_name: contactName,
        telegram_username: telegramUsername || undefined
      })
      navigate(`/items/${item.id}`)
    } catch {
      setError('Could not create item. Please review the form.')
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
          <input required value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Category
          <input required value={category} onChange={(e) => setCategory(e.target.value)} />
        </label>
        <label>
          Location
          <input required value={location} onChange={(e) => setLocation(e.target.value)} />
        </label>
        <label>
          Description
          <textarea required rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label>
          Contact name
          <input required value={contactName} onChange={(e) => setContactName(e.target.value)} />
        </label>
        <label>
          Telegram username (optional)
          <input value={telegramUsername} onChange={(e) => setTelegramUsername(e.target.value)} placeholder="@username" />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit">Create item</button>
      </form>
    </section>
  )
}
