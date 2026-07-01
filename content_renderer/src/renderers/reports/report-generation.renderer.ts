/**
 * Report generation renderer (CR-601 / CR-602).
 *
 * Closes the report_generation cycle:
 *   1. validate the `report` payload (invalid → controlled `failed` result);
 *   2. build a normalised {@link ReportModel} (cover, period, artist/campaign/
 *      track, sections, basic stats, generation date);
 *   3. produce the document — a PDF (pdf-lib) by default, falling back to a
 *      self-contained HTML file when PDF is disabled or unavailable
 *      (`fallback_html: true`);
 *   4. persist the file and return a Django-compatible asset.
 *
 * No charts, no BI, no metric computation — the renderer only presents the data
 * Django supplied. Failures (invalid payload, storage error) are returned as a
 * `failed` {@link RenderResult}; the dispatcher turns that into a `failed`
 * callback. PDF dependency problems are non-fatal (HTML fallback).
 */
import { AppError } from '../../errors/errors';
import type { JobEnvelope, RenderOutput, RenderResult } from '../../jobs/job.types';
import type { Renderer, RenderContext } from '../renderer.types';
import { renderReportHtml } from './report.html';
import { buildReportModel, parseReportPayload, type ReportModel } from './report.model';
import { renderReportPdf } from './report.pdf';

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

function htmlDocument(model: ReportModel): GeneratedDocument {
  return {
    data: Buffer.from(renderReportHtml(model), 'utf8'),
    format: 'html',
    fileName: 'report.html',
    mimeType: 'text/html',
    fallbackHtml: true,
  };
}

export const renderReportGeneration: Renderer = async (
  envelope: JobEnvelope,
  context: RenderContext,
): Promise<RenderResult> => {
  const { logger, storage, config } = context;
  const targetFormat = config.reportOutputFormat === 'html' ? 'html' : 'pdf';

  // 1. Validate the report payload.
  const parsed = parseReportPayload(envelope.payload);
  if (!parsed.success) {
    const issues = parsed.error.issues.map((issue) => ({
      path: issue.path.map((segment) => String(segment)).join('.'),
      message: issue.message,
    }));
    logger.warn('report.invalid_payload', { issue_count: issues.length });
    return {
      status: 'failed',
      outputs: [
        {
          output_type: 'report',
          format: targetFormat,
          status: 'failed',
          required: true,
          metadata: {
            error: { code: 'invalid_payload', message: 'Invalid report payload.' },
            issues,
          },
        },
      ],
    };
  }

  const model = buildReportModel(parsed.data);
  logger.info('report.render_started', {
    report_type: model.reportType,
    target_format: targetFormat,
    sections: model.sections.length,
    stats: model.stats.length,
  });

  // 2. Produce the document (PDF preferred, HTML fallback).
  let doc: GeneratedDocument;
  if (config.reportOutputFormat === 'html') {
    doc = htmlDocument(model);
  } else {
    try {
      doc = {
        data: await renderReportPdf(model),
        format: 'pdf',
        fileName: 'report.pdf',
        mimeType: 'application/pdf',
        fallbackHtml: false,
      };
    } catch (err) {
      // PDF unavailable/failed → fall back to HTML (CR-602, risk 14.3).
      logger.warn('report.pdf_fallback_html', {
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
      output_type: 'report',
      format: doc.format,
      status: 'completed',
      title: model.title,
      required: true,
      template_key: 'report_cover',
      asset,
      metadata: {
        report_type: model.reportType,
        period_start: model.periodStart ?? null,
        period_end: model.periodEnd ?? null,
        section_count: model.sections.length,
        stat_count: model.stats.length,
        related_output_count: model.relatedOutputCount,
        generated_at: model.generatedAt,
        fallback_html: doc.fallbackHtml,
      },
    };

    logger.info('report.render_finished', {
      status: 'completed',
      format: doc.format,
      fallback_html: doc.fallbackHtml,
      file_size_bytes: asset.file_size_bytes,
    });
    return { status: 'completed', outputs: [output] };
  } catch (err) {
    const safe = toSafeError(err);
    logger.error('report.storage_failed', { error_code: safe.code });
    return {
      status: 'failed',
      outputs: [
        {
          output_type: 'report',
          format: doc.format,
          status: 'failed',
          required: true,
          template_key: 'report_cover',
          metadata: { error: safe, report_type: model.reportType },
        },
      ],
    };
  }
};
