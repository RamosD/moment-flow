export { apiClient, createApiClient } from './client'
export type { ApiClient, ApiClientOptions } from './client'

export {
  setTokenProvider,
  setWorkspaceProvider,
  setUnauthorizedHandler,
  readToken,
  readWorkspaceId,
} from './providers'

export {
  ApiError,
  UnauthorizedError,
  ForbiddenError,
  NotFoundError,
  ValidationError,
  ServiceUnavailableError,
  NetworkError,
} from './errors'
export type { ApiErrorOptions, FieldErrors } from './errors'

export type {
  Paginated,
  RequestOptions,
  TokenProvider,
  WorkspaceProvider,
} from './types'
