/**
 * Media kit payload validation + normalised document model (CR-701).
 *
 * Reads an untrusted `media_kit` payload (artist, optional campaign/track,
 * items, assets, smart links, branding, metadata), validates that there is at
 * least an artist name, and normalises everything into a {@link MediaKitModel}
 * the PDF/HTML builders present. No external calls, no scraping — it only shows
 * what the Backend Core supplied.
 */
import { z } from 'zod';

import { sanitizeColor } from '../../templates/svg';

const looseObject = z.record(z.string(), z.unknown());

// The Backend Core sends `null` for absent blocks (campaign/track), so every
// optional field is `.nullish()` (null | undefined). Unknown keys (e.g. a
// top-level `title`) are stripped, not rejected.
export const mediaKitPayloadSchema = z
  .object({
    artist: looseObject.nullish(),
    campaign: looseObject.nullish(),
    track: looseObject.nullish(),
    items: z.array(z.unknown()).nullish(),
    assets: z.array(z.unknown()).nullish(),
    // Smart links may arrive as an array or a label→url object.
    smart_links: z.union([z.array(z.unknown()), looseObject]).nullish(),
    branding: looseObject.nullish(),
    metadata: looseObject.nullish(),
  })
  .refine((p) => extractArtistName(p.artist) !== undefined, {
    message: 'Media kit payload must include an artist name.',
  });

export type MediaKitPayload = z.infer<typeof mediaKitPayloadSchema>;

export type MediaKitParseResult =
  | { success: true; data: MediaKitPayload }
  | { success: false; error: z.ZodError };

export function parseMediaKitPayload(input: unknown): MediaKitParseResult {
  const result = mediaKitPayloadSchema.safeParse(input);
  return result.success
    ? { success: true, data: result.data }
    : { success: false, error: result.error };
}

export interface MediaKitLink {
  label: string;
  url: string;
}

export interface MediaKitContact {
  label: string;
  value: string;
}

export interface MediaKitAsset {
  label: string;
  detail?: string;
}

export interface MediaKitModel {
  artistName: string;
  tagline?: string;
  bio?: string;
  campaignName?: string;
  trackTitle?: string;
  highlights: string[];
  links: MediaKitLink[];
  contacts: MediaKitContact[];
  assets: MediaKitAsset[];
  brandColor: string;
  generatedAt: string;
}

// --- coercion helpers (payload is untrusted) ---------------------------------

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asString(value: unknown): string | undefined {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed === '' ? undefined : trimmed;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  return undefined;
}

function firstOf(...candidates: Array<string | undefined>): string | undefined {
  for (const candidate of candidates) {
    if (candidate) {
      return candidate;
    }
  }
  return undefined;
}

function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function extractArtistName(artist: unknown): string | undefined {
  const rec = asRecord(artist);
  return firstOf(
    asString(rec.name),
    asString(rec.display_name),
    asString(rec.stage_name),
    asString(rec.artist_name),
  );
}

function normalizeHighlights(items: unknown[]): string[] {
  const out: string[] = [];
  for (const item of items) {
    if (typeof item === 'string') {
      const text = asString(item);
      if (text) {
        out.push(text);
      }
      continue;
    }
    const rec = asRecord(item);
    const label = firstOf(asString(rec.title), asString(rec.label), asString(rec.name));
    const detail = firstOf(asString(rec.description), asString(rec.text), asString(rec.value));
    if (label && detail) {
      out.push(`${label} — ${detail}`);
    } else if (label) {
      out.push(label);
    } else if (detail) {
      out.push(detail);
    }
  }
  return out;
}

