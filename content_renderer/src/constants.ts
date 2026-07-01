/**
 * Service-wide identity constants.
 *
 * These values are reported to the Backend Core (Django) in healthcheck and
 * callback `metadata` blocks, so keep `RENDERER_VERSION` aligned with the
 * package version.
 */
export const RENDERER_NAME = 'content_renderer';
export const RENDERER_VERSION = '0.1.0';
