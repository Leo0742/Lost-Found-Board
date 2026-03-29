import { useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { getAuthMe } from '../api/items'

export const Layout = () => {
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [role, setRole] = useState<'admin' | 'moderator' | null>(null)

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const me = await getAuthMe()
        if (!me.linked || !me.admin_access) {
          setRole(null)
          setLinkedUsername(null)
          setLinkedUserId(null)
          return
        }
        setRole(me.role ?? null)
        setLinkedUsername(me.identity?.telegram_username ?? null)
        setLinkedUserId(me.identity?.telegram_user_id ?? null)
      } catch {
        setRole(null)
      }
    }
    loadAuth()
  }, [])

  const identityLabel = linkedUsername ? `@${linkedUsername}` : linkedUserId

  return (
    <div className="app-shell">
      <header className="header">
        <div className="container">
          <Link className="brand" to="/">
            Lost & Found Board
          </Link>
          <nav className="top-nav">
            <Link to="/">Items</Link>
            <Link to="/new">Report Item</Link>
            <Link to="/my-reports">My Reports</Link>
            {role ? <Link to="/admin">Moderation</Link> : null}
          </nav>
          {role ? (
            <div className={`role-chip ${role}`}>
              <span>{role === 'admin' ? 'Admin' : 'Moderator'}</span>
              <small>Signed in as {identityLabel}</small>
            </div>
          ) : null}
        </div>
      </header>
      <main className="container content">
        <Outlet />
      </main>
    </div>
  )
}
