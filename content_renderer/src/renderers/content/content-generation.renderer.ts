/**
 * Content generation renderer (CR-501 / CR-502 / CR-802).
 *
 * Closes the real content_generation cycle:
 *   1. read the domain payload (campaign, artist, track, content_pack,
 *      templates, expected_outputs, branding, smart_link, billing_context,
 *      metadata);
 *   2. derive the list of outputs to produce — from `expected_outputs` when
 *      present, otherwise from the content pack's defaults, otherwise a single
 *      generic fallback so a job NEVER produces zero outputs;
 *   3. for each output: select a template by `template_key` (registry fallback
 *      when unknown), resolve format/dimensions, build the SVG, rasterize to PNG
 *      (Sharp) and persist via the storage backend;
 *   4. return Django-compatible `result.outputs` and an overall job status.
 *
 * Partial success (CR-802): each output is rendered independently. A failing
 * output is reported with `status: "failed"` and a safe error in its metadata,
 * without aborting the others. The aggregate status is:
 *   - `completed`            — every output was generated (no failures);
 *   - `partially_completed`  — at least one output generated AND at least one failed;
 *   - `failed`               — no output could be generated.
 *
 * The renderer NEVER decides product rules (permissions, plan, billing). It only
 * generates assets and reports the technical outcome. `billing_context` is read
 * for traceability but never acted upon.
 */
import { AppError } from '../../errors/errors';
import type {
  AssetMetadata,
  JobEnvelope,
  JobStatus,
  RenderOutput,
  RenderResult,
} from '../../jobs/job.types';
import { resolveOutputDimensions } from '../../templates/dimensions';
import { renderTemplate, resolveTemplate } from '../../templates/registry';
import type { Renderer, RenderContext } from '../renderer.types';

/** A resolved instruction for a single output to render. */
interface OutputSpec {
  output_type: string;
  template_key: string;
  /** Template id as received in the request (never invented). */
  template_id?: string;
  /** Social format / dimension key (e.g. `post_1_1`). */
  format: string;
  required: boolean;
  title?: string;
  caption?: string;
  cta?: string;
  metric?: string;
  metadata: Record<string, unknown>;
}

/**
 * Default outputs per supported content pack (CR-502). Each entry is a minimal,
 * predictable single card. `auto_media_kit` is supported as a simple fallback
 * cover only when it arrives as a content pack.
 */
const PACK_DEFAULTS: Record<string, ReadonlyArray<Omit<OutputSpec, 'metadata'>>> = {
  release_pack: [
    { output_type: 'post', template_key: 'release_card', format: 'post_1_1', required: true },
  ],
  milestone_pack: [
    { output_type: 'post', template_key: 'milestone_card', format: 'post_1_1', required: true },
  ],
  weekly_growth_pack: [
    { output_type: 'post', template_key: 'weekly_growth_card', format: 'post_1_1', required: true },
  ],
  monthly_recap_pack: [
    { output_type: 'post', template_key: 'generic_post', format: 'post_1_1', required: true },
  ],
  auto_media_kit: [
    { output_type: 'cover', template_key: 'media_kit_cover', format: 'post_4_5', required: false },
  ],
};

/** Used when there is no content pack match and no expected outputs. */
const FALLBACK_SPEC: Omit<OutputSpec, 'metadata'> = {
  output_type: 'post',
  template_key: 'generic_post',
  format: 'post_1_1',
  required: true,
};

// --- payload coercion helpers (defensive: the payload is untrusted input) ----

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
  return undefined;
}

function asBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

/** Extract the content pack key from a string or an object (several aliases). */
function extractPackKey(contentPack: unknown): string | undefined {
  if (typeof contentPack === 'string') {
    return asString(contentPack);
  }
  const rec = asRecord(contentPack);
  return (
    asString(rec.type) ??
    asString(rec.key) ??
    asString(rec.pack) ??
    asString(rec.pack_type) ??
    asString(rec.slug)
  );
}

