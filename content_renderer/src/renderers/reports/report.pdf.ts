/**
 * Simple PDF report (CR-601) built on the shared {@link createPdfDoc} toolkit
 * (`pdf-lib`, no browser). The toolkit handles dynamic loading, layout and
 * pagination; this module only maps the {@link ReportModel} onto it.
 *
 * Throws if `pdf-lib` is unavailable — the caller falls back to HTML (CR-602).
 */
import { createPdfDoc } from '../shared/pdf-doc';
import type { ReportModel } from './report.model';

/** Render the report model to a PDF buffer. */
export async function renderReportPdf(model: ReportModel): Promise<Buffer> {
  const pdf = await createPdfDoc(model.brandColor);

  pdf.cover(model.title || 'Report', model.periodLabel);

  const meta: Array<[string, string | undefined]> = [
    ['Report type', model.reportType],
    ['Artist', model.artistName],
    ['Campaign', model.campaignName],
    ['Track', model.trackTitle],
  ];
  for (const [label, value] of meta) {
    if (value) {
      pdf.meta(label, value);
    }
  }

  if (model.stats.length > 0) {
    pdf.gap(10);
    pdf.heading('Statistics');
    for (const stat of model.stats) {
      pdf.line(`${stat.label}: ${stat.value}`, { indent: 12 });
    }
  }

  for (const section of model.sections) {
    pdf.gap(12);
    pdf.heading(section.heading);
    if (section.body) {
      pdf.line(section.body);
    }
    for (const item of section.items) {
      pdf.bullet(item);
    }
  }

  pdf.gap(18);
  pdf.footnote(`Generated at ${model.generatedAt}`);

  return pdf.save();
}
