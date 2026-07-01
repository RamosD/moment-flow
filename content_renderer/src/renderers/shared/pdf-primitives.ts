/**
 * Low-level PDF primitives shared by the report and media-kit renderers.
 *
 * Kept dependency-free (no `pdf-lib` import here) so they are trivially unit
 * testable: colour parsing, WinAnsi-safe text sanitization, greedy word-wrap and
 * the A4 page geometry.
 */

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

/** Minimal font shape needed for measuring text width (satisfied by pdf-lib fonts). */
export interface MeasurableFont {
  widthOfTextAtSize(text: string, size: number): number;
}

export const A4_WIDTH = 595.28; // A4 portrait, in PDF points
export const A4_HEIGHT = 841.89;
export const PAGE_MARGIN = 50;

export const DEFAULT_BRAND: Rgb = { r: 0x6c / 255, g: 0x5c / 255, b: 0xe7 / 255 };

/** Parse `#rgb`/`#rrggbb` into 0..1 channels; fall back for anything else. */
export function hexToRgb01(hex: string, fallback: Rgb = DEFAULT_BRAND): Rgb {
  const match = /^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(hex.trim());
  if (!match) {
    return fallback;
  }
  let value = match[1];
  if (value.length === 3) {
    value = value
      .split('')
      .map((c) => c + c)
      .join('');
  }
  const n = parseInt(value, 16);
  return { r: ((n >> 16) & 0xff) / 255, g: ((n >> 8) & 0xff) / 255, b: (n & 0xff) / 255 };
}

/**
 * Reduce arbitrary text to characters the StandardFont (WinAnsi) can encode:
 * decompose accents, map smart punctuation to ASCII, drop the rest. Prevents
 * pdf-lib "cannot encode" errors on unexpected unicode from the payload.
 */
export function toPdfText(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[‐-―]/g, '-')
    .replace(/[‘’‚‛]/g, "'")
    .replace(/[“”„‟]/g, '"')
    .replace(/[^\x20-\x7E]/g, '')
    .trim();
}

/** Greedy word-wrap for a single paragraph at the given font/size. */
export function wrapText(
  text: string,
  font: MeasurableFont,
  size: number,
  maxWidth: number,
): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = '';
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (current && font.widthOfTextAtSize(candidate, size) > maxWidth) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) {
    lines.push(current);
  }
  return lines;
}