function normalizeLinks(smartLinks: unknown, artist: Record<string, unknown>): MediaKitLink[] {
  const links: MediaKitLink[] = [];

  const pushFrom = (entry: unknown, fallbackLabel?: string): void => {
    if (typeof entry === 'string') {
      const url = asString(entry);
      if (url) {
        links.push({ label: fallbackLabel ?? url, url });
      }
      return;
    }
    const rec = asRecord(entry);
    const url = firstOf(asString(rec.url), asString(rec.href), asString(rec.short_url));
    if (url) {
      const label = firstOf(
        asString(rec.label),
        asString(rec.title),
        asString(rec.name),
        asString(rec.platform),
        fallbackLabel,
      );
      links.push({ label: label ?? url, url });
    }
  };

  if (Array.isArray(smartLinks)) {
    for (const entry of smartLinks) {
      pushFrom(entry);
    }
  } else if (smartLinks && typeof smartLinks === 'object') {
    for (const [key, value] of Object.entries(smartLinks as Record<string, unknown>)) {
      if (typeof value === 'string') {
        pushFrom(value, humanize(key));
      } else {
        pushFrom(value, humanize(key));
      }
    }
  }

  // Optional artist.links (array or label→url object).
  const artistLinks = artist.links;
  if (Array.isArray(artistLinks)) {
    for (const entry of artistLinks) {
      pushFrom(entry);
    }
  } else if (artistLinks && typeof artistLinks === 'object') {
    for (const [key, value] of Object.entries(artistLinks as Record<string, unknown>)) {
      pushFrom(value, humanize(key));
    }
  }

  return links;
}

const CONTACT_KEYS = ['email', 'phone', 'management', 'booking', 'press', 'label', 'website'];

function normalizeContacts(artist: Record<string, unknown>): MediaKitContact[] {
  const contacts: MediaKitContact[] = [];
  const seen = new Set<string>();

  const add = (label: string, value: string | undefined): void => {
    if (value && !seen.has(`${label}:${value}`)) {
      seen.add(`${label}:${value}`);
      contacts.push({ label, value });
    }
  };

  // Nested artist.contact / artist.press objects.
  for (const container of [asRecord(artist.contact), asRecord(artist.press)]) {
    for (const [key, val] of Object.entries(container)) {
      add(humanize(key), asString(val));
    }
  }

  // Well-known scalar keys directly on the artist object.
  for (const key of CONTACT_KEYS) {
    add(humanize(key), asString(artist[key]));
  }

  return contacts;
}

function normalizeAssets(assets: unknown[]): MediaKitAsset[] {
  const out: MediaKitAsset[] = [];
  for (const asset of assets) {
    if (typeof asset === 'string') {
      const label = asString(asset);
      if (label) {
        out.push({ label });
      }
      continue;
    }
    const rec = asRecord(asset);
    const label = firstOf(
      asString(rec.file_name),
      asString(rec.name),
      asString(rec.title),
      asString(rec.label),
    );
    const detail = firstOf(asString(rec.type), asString(rec.mime_type), asString(rec.kind));
    if (label) {
      out.push(detail ? { label, detail } : { label });
    }
  }
  return out;
}

/** Build the normalised, render-ready media-kit model from a validated payload. */
export function buildMediaKitModel(payload: MediaKitPayload): MediaKitModel {
  const artist = asRecord(payload.artist);
  const campaign = asRecord(payload.campaign);
  const track = asRecord(payload.track);
  const branding = asRecord(payload.branding);

  const artistName = extractArtistName(artist) ?? 'Artist';
  const campaignName = firstOf(asString(campaign.name), asString(campaign.title));
  const trackTitle = firstOf(asString(track.title), asString(track.name));

  const brandColor = sanitizeColor(
    firstOf(
      asString(branding.brand_color),
      asString(branding.primary_color),
      asString(branding.color),
    ),
    '#6C5CE7',
  );

  return {
    artistName,
    tagline: firstOf(asString(artist.tagline), asString(artist.headline), campaignName),
    bio: firstOf(asString(artist.bio), asString(artist.biography), asString(artist.description)),
    campaignName,
    trackTitle,
    highlights: normalizeHighlights(Array.isArray(payload.items) ? payload.items : []),
    links: normalizeLinks(payload.smart_links, artist),
    contacts: normalizeContacts(artist),
    assets: normalizeAssets(Array.isArray(payload.assets) ? payload.assets : []),
    brandColor,
    generatedAt: new Date().toISOString(),
  };
}
