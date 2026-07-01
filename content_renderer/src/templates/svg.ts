/**
 * Minimal SVG card builder and SVG → PNG rasterizer (CR-402).
 *
 * The SVG is plain string templating (no editor, no browser, no remote assets).
 * Rasterization uses Sharp (libvips), which renders SVG without a headless
 * browser. All text and colours are sanitized before they enter the markup to
 * prevent broken/invalid SVG and attribute injection.
 */
import sharp from 'sharp';

export interface SvgSpec {
  width: number;
  height: number;
  backgroundColor: string;
  brandColor: string;
  title: string;
  subtitle?: string;
  artistName?: string;
  trackTitle?: string;
  campaignName?: string;
  /** A metric or milestone highlight, e.g. "1,000,000 streams". */
  metric?: string;
  /** Small top label, e.g. "NEW RELEASE". */
  badge?: string;
}

// Control characters that would corrupt the SVG (strip all of them). Built from
// an escaped string so no raw control bytes live in this source file.
// eslint-disable-next-line no-control-regex
const CONTROL_CHARS = new RegExp('[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F]', 'g');

/**
 * Make arbitrary text safe to embed as SVG text content: strip control chars,
 * collapse whitespace, clamp length, then XML-escape the five sensitive chars.
 */
export function sanitizeTextForSvg(text: unknown, maxLength = 200): string {
  const raw = text === null || text === undefined ? '' : String(text);
  const cleaned = raw.replace(CONTROL_CHARS, '').replace(/\s+/g, ' ').trim().slice(0, maxLength);
  return cleaned
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const HEX_COLOR = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
const NAMED_COLOR = /^[a-zA-Z]{1,20}$/;

/** Accept only `#rgb`/`#rrggbb` or simple named colours; otherwise fall back. */
export function sanitizeColor(color: unknown, fallback: string): string {
  if (typeof color === 'string') {
    const value = color.trim();
    if (HEX_COLOR.test(value) || NAMED_COLOR.test(value)) {
      return value;
    }
  }
  return fallback;
}

const FONT_STACK = 'Arial, Helvetica, sans-serif';

/** Build a simple branded card SVG from a fully-specified {@link SvgSpec}. */
export function buildSvg(spec: SvgSpec): string {
  const { width, height } = spec;
  const bg = sanitizeColor(spec.backgroundColor, '#0B0B0F');
  const brand = sanitizeColor(spec.brandColor, '#6C5CE7');

  const pad = Math.round(width * 0.08);
  const titleSize = Math.round(width * 0.075);
  const subSize = Math.round(width * 0.042);
  const metaSize = Math.round(width * 0.034);
  const metricSize = Math.round(width * 0.062);

  const title = sanitizeTextForSvg(spec.title, 120);
  const subtitle = sanitizeTextForSvg(spec.subtitle, 160);
  const artist = sanitizeTextForSvg(spec.artistName, 80);
  const track = sanitizeTextForSvg(spec.trackTitle, 80);
  const campaign = sanitizeTextForSvg(spec.campaignName, 80);
  const metric = sanitizeTextForSvg(spec.metric, 60);
  const badge = sanitizeTextForSvg(spec.badge, 24);

  const parts: string[] = [
    `<rect x="0" y="0" width="${width}" height="${height}" fill="${bg}"/>`,
    `<rect x="0" y="0" width="${width}" height="${Math.round(height * 0.018)}" fill="${brand}"/>`,
  ];

  let y = Math.round(height * 0.2);

  if (badge) {
    parts.push(
      `<text x="${pad}" y="${y}" fill="${brand}" font-family="${FONT_STACK}" font-size="${metaSize}" font-weight="700" letter-spacing="2">${badge}</text>`,
    );
    y += Math.round(metaSize * 1.9);
  }

  parts.push(
    `<text x="${pad}" y="${y}" fill="#FFFFFF" font-family="${FONT_STACK}" font-size="${titleSize}" font-weight="800">${title}</text>`,
  );
  y += Math.round(titleSize * 1.35);

  if (subtitle) {
    parts.push(
      `<text x="${pad}" y="${y}" fill="#C8C8D0" font-family="${FONT_STACK}" font-size="${subSize}">${subtitle}</text>`,
    );
    y += Math.round(subSize * 1.7);
  }

  const trackLine = [artist, track].filter(Boolean).join('  -  ');
  if (trackLine) {
    parts.push(
      `<text x="${pad}" y="${y}" fill="#E8E8EC" font-family="${FONT_STACK}" font-size="${metaSize}" font-weight="600">${trackLine}</text>`,
    );
    y += Math.round(metaSize * 1.7);
  }

  if (campaign) {
    parts.push(
      `<text x="${pad}" y="${y}" fill="#9A9AA6" font-family="${FONT_STACK}" font-size="${metaSize}">${campaign}</text>`,
    );
  }

  if (metric) {
    const metricY = Math.round(height * 0.86);
    parts.push(
      `<text x="${pad}" y="${metricY}" fill="${brand}" font-family="${FONT_STACK}" font-size="${metricSize}" font-weight="800">${metric}</text>`,
    );
  }

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    ...parts,
    `</svg>`,
  ].join('');
}

/**
 * Rasterize an SVG string to a PNG buffer. When dimensions are provided the
 * output is forced to exactly those pixels (the SVG is already authored at the
 * target size, so this is an exactness guard, not a rescale).
 */
export async function renderSvgToPng(
  svg: string,
  dimensions?: { width?: number; height?: number },
): Promise<Buffer> {
  let pipeline = sharp(Buffer.from(svg, 'utf8'));
  if (dimensions?.width && dimensions?.height) {
    pipeline = pipeline.resize(dimensions.width, dimensions.height, { fit: 'fill' });
  }
  return pipeline.png().toBuffer();
}
