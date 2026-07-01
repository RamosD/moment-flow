/**
 * Static, build-time application metadata.
 *
 * Runtime/environment configuration (API base URL, etc.) is intentionally NOT
 * here — it belongs to shared/api + app/config env reading, introduced in
 * FE-003. Keep this file free of secrets.
 */

export const APP_CONFIG = {
  name: 'ChartRex',
  productName: 'MomentFlow',
  description: 'Campaign intelligence and orchestration for music marketing.',
} as const

export type AppConfig = typeof APP_CONFIG
