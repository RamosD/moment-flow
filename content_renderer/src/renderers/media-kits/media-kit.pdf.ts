/**
 * Simple PDF media kit (CR-701) built on the shared {@link createPdfDoc} toolkit
 * (`pdf-lib`, no browser). Reuses the exact "PDF or HTML fallback" strategy of
 * report_generation; this module only maps the {@link MediaKitModel} onto the
 * toolkit.
 *
 * Throws if `pdf-lib` is unavailable — the caller falls back to HTML.
 */
import { createPdfDoc } from '../shared/pdf-doc';
import type { MediaKitModel } from './media-kit.model';

/** Render the media-kit model to a PDF buffer. */
export async function renderMediaKitPdf(model: MediaKitModel): Promise<Buffer> {
  const pdf = await createPdfDoc(model.brandColor);

  pdf.cover(model.artistName, model.tagline);

  if (model.bio) {
    pdf.line(model.bio);
  }

  const featured = [model.trackTitle, model.campaignName].filter(Boolean).join('  ·  ');
  if (featured) {
    pdf.gap(6);
    pdf.meta('Featured', featured);
  }

  if (model.highlights.length > 0) {
    pdf.gap(12);
    pdf.heading('Highlights');
    for (const highlight of model.highlights) {
      pdf.bullet(highlight);
    }
  }

  if (model.links.length > 0) {
    pdf.gap(12);
    pdf.heading('Links');
    for (const link of model.links) {
      pdf.bullet(`${link.label}: ${link.url}`);
    }
  }

  if (model.contacts.length > 0) {
    pdf.gap(12);
    pdf.heading('Contact');
    for (const contact of model.contacts) {
      pdf.meta(contact.label, contact.value);
    }
  }

  if (model.assets.length > 0) {
    pdf.gap(12);
    pdf.heading('Assets');
    for (const asset of model.assets) {
      pdf.bullet(asset.detail ? `${asset.label} (${asset.detail})` : asset.label);
    }
  }

  pdf.gap(18);
  pdf.footnote(`Generated at ${model.generatedAt}`);

  return pdf.save();
}
