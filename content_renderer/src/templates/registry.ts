/**
 * Template registry (CR-401).
 *
 * Maps a `template_key` to a template definition (default format + how to turn
 * domain content into an {@link SvgSpec}). Unknown keys resolve to a safe
 * fallback. `renderTemplate` ties the registry to the SVG builder and the PNG
 * rasterizer.
 */
import {
  resolveOutputDimensions,
  type OutputFormat,
  type ResolvedDimensions,
} from './dimensions';
import { buildSvg, renderSvgToPng, type SvgSpec } from './svg';

/** Initial catalogue of template keys (backlog CR-401). */
export const TEMPLATE_KEYS = [
  'generic_post',
  'generic_story',
  'milestone_card',
  'weekly_growth_card',
  'release_card',
  'report_cover',
  'media_kit_cover',
] as const;

export type TemplateKey = (typeof TEMPLATE_KEYS)[number];

/** Fallback used when an unknown template key is requested. */
export const FALLBACK_TEMPLATE_KEY: TemplateKey = 'generic_post';

/** Domain content a template can present. All fields optional. */
export interface TemplateContent {
  title?: string;
  subtitle?: string;
  artistName?: string;
  trackTitle?: string;
  campaignName?: string;
  /** Metric or milestone highlight. */
  metric?: string;
  /** Optional brand colour (hex/named); sanitized at render time. */
  brandColor?: string;
}

export interface TemplateDefinition {
  key: TemplateKey;
  /** Default output format when the job does not request one. */
  defaultFormat: OutputFormat;
  /** Map content + resolved dimensions to a render-ready SVG spec. */
  buildSpec: (content: TemplateContent, dimensions: ResolvedDimensions) => SvgSpec;
}

interface SpecOptions {
  badge?: string;
  backgroundColor?: string;
  brandColor?: string;
}

function specFor(
  content: TemplateContent,
  dimensions: ResolvedDimensions,
  options: SpecOptions,
): SvgSpec {
  return {
    width: dimensions.width,
    height: dimensions.height,
    backgroundColor: options.backgroundColor ?? '#0B0B0F',
    brandColor: content.brandColor ?? options.brandColor ?? '#6C5CE7',
    title: content.title ?? '',
    subtitle: content.subtitle,
    artistName: content.artistName,
    trackTitle: content.trackTitle,
    campaignName: content.campaignName,
    metric: content.metric,
    badge: options.badge,
  };
}

const DEFINITIONS: Record<TemplateKey, TemplateDefinition> = {
  generic_post: {
    key: 'generic_post',
    defaultFormat: 'post_1_1',
    buildSpec: (c, d) => specFor(c, d, {}),
  },
  generic_story: {
    key: 'generic_story',
    defaultFormat: 'story_9_16',
    buildSpec: (c, d) => specFor(c, d, {}),
  },
  milestone_card: {
    key: 'milestone_card',
    defaultFormat: 'post_1_1',
    buildSpec: (c, d) => specFor(c, d, { badge: 'MILESTONE', brandColor: '#00B894' }),
  },
  weekly_growth_card: {
    key: 'weekly_growth_card',
    defaultFormat: 'post_1_1',
    buildSpec: (c, d) => specFor(c, d, { badge: 'WEEKLY GROWTH', brandColor: '#0984E3' }),
  },
  release_card: {
    key: 'release_card',
    defaultFormat: 'post_1_1',
    buildSpec: (c, d) => specFor(c, d, { badge: 'NEW RELEASE', brandColor: '#E17055' }),
  },
  report_cover: {
    key: 'report_cover',
    defaultFormat: 'post_4_5',
    buildSpec: (c, d) => specFor(c, d, { badge: 'REPORT', backgroundColor: '#101018' }),
  },
  media_kit_cover: {
    key: 'media_kit_cover',
    defaultFormat: 'post_4_5',
    buildSpec: (c, d) => specFor(c, d, { badge: 'MEDIA KIT', backgroundColor: '#101018' }),
  },
};

export function isKnownTemplate(key: string): key is TemplateKey {
  return (TEMPLATE_KEYS as readonly string[]).includes(key);
}

export interface ResolvedTemplate {
  key: TemplateKey;
  definition: TemplateDefinition;
  usedFallback: boolean;
}

/** Resolve a template key to its definition, falling back to the generic one. */
export function resolveTemplate(key: string | undefined): ResolvedTemplate {
  if (key && isKnownTemplate(key)) {
    return { key, definition: DEFINITIONS[key], usedFallback: false };
  }
  return {
    key: FALLBACK_TEMPLATE_KEY,
    definition: DEFINITIONS[FALLBACK_TEMPLATE_KEY],
    usedFallback: true,
  };
}

export interface RenderedImage {
  templateKey: TemplateKey;
  usedFallbackTemplate: boolean;
  format: OutputFormat;
  usedFallbackFormat: boolean;
  width: number;
  height: number;
  svg: string;
  png: Buffer;
}

export interface RenderTemplateInput {
  templateKey?: string;
  format?: string;
  content: TemplateContent;
}

/**
 * Resolve template + dimensions, build the SVG and rasterize to PNG. Unknown
 * template keys and formats both fall back safely.
 */
export async function renderTemplate(input: RenderTemplateInput): Promise<RenderedImage> {
  const resolved = resolveTemplate(input.templateKey);
  const dimensions = resolveOutputDimensions(input.format ?? resolved.definition.defaultFormat);
  const spec = resolved.definition.buildSpec(input.content, dimensions);
  const svg = buildSvg(spec);
  const png = await renderSvgToPng(svg, { width: dimensions.width, height: dimensions.height });

  return {
    templateKey: resolved.key,
    usedFallbackTemplate: resolved.usedFallback,
    format: dimensions.format,
    usedFallbackFormat: dimensions.usedFallback,
    width: dimensions.width,
    height: dimensions.height,
    svg,
    png,
  };
}
