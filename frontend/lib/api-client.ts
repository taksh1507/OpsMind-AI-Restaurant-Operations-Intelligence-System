import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios'

// Default to `localhost` (not 127.0.0.1) so the API is same-site with the
// Next.js dev server on localhost:3000 — required for the SameSite=Lax refresh
// cookie to be sent on cross-origin (different-port) XHRs.
const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Fast default for CRUD/read requests. Anything slower is an outlier we don't
// want the UI hanging on.
const DEFAULT_TIMEOUT_MS = 10000

// LLM- and ML-backed endpoints are inherently slow: a single Claude strategy
// call runs ~15-25s (occasionally longer with weather lookups), and model
// retraining is longer still. These paths get a much larger budget so the
// browser doesn't abort a request the server is still legitimately working on.
const SLOW_ENDPOINT_PATTERNS = [
  '/analytics/ai-briefing',
  '/analytics/daily-tip',
  '/analytics/forecast',
  '/analytics/staffing-plan',
  '/analytics/reputation',
  '/ml/retrain',
]
const SLOW_TIMEOUT_MS = 120000

// Create Axios instance with base URL
const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: DEFAULT_TIMEOUT_MS,
  // Send/receive the httpOnly refresh cookie on auth requests.
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    // Get JWT token from localStorage
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    // Give slow LLM/ML endpoints a longer budget unless the caller already set
    // an explicit per-request timeout.
    const url = config.url ?? ''
    if (
      config.timeout === DEFAULT_TIMEOUT_MS &&
      SLOW_ENDPOINT_PATTERNS.some((p) => url.includes(p))
    ) {
      config.timeout = SLOW_TIMEOUT_MS
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// --- Refresh-token handling -------------------------------------------------

// Single-flight guard: while one refresh is in progress, concurrent 401s share
// the same promise so we only call /auth/refresh once (rotation issues a new
// refresh token, so parallel refreshes would invalidate each other).
let refreshPromise: Promise<string> | null = null

function clearSessionAndRedirect(): void {
  if (typeof window !== 'undefined') {
    // The refresh token lives in an httpOnly cookie the server clears on logout;
    // here we only drop the client-readable access token + type.
    localStorage.removeItem('access_token')
    localStorage.removeItem('token_type')
    window.location.href = '/login'
  }
}

async function refreshAccessToken(): Promise<string> {
  // The refresh token is sent automatically as an httpOnly cookie (withCredentials),
  // so there is nothing to read from localStorage and no token in the body.
  // Use a bare axios call (not apiClient) so this request bypasses the
  // interceptors and can never trigger a recursive refresh on its own 401.
  const { data } = await axios.post(
    `${baseURL}/auth/refresh`,
    {},
    { withCredentials: true }
  )

  const newAccessToken: string = data.access_token
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', newAccessToken)
    // Rotation issues a fresh refresh token, delivered as a new httpOnly cookie.
    if (data.token_type) {
      localStorage.setItem('token_type', data.token_type)
    }
  }
  return newAccessToken
}

// Response interceptor: on 401, try one silent refresh + retry, else log out.
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined

    // Auth endpoints must surface their own 401s (e.g. "invalid credentials")
    // to the calling page instead of triggering a refresh + redirect loop.
    const url = originalRequest?.url ?? ''
    const isAuthEndpoint =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/logout')

    // Only attempt a refresh for a genuine 401 we have not already retried.
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null
          })
        }
        const newAccessToken = await refreshPromise

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed (missing/expired/revoked token) -> end the session.
        clearSessionAndRedirect()
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
