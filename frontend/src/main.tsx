import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { NewItemPage } from './pages/NewItemPage'
import { ItemDetailsPage } from './pages/ItemDetailsPage'
import { MyReportsPage } from './pages/MyReportsPage'
import { AdminPage } from './pages/AdminPage'
import './styles/main.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="new" element={<NewItemPage />} />
          <Route path="my-reports" element={<MyReportsPage />} />
          <Route path="items/:id" element={<ItemDetailsPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
