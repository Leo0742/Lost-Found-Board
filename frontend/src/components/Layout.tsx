import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
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
          <Link className="brand" to="/">Lost & Found Board</Link>
          <nav className="top-nav">
            <NavLink to="/">Items</NavLink>
            <NavLink to="/new">Report Item</NavLink>
            <NavLink to="/my-reports">My Reports</NavLink>
            {role ? <NavLink to="/admin">Moderation</NavLink> : null}
          </nav>
          {role ? (
            <div className={`role-chip ${role}`}>
              <span>{role === 'admin' ? 'Admin Console' : 'Moderator Console'}</span>
              <small>{identityLabel}</small>
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
