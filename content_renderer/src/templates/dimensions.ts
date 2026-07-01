/**
 * Output formats and pixel dimensions (CR-403).
 *
 * The renderer supports a small set of social formats. Unknown/absent formats
 * resolve to a safe fallback so a render never fails on dimensions alone.
 */
export const OUTPUT_FORMATS = [
  'post_1_1',
  'post_4_5',
  'story_9_16',
  'thumbnail_16_9',
] as const;

export type OutputFormat = (typeof OUTPUT_FORMATS)[number];

export interface Dimensions {
  width: number;
  height: number;
}

export const FORMAT_DIMENSIONS: Record<OutputFormat, Dimensions> = {
  post_1_1: { width: 1080, height: 1080 },
  post_4_5: { width: 1080, height: 1350 },
  story_9_16: { width: 1080, height: 1920 },
  thumbnail_16_9: { width: 1280, height: 720 },
};

/** Safe fallback format used when an unknown/absent format is requested. */
export const FALLBACK_FORMAT: OutputFormat = 'post_1_1';

export interface ResolvedDimensions extends Dimensions {
  format: OutputFormat;
  usedFallback: boolean;
}

export function isKnownFormat(format: string): format is OutputFormat {
  return (OUTPUT_FORMATS as readonly string[]).includes(format);
}

/** Resolve a requested format to concrete dimensions, falling back safely. */
export function resolveOutputDimensions(format?: string): ResolvedDimensions {
  if (format && isKnownFormat(format)) {
    return { format, ...FORMAT_DIMENSIONS[format], usedFallback: false };
  }
  return {
    format: FALLBACK_FORMAT,
    ...FORMAT_DIMENSIONS[FALLBACK_FORMAT],
    usedFallback: true,
  };
}
