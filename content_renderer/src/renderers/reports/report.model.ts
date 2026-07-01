/**
 * Report payload validation + normalised document model (CR-601).
 *
 * The renderer reads an untrusted `report` payload from the job envelope. This
 * module:
 *   1. validates the payload shape with Zod (`parseReportPayload`) — a report
 *      with no title, no report_type and no sections is rejected as invalid;
 *   2. normalises the validated payload into a {@link ReportModel} that the PDF
 *      and HTML builders render (cover, period, artist/campaign/track, sections,
 *      basic stats, generation date).
 *
 * It intentionally does NOT compute metrics or perform BI — it only presents the
 * data the Backend Core already supplied (smart-link stats, related outputs).
 */
import { z } from 'zod';

import { sanitizeColor } from '../../templates/svg';

const looseObject = z.record(z.string(), z.unknown());

// The Backend Core sends `null` for absent blocks (campaign/artist/track/
// period_*) and an ARRAY for `smart_link_stats` — so every optional field is
// `.nullish()` (null | undefined) and stats accept array-or-object. Unknown keys
// (e.g. `related_outputs`) are stripped, not rejected.
export const reportPayloadSchema = z
  .object({
    report_type: z.string().nullish(),
    title: z.string().nullish(),
    period_start: z.string().nullish(),
    period_end: z.string().nullish(),
    campaign: looseObject.nullish(),
    artist: looseObject.nullish(),
    track: looseObject.nullish(),
    sections: z.array(z.unknown()).nullish(),
    outputs: z.array(z.unknown()).nullish(),
    related_outputs: z.array(z.unknown()).nullish(),
    smart_link: looseObject.nullish(),
    smart_link_stats: z.union([z.array(z.unknown()), looseObject]).nullish(),
    branding: looseObject.nullish(),
  })
  .refine(
    (p) =>
      Boolean(
        (typeof p.title === 'string' && p.title.trim() !== '') ||
          (typeof p.report_type === 'string' && p.report_type.trim() !== '') ||
          (Array.isArray(p.sections) && p.sections.length > 0),
      ),
    { message: 'Report payload must include a title, report_type or at least one section.' },
  );

export type ReportPayload = z.infer<typeof reportPayloadSchema>;

export type ReportParseResult =
  | { success: true; data: ReportPayload }
  | { success: false; error: z.ZodError };

export function parseReportPayload(input: unknown): ReportParseResult {
  const result = reportPayloadSchema.safeParse(input);
  return result.success
    ? { success: true, data: result.data }
    : { success: false, error: result.error };
}

export interface ReportSection {
  heading: string;
  body?: string;
  items: string[];
}

export interface ReportStat {
  label: string;
  value: string;
}

export interface ReportModel {
  reportType: string;
  title: string;
  periodStart?: string;
  periodEnd?: string;
  periodLabel?: string;
  artistName?: string;
  campaignName?: string;
  trackTitle?: string;
  sections: ReportSection[];
  stats: ReportStat[];
  relatedOutputCount: number;
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

/** "weekly_growth" → "Weekly Growth". */
function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildPeriodLabel(start?: string, end?: string): string | undefined {
  if (start && end) {
    return `${start} — ${end}`;
  }
  if (start) {
    return `From ${start}`;
  }
  if (end) {
    return `Until ${end}`;
  }
  return undefined;
}

function normalizeSections(raw: unknown[]): ReportSection[] {
  return raw.map((entry, index) => {
    if (typeof entry === 'string') {
      return { heading: `Section ${index + 1}`, body: entry, items: [] };
    }
    const rec = asRecord(entry);
    const heading =
      firstOf(asString(rec.heading), asString(rec.title), asString(rec.name)) ??
      `Section ${index + 1}`;
    const body = firstOf(asString(rec.body), asString(rec.text), asString(rec.content));
    const itemsRaw = Array.isArray(rec.items)
      ? rec.items
      : Array.isArray(rec.bullets)
        ? rec.bullets
        : [];
    const items = itemsRaw
      .map((item) => asString(item))
      .filter((item): item is string => item !== undefined);
    return { heading, body, items };
  });
}

function normalizeStats(stats: Record<string, unknown>): ReportStat[] {
  const out: ReportStat[] = [];
  for (const [key, val] of Object.entries(stats)) {
    const value = asString(val);
    if (value !== undefined) {
      out.push({ label: humanize(key), value });
    }
  }
  return out;
}

/** Build the normalised, render-ready document model from a validated payload. */
export function buildReportModel(payload: ReportPayload): ReportModel {
  const campaign = asRecord(payload.campaign);
  const artist = asRecord(payload.artist);
  const track = asRecord(payload.track);
  const branding = asRecord(payload.branding);
  const smartLinkStats = asRecord(payload.smart_link_stats);

  const reportType = asString(payload.report_type) ?? 'report';
  const title =
    asString(payload.title) ?? humanize(reportType) ?? 'Report';

  const periodStart = asString(payload.period_start);
  const periodEnd = asString(payload.period_end);

  const sections = normalizeSections(Array.isArray(payload.sections) ? payload.sections : []);
  const stats = normalizeStats(smartLinkStats);
  const relatedOutputCount = Array.isArray(payload.outputs) ? payload.outputs.length : 0;

  const brandColor = sanitizeColor(
    firstOf(
      asString(branding.brand_color),
      asString(branding.primary_color),
      asString(branding.color),
    ),
    '#6C5CE7',
  );

  return {
    reportType,
    title,
    periodStart,
    periodEnd,
    periodLabel: buildPeriodLabel(periodStart, periodEnd),
    artistName: firstOf(
      asString(artist.name),
      asString(artist.display_name),
      asString(artist.stage_name),
    ),
    campaignName: firstOf(asString(campaign.name), asString(campaign.title)),
    trackTitle: firstOf(asString(track.title), asString(track.name)),
    sections,
    stats,
    relatedOutputCount,
    brandColor,
    generatedAt: new Date().toISOString(),
  };
}
