/**
 * Shared HTML helpers for the report and media-kit renderers.
 *
 * Pure string utilities — no DOM, no remote assets. Everything coming from the
 * untrusted payload must pass through {@link escapeHtml}; URLs additionally pass
 * through {@link safeUrl} so only http(s)/mailto links are emitted (no
 * `javascript:` or other active schemes).
 */

/** Escape the five HTML-sensitive characters. */
export function escapeHtml(value: unknown): string {
  const raw = value === null || value === undefined ? '' : String(value);
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Accept only safe CSS colour tokens (hex or simple named); else a default. */
export function safeCssColor(color: string, fallback = '#6C5CE7'): string {
  return /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(color) || /^[a-zA-Z]{1,20}$/.test(color)
    ? color
    : fallback;
}

/**
 * Return the URL only if it uses an allowed scheme (http/https/mailto), else
 * `null`. Prevents `javascript:`/`data:` links in generated HTML.
 */
export function safeUrl(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed) || /^mailto:/i.test(trimmed)) {
    return trimmed;
  }
  return null;
}