/** Build a lookup of `template_key` → payload-provided template overrides. */
function indexTemplates(templates: unknown): Map<string, Record<string, unknown>> {
  const map = new Map<string, Record<string, unknown>>();
  if (Array.isArray(templates)) {
    for (const entry of templates) {
      const rec = asRecord(entry);
      const key = asString(rec.template_key) ?? asString(rec.key);
      if (key) {
        map.set(key, rec);
      }
    }
  } else {
    for (const [key, val] of Object.entries(asRecord(templates))) {
      map.set(key, asRecord(val));
    }
  }
  return map;
}

/** Normalise a single payload `expected_output` into an {@link OutputSpec}. */
function readExpectedOutput(raw: unknown, fallbackTemplate: string): OutputSpec {
  const rec = asRecord(raw);
  return {
    output_type: asString(rec.output_type) ?? 'post',
    template_key: asString(rec.template_key) ?? fallbackTemplate,
    // Preserve a template id ONLY if the request carried one (never invent it).
    template_id: asString(rec.template_id) ?? asString(rec.template_uuid) ?? asString(rec.id),
    // Accept several aliases for the social format/dimension; unknown values
    // resolve to a safe fallback later, so this never hard-fails.
    format: asString(rec.format) ?? asString(rec.dimension) ?? asString(rec.size) ?? 'post_1_1',
    required: asBoolean(rec.required) ?? true,
    title: asString(rec.title),
    caption: asString(rec.caption),
    cta: asString(rec.cta),
    metric: asString(rec.metric),
    metadata: asRecord(rec.metadata),
  };
}

/** Map any thrown value to a safe, secret-free error descriptor. */
function toSafeError(err: unknown): { code: string; message: string } {
  if (err instanceof AppError) {
    return { code: err.code, message: err.message };
  }
  return {
    code: 'render_failed',
    message: err instanceof Error ? err.message : 'Unknown render error.',
  };
}

/** First non-empty string from the candidates, or undefined. */
function firstOf(...candidates: Array<string | undefined>): string | undefined {
  for (const candidate of candidates) {
    if (candidate) {
      return candidate;
    }
  }
  return undefined;
}

