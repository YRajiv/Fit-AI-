import axios from 'axios'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'https://fit-ai-z29o.onrender.com'
).replace(/\/+$/, '')

let csrfToken = ''

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { Accept: 'application/json' },
})

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (csrfToken && !['get', 'head', 'options'].includes(method)) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

export async function initializeCsrf() {
  const { data } = await api.get('/users/api/csrf/')
  csrfToken = data.csrfToken
  return csrfToken
}

export function updateCsrfToken(token) {
  if (token) csrfToken = token
}

export function getCsrfToken() {
  return csrfToken
}

export function getErrorMessage(error) {
  const data = error.response?.data
  if (typeof data?.error === 'string') return data.error
  if (typeof data?.message === 'string') return data.message
  if (data?.errors) {
    return Object.values(data.errors)
      .flat()
      .map((item) => item.message)
      .filter(Boolean)
      .join(' ')
  }
  if (error.response?.status === 401) {
    return 'Your session has expired. Please sign in again.'
  }
  if (error.response) return `Request failed (${error.response.status}).`
  return error.message || 'Could not reach the FitAI server.'
}

export async function streamChat(message, history, onText) {
  const response = await fetch(`${API_BASE_URL}/chat/send/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({ message, history }),
  })

  const contentType = response.headers.get('content-type') || ''
  if (!response.ok || !contentType.includes('text/event-stream')) {
    let data
    try {
      if (contentType.includes('application/json')) data = await response.json()
    } catch {
      data = null
    }
    throw new Error(
      data?.error ||
      (response.status === 401
        ? 'Your session has expired. Please sign in again.'
        : 'The assistant returned an unexpected response. Please sign in again and retry.')
    )
  }

  if (!response.body) throw new Error('Streaming is not supported by this browser.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let answer = ''

  const processEvent = (event) => {
    const dataLine = event
      .split(/\r?\n/)
      .find((line) => line.startsWith('data:'))
    if (!dataLine) return

    let payload
    try {
      payload = JSON.parse(dataLine.slice(5).trim())
    } catch {
      throw new Error('The assistant returned an unreadable response.')
    }

    if (payload.type === 'text' && typeof payload.text === 'string') {
      answer += payload.text
      onText(payload.text)
    } else if (payload.type === 'error') {
      throw new Error(payload.message || 'The assistant could not respond.')
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() || ''
    events.forEach(processEvent)
    if (done) break
  }

  if (buffer.trim()) processEvent(buffer)
  return answer
}
