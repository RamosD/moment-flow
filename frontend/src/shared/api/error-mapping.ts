import {
  ApiError,
  ForbiddenError,
  NotFoundError,
  ServiceUnavailableError,
  UnauthorizedError,
  ValidationError,
} from './errors.ts'
import type { FieldErrors } from './errors.ts'

function extractRequestId(
  response: Response,
  body: unknown,
): string | undefined {
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
    if (Array.isArray(value) && value.every((item) => typeof item === 'string')) {
      result[key] = value as string[]
    } else if (typeof value === 'string') {
      result[key] = [value]
    }
  }
  return Object.keys(result).length > 0 ? result : undefined
}

/** Preserve distinct public error classes without exposing hidden resources. */
export function mapHttpError(response: Response, body: unknown): ApiError {
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