export const renderContentGeneration: Renderer = async (
  envelope: JobEnvelope,
  context: RenderContext,
): Promise<RenderResult> => {
  const { logger, storage } = context;
  const payload = asRecord(envelope.payload);

  // 1. Read the domain payload.
  const campaign = asRecord(payload.campaign);
  const artist = asRecord(payload.artist);
  const track = asRecord(payload.track);
  const branding = asRecord(payload.branding);
  const smartLink = asRecord(payload.smart_link);
  const contentPack = payload.content_pack;
  const packKey = extractPackKey(contentPack);
  const templateOverrides = indexTemplates(payload.templates);

  const campaignName = firstOf(asString(campaign.name), asString(campaign.title));
  const artistName = firstOf(
    asString(artist.name),
    asString(artist.display_name),
    asString(artist.stage_name),
  );
  const trackTitle = firstOf(asString(track.title), asString(track.name));
  const brandColor = firstOf(
    asString(branding.brand_color),
    asString(branding.primary_color),
    asString(branding.color),
  );
  const smartLinkUrl = firstOf(
    asString(smartLink.url),
    asString(smartLink.short_url),
    asString(smartLink.href),
  );
  const packMetric = firstOf(asString(asRecord(contentPack).metric), asString(payload.metric));

  // 2. Decide which outputs to produce (CR-502 + "never zero outputs").
  const packPrimaryTemplate = PACK_DEFAULTS[packKey ?? '']?.[0]?.template_key ?? 'generic_post';
  const expectedOutputs = Array.isArray(payload.expected_outputs) ? payload.expected_outputs : [];

  let specs: OutputSpec[];
  if (expectedOutputs.length > 0) {
    specs = expectedOutputs.map((raw) => readExpectedOutput(raw, packPrimaryTemplate));
  } else {
    const defaults = PACK_DEFAULTS[packKey ?? ''] ?? [FALLBACK_SPEC];
    specs = defaults.map((d) => ({ ...d, metadata: {} }));
  }
  if (specs.length === 0) {
    specs = [{ ...FALLBACK_SPEC, metadata: {} }];
  }

  logger.info('content.render_started', {
    content_pack: packKey ?? null,
    output_count: specs.length,
    from_expected_outputs: expectedOutputs.length > 0,
  });

  // 3. Render each output independently (partial success — CR-802).
  const outputs = await Promise.all(
    specs.map((spec, index) => renderOne(spec, index)),
  );

  // 4. Aggregate the overall status.
  const generated = outputs.filter((o) => o.status === 'completed');
  const failed = outputs.filter((o) => o.status === 'failed');
  let status: JobStatus;
  if (generated.length === 0) {
    status = 'failed';
  } else if (failed.length === 0) {
    status = 'completed';
  } else {
    status = 'partially_completed';
  }

  logger.info('content.render_finished', {
    status,
    generated: generated.length,
    failed: failed.length,
  });

  return { status, outputs };

  /** Render a single output, never throwing — failures become a failed output. */
  async function renderOne(spec: OutputSpec, index: number): Promise<RenderOutput> {
    const fileName = `output_${String(index + 1).padStart(3, '0')}.png`;
    const override = templateOverrides.get(spec.template_key) ?? {};

    const title = firstOf(
      spec.title,
      asString(override.title),
      trackTitle,
      campaignName,
      artistName,
      'ChartRex',
    );
    const caption = firstOf(spec.caption, asString(override.caption), campaignName);
    const cta = firstOf(spec.cta, asString(override.cta), smartLinkUrl ? 'Listen now' : undefined);
    const metric = firstOf(spec.metric, packMetric);

    // Resolve template + dimensions up-front so the template-echo metadata
    // (R-HARD-004) is identical on the success and failure paths. The registry
    // resolution here matches what `renderTemplate` does internally.
    const resolved = resolveTemplate(spec.template_key);
    const dims = resolveOutputDimensions(spec.format);
    // Echo a template id ONLY if the request carried one (payload templates[] or
    // expected_outputs[]). Never invented — the registry has no ids of its own.
    const requestedTemplateId = firstOf(spec.template_id, asString(override.template_id));

    // Template resolution metadata, shared by both outcomes.
    const templateMeta: Record<string, unknown> = {
      requested_template_key: spec.template_key,
      resolved_template_key: resolved.key,
      used_fallback_template: resolved.usedFallback,
      used_fallback_format: dims.usedFallback,
      dimension: dims.format,
      width: dims.width,
      height: dims.height,
      ...(requestedTemplateId ? { requested_template_id: requestedTemplateId } : {}),
    };
    // Top-level template id, only when received (Django resolves Template by it).
    const templateIdField = requestedTemplateId ? { template_id: requestedTemplateId } : {};

    try {
      const image = await renderTemplate({
        templateKey: spec.template_key,
        format: spec.format,
        content: {
          title,
          subtitle: caption,
          artistName,
          trackTitle,
          campaignName,
          metric,
          brandColor,
        },
      });

      const asset: AssetMetadata = await storage.saveBuffer({
        workspaceId: envelope.workspace_id,
        jobId: envelope.job_id,
        fileName,
        data: image.png,
        mimeType: 'image/png',
        width: image.width,
        height: image.height,
      });

      return {
        output_type: spec.output_type,
        format: 'png',
        status: 'completed',
        title,
        caption,
        cta,
        required: spec.required,
        // The template actually used (== resolved.key).
        template_key: image.templateKey,
        ...templateIdField,
        asset,
        metadata: {
          ...spec.metadata,
          content_pack: packKey ?? null,
          ...templateMeta,
          ...(smartLinkUrl ? { smart_link_url: smartLinkUrl } : {}),
        },
      };
    } catch (err) {
      const safe = toSafeError(err);
      logger.error('content.output_failed', {
        file_name: fileName,
        output_type: spec.output_type,
        template_key: spec.template_key,
        error_code: safe.code,
      });
      return {
        output_type: spec.output_type,
        format: 'png',
        status: 'failed',
        title,
        caption,
        cta,
        required: spec.required,
        // Best compatible value for Django (resolved, never an unknown key).
        template_key: resolved.key,
        ...templateIdField,
        metadata: {
          ...spec.metadata,
          content_pack: packKey ?? null,
          ...templateMeta,
          error: safe,
        },
      };
    }
  }
};
