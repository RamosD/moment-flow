/**
 * Media kit generation renderer (CR-701).
 *
 * Closes the media_kit_generation cycle, reusing the report strategy:
 *   1. validate the `media_kit` payload (needs at least an artist name —
 *      invalid → controlled `failed` result);
 *   2. build a normalised {@link MediaKitModel} (cover, bio, music/campaign,
 *      highlights, links, contacts/press, listed assets);
 *   3. produce the document — a PDF (pdf-lib) by default, falling back to a
 *      self-contained HTML file when PDF is disabled/unavailable
 *      (`fallback_html: true`);
 *   4. persist the file and return a Django-compatible asset.
 *
 * No public page, no editor, no external uploads, no scraping, no API calls.
 * The document output format is governed by the same `REPORT_OUTPUT_FORMAT`
 * config that report_generation uses.
 */
import { AppError } from '../../errors/errors';
import type { JobEnvelope, RenderOutput, RenderResult } from '../../jobs/job.types';
import type { Renderer, RenderContext } from '../renderer.types';
import { renderMediaKitHtml } from './media-kit.html';
import { buildMediaKitModel, parseMediaKitPayload, type MediaKitModel } from './media-kit.model';
import { renderMediaKitPdf } from './media-kit.pdf';

interface GeneratedDocument {
  data: Buffer;
  format: 'pdf' | 'html';
  fileName: string;
  mimeType: string;
  fallbackHtml: boolean;
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

function htmlDocument(model: MediaKitModel): GeneratedDocument {
  return {
    data: Buffer.from(renderMediaKitHtml(model), 'utf8'),
    format: 'html',
    fileName: 'media_kit.html',
    mimeType: 'text/html',
    fallbackHtml: true,
  };
}

export const renderMediaKitGeneration: Renderer = async (
  envelope: JobEnvelope,
  context: RenderContext,
): Promise<RenderResult> => {
  const { logger, storage, config } = context;
  const targetFormat = config.reportOutputFormat === 'html' ? 'html' : 'pdf';

  // 1. Validate the media-kit payload.
  const parsed = parseMediaKitPayload(envelope.payload);
  if (!parsed.success) {
    const issues = parsed.error.issues.map((issue) => ({
      path: issue.path.map((segment) => String(segment)).join('.'),
      message: issue.message,
    }));
    logger.warn('media_kit.invalid_payload', { issue_count: issues.length });
    return {
      status: 'failed',
      outputs: [
        {
          output_type: 'media_kit',
          format: targetFormat,
          status: 'failed',
          required: true,
          metadata: {
            error: { code: 'invalid_payload', message: 'Invalid media kit payload.' },
            issues,
          },
        },
      ],
    };
  }

  const model = buildMediaKitModel(parsed.data);
  logger.info('media_kit.render_started', {
    target_format: targetFormat,
    highlights: model.highlights.length,
    links: model.links.length,
    assets: model.assets.length,
  });

  // 2. Produce the document (PDF preferred, HTML fallback).
  let doc: GeneratedDocument;
  if (config.reportOutputFormat === 'html') {
    doc = htmlDocument(model);
  } else {
    try {
      doc = {
        data: await renderMediaKitPdf(model),
        format: 'pdf',
        fileName: 'media_kit.pdf',
        mimeType: 'application/pdf',
        fallbackHtml: false,
      };
    } catch (err) {
      // PDF unavailable/failed → fall back to HTML (risk 14.3).
      logger.warn('media_kit.pdf_fallback_html', {
        reason: err instanceof Error ? err.message : 'unknown',
      });
      doc = htmlDocument(model);
    }
  }

  // 3. Persist and return a Django-compatible asset.
  try {
    const asset = await storage.saveBuffer({
      workspaceId: envelope.workspace_id,
      jobId: envelope.job_id,
      fileName: doc.fileName,
      data: doc.data,
      mimeType: doc.mimeType,
    });

    const output: RenderOutput = {
      output_type: 'media_kit',
      format: doc.format,
      status: 'completed',
      title: `${model.artistName} — Media Kit`,
      required: true,
      template_key: 'media_kit_cover',
      asset,
      metadata: {
        artist_name: model.artistName,
        highlight_count: model.highlights.length,
        link_count: model.links.length,
        contact_count: model.contacts.length,
        asset_count: model.assets.length,
        generated_at: model.generatedAt,
        fallback_html: doc.fallbackHtml,
      },
    };

    logger.info('media_kit.render_finished', {
      status: 'completed',
      format: doc.format,
      fallback_html: doc.fallbackHtml,
      file_size_bytes: asset.file_size_bytes,
    });
    return { status: 'completed', outputs: [output] };
  } catch (err) {
    const safe = toSafeError(err);
    logger.error('media_kit.storage_failed', { error_code: safe.code });
    return {
      status: 'failed',
      outputs: [
        {
          output_type: 'media_kit',
          format: doc.format,
          status: 'failed',
          required: true,
          template_key: 'media_kit_cover',
          metadata: { error: safe, artist_name: model.artistName },
        },
      ],
    };
  }
};
