import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

let csrfToken: string | null = null
let csrfPromise: Promise<string> | null = null

const fetchCsrfToken = async () => {
  if (csrfToken) return csrfToken
  if (!csrfPromise) {
    csrfPromise = apiClient.get<{ csrf_token: string }>('/auth/csrf').then((response) => {
      csrfToken = response.data.csrf_token
      return csrfToken
    }).finally(() => {
      csrfPromise = null
    })
  }
  return csrfPromise
}

apiClient.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toUpperCase()
  const requiresCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  if (!requiresCsrf || config.url?.endsWith('/auth/session') || config.url?.endsWith('/auth/csrf')) return config
  const token = await fetchCsrfToken()
  config.headers = config.headers || {}
  config.headers['X-CSRF-Token'] = token
  return config
})
