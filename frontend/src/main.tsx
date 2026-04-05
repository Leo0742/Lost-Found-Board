import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { NewItemPage } from './pages/NewItemPage'
import { ItemDetailsPage } from './pages/ItemDetailsPage'
import { MyReportsPage } from './pages/MyReportsPage'
import { AdminPage } from './pages/AdminPage'
import { ProfilePage } from './pages/ProfilePage'
import './styles/main.css'
import { SettingsProvider } from './context/SettingsContext'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SettingsProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="new" element={<NewItemPage />} />
          <Route path="my-reports" element={<MyReportsPage />} />
          <Route path="items/:id" element={<ItemDetailsPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </SettingsProvider>
  </React.StrictMode>
)
