import { useEffect, useState } from 'react'
import { AxiosError } from 'axios'
import { claimAction, fetchMyItems, generateLinkCode, getAuthMe, listClaims, resolveItem, reopenItem, softDeleteItem, unlinkTelegram } from '../api/items'
import { Claim, Item } from '../types/item'
import { Link } from 'react-router-dom'

export const MyReportsPage = () => {
  const [items, setItems] = useState<Item[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [claimsError, setClaimsError] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    setClaimsError(null)
    try {
      const me = await getAuthMe()
      if (!me.linked || !me.identity?.telegram_user_id) {
        setLinkedUserId(null)
        setLinkedUsername(null)
        setItems([])
        setClaims([])
        return
      }
      setLinkedUserId(me.identity.telegram_user_id)
      setLinkedUsername(me.identity.telegram_username || null)
      const myItems = await fetchMyItems()
      setItems(myItems.sort((a, b) => b.id - a.id))
      setLinkCode(null)
      try {
        const incomingClaims = await listClaims(undefined, 'incoming')
        setClaims(incomingClaims as Claim[])
      } catch (claimsErr) {
        console.error(claimsErr)
        setClaims([])
        setClaimsError('Claims are temporarily unavailable. Your reports are still loaded.')
      }
    } catch (err) {
      console.error(err)
      const axiosErr = err as AxiosError<{ detail?: string }>
      if (axiosErr.response?.status === 401) {
        setLinkedUserId(null)
        setLinkedUsername(null)
        setItems([])
        setClaims([])
        setError(null)
        return
      }
      setError('Failed to load server-owned reports. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const startLinkFlow = async () => {
    try {
      const result = await generateLinkCode()
      setLinkCode(result.code)
      setError(null)
    } catch {
      setError('Could not create link code right now. Please refresh and try again.')
    }
  }

  const runAction = async (itemId: number, action: 'resolve' | 'reopen' | 'delete') => {
    try {
      if (action === 'resolve') await resolveItem(itemId)
      if (action === 'reopen') await reopenItem(itemId)
      if (action === 'delete') await softDeleteItem(itemId)
      await load()
    } catch (err) {
      console.error(err)
      setError('Action failed. Ensure this Telegram-linked account owns the report.')
    }
  }

  const runUnlink = async () => {
    const shouldUnlink = window.confirm('Unlink Telegram from this browser session? You can relink anytime with a new code.')
    if (!shouldUnlink) return
    try {
      await unlinkTelegram()
      await load()
    } catch (err) {
      console.error(err)
      setError('Could not unlink Telegram right now. Please try again.')
    }
  }

  return (
    <section>
      <h1>My Reports</h1>
      <p className="subtle">Server-driven ownership (Telegram-linked), synced across devices and bot.</p>
      {loading ? <p>Loading...</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {claimsError ? <p className="subtle">{claimsError}</p> : null}

      {!loading && !linkedUserId ? (
        <article className="card">
          <h3>Connect Telegram</h3>
          <p>To manage reports from web and bot, link this website session to your Telegram account.</p>
          <button type="button" onClick={startLinkFlow}>Generate link code</button>
          {linkCode ? (
            <p>
              Send this to bot: <strong>/link {linkCode}</strong>
            </p>
          ) : null}
          <p className="subtle">After sending /link in Telegram, reload this page.</p>
        </article>
      ) : null}

      {linkedUserId ? (
        <div className="actions-row">
          <p className="subtle">
            Connected Telegram: <strong>{linkedUsername ? `@${linkedUsername}` : linkedUserId}</strong>
          </p>
          <button type="button" className="danger" onClick={runUnlink}>Unlink Telegram</button>
        </div>
      ) : null}

      {!loading && linkedUserId && items.length === 0 ? <p>No reports yet. Create one on Report Item page.</p> : null}

      <div className="grid">
        {items.map((item) => (
          <article key={item.id} className="card">
            {item.image_path ? <img className="thumb" src={`/media/${item.image_path}`} alt={item.title} /> : null}
            <div className="card-head">
              <h3>
                <Link to={`/items/${item.id}`}>{item.title}</Link>
              </h3>
              <span className={`badge ${item.status}`}>{item.status}</span>
            </div>
            <p>Lifecycle: <strong>{item.lifecycle}</strong></p>
            <p>Moderation: <strong>{item.moderation_status}</strong> {item.is_verified ? '✅ Verified' : ''}</p>
            <div className="meta">
              <span>{item.category}</span>
              <span>{item.location}</span>
            </div>
            <div className="actions-row">
              {item.lifecycle === 'active' ? <button type="button" onClick={() => runAction(item.id, 'resolve')}>Resolve</button> : null}
              {item.lifecycle === 'resolved' ? <button type="button" onClick={() => runAction(item.id, 'reopen')}>Reopen</button> : null}
              {item.lifecycle !== 'deleted' ? <button type="button" className="danger" onClick={() => runAction(item.id, 'delete')}>Delete</button> : null}
            </div>
          </article>
        ))}
      </div>

      {linkedUserId && claims.length > 0 ? (
        <section>
          <h2>Incoming Claims</h2>
          {claims.map((claim) => (
            <article key={claim.id} className="card">
              <strong>Claim #{claim.id}</strong> — {claim.status}
              <div>For item #{claim.target_item_id}</div>
              {claim.status === 'pending' ? (
                <div className="actions-row">
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'approve'); await load() }}>Approve</button>
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'reject'); await load() }}>Reject</button>
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'complete'); await load() }}>Mark returned</button>
                </div>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}
    </section>
  )
}
