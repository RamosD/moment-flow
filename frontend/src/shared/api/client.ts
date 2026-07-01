/**
 * Central Backend Core HTTP client.
 *
 * This is the ONLY network boundary of the frontend. It targets the Backend
 * Core exclusively (never the Intelligence Engine or Content Renderer) and
 * never sends `X-Internal-Token` — that header is a service-to-service secret
 * and must not exist in the browser.
 *
 * Credentials are injected, not hardcoded: the access token and workspace id
 * are read through provider functions at request time (see ./providers).
 */

import { ENV } from '@/shared/config'

import {
  ApiError,
  ForbiddenError,
  NetworkError,
  NotFoundError,
  ServiceUnavailableError,
  UnauthorizedError,
  ValidationError,
  type FieldErrors,
} from './errors'
import { notifyUnauthorized, readToken, readWorkspaceId } from './providers'
import type { RequestOptions, TokenProvider, WorkspaceProvider } from './types'

/** Header that must never be sent from the frontend. */
const INTERNAL_TOKEN_HEADER = 'x-internal-token'

export interface ApiClientOptions {
  baseUrl: string
  getAuthToken?: TokenProvider
  getWorkspaceId?: WorkspaceProvider
}

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

function buildUrl(
  baseUrl: string,
  path: string,
  params?: RequestOptions['params'],
): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${baseUrl}${normalizedPath}`
  if (!params) return url

  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    search.append(key, String(value))
  }
  const query = search.toString()
  return query ? `${url}?${query}` : url
}

/** Drop any attempt to set the internal service-to-service token. */
function sanitizeCustomHeaders(
  headers: Record<string, string> | undefined,
  target: Headers,
): void {
  if (!headers) return
  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === INTERNAL_TOKEN_HEADER) {
      if (ENV.isDev) {
        console.warn(
          '[api] Blocked attempt to set X-Internal-Token from the frontend.',
        )
      }
      continue
    }
    target.set(key, value)
  }
}

function extractRequestId(response: Response, body: unknown): string | undefined {
  const fromHeader =
    response.headers.get('X-Request-ID') ??
    response.headers.get('X-Request-Id') ??
    undefined
  if (fromHeader) return fromHeader
  if (body && typeof body === 'object' && 'request_id' in body) {
    const value = (body as Record<string, unknown>).request_id
    if (typeof value === 'string') return value
  }
  return undefined
}

function extractMessage(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body.trim()) return body
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>
    if (typeof record.detail === 'string') return record.detail
    if (typeof record.message === 'string') return record.message
  }
  return fallback
}

function extractCode(body: unknown): string | undefined {
  if (body && typeof body === 'object') {
    const value = (body as Record<string, unknown>).code
    if (typeof value === 'string') return value
  }
  return undefined
}

/** Best-effort parse of DRF field errors: `{ field: ["msg", …], … }`. */
function extractFieldErrors(body: unknown): FieldErrors | undefined {
  if (!body || typeof body !== 'object') return undefined
  const result: FieldErrors = {}
  for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
    if (key === 'detail' || key === 'code' || key === 'message') continue
    if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
      result[key] = value as string[]
    } else if (typeof value === 'string') {
      result[key] = [value]
    }
  }
  return Object.keys(result).length > 0 ? result : undefined
}

function mapHttpError(response: Response, body: unknown): ApiError {
  const status = response.status
  const requestId = extractRequestId(response, body)
  const code = extractCode(body)
  const message = extractMessage(body, response.statusText || `HTTP ${status}`)
  const base = { code, details: body, requestId }

  switch (status) {
    case 400:
    case 422:
      return new ValidationError(message, {
        ...base,
        status,
        fieldErrors: extractFieldErrors(body),
      })
    case 401:
      return new UnauthorizedError(message, base)
    case 403:
      return new ForbiddenError(message, base)
    case 404:
      return new NotFoundError(message, base)
    case 502:
    case 503:
      return new ServiceUnavailableError(message, { ...base, status })
    default:
      return new ApiError(message, { ...base, status })
  }
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const text = await response.text()
  if (!text) return undefined
  const contentType = response.headers.get('Content-Type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return JSON.parse(text)
    } catch {
      return text
    }
  }
  return text
}

export interface ApiClient {
  get<T>(path: string, options?: RequestOptions): Promise<T>
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>
  delete<T>(path: string, options?: RequestOptions): Promise<T>
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const { baseUrl } = options
  const getAuthToken = options.getAuthToken ?? (() => null)
  const getWorkspaceId = options.getWorkspaceId ?? (() => null)

  async function request<T>(
    method: HttpMethod,
    path: string,
    body: unknown,
    options: RequestOptions = {},
  ): Promise<T> {
    const hasBody = body !== undefined && method !== 'GET'
    const headers = new Headers()
    headers.set('Accept', 'application/json')
    if (hasBody) headers.set('Content-Type', 'application/json')

    if (options.auth !== false) {
      const token = getAuthToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
    }

    const workspaceId = getWorkspaceId()
    if (workspaceId) headers.set('X-Workspace-ID', workspaceId)

    // Custom headers are merged last; internal-secret headers are stripped.
    sanitizeCustomHeaders(options.headers, headers)

    const url = buildUrl(baseUrl, path, options.params)

    let response: Response
    try {
      response = await fetch(url, {
        method,
        headers,
        body: hasBody ? JSON.stringify(body) : undefined,
        signal: options.signal,
      })
    } catch (cause) {
      // Propagate genuine cancellations untouched.
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        throw cause
      }
      throw new NetworkError(
        'Network request failed. The Backend Core may be unreachable.',
        { cause },
      )
    }

    const parsed = await parseBody(response)
    if (!response.ok) {
      // A 401 on an authenticated request means the session token was refused.
      // Login/refresh use `auth: false` and are excluded on purpose.
      if (response.status === 401 && options.auth !== false) {
        notifyUnauthorized()
      }
      throw mapHttpError(response, parsed)
    }
    return parsed as T
  }

  return {
    get: (path, options) => request('GET', path, undefined, options),
    post: (path, body, options) => request('POST', path, body, options),
    patch: (path, body, options) => request('PATCH', path, body, options),
    delete: (path, options) => request('DELETE', path, undefined, options),
  }
}

/**
 * Default singleton client: base URL from env, credentials read through the
 * injectable provider registry. Use this everywhere; call the provider setters
 * (FE-007/FE-008) to wire auth + workspace state.
 */
export const apiClient = createApiClient({
  baseUrl: ENV.apiBaseUrl,
  getAuthToken: readToken,
  getWorkspaceId: readWorkspaceId,
})
