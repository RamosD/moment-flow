/**
 * Simple, reusable PDF document builder (CR-601 / CR-701).
 *
 * Wraps `pdf-lib` (imported dynamically so the service still boots and callers
 * can fall back to HTML when PDF is unavailable — backlog risk 14.3) behind a
 * tiny layout API: a brand-coloured cover band, headings, body text, bullets,
 * key/value meta rows and a footnote, with greedy word-wrap and A4 pagination.
 *
 * Shared by the report and media-kit renderers so the "PDF or HTML fallback"
 * strategy lives in one place. No charts, no images, no BI.
 */
import {
  A4_HEIGHT,
  A4_WIDTH,
  DEFAULT_BRAND,
  PAGE_MARGIN,
  hexToRgb01,
  toPdfText,
  wrapText,
  type Rgb,
} from './pdf-primitives';

const HEADER_HEIGHT = 130;
const CONTENT_WIDTH = A4_WIDTH - PAGE_MARGIN * 2;
const TEXT_COLOR: Rgb = { r: 0.1, g: 0.1, b: 0.13 };
const MUTED_COLOR: Rgb = { r: 0.53, g: 0.53, b: 0.56 };

export interface LineOptions {
  size?: number;
  bold?: boolean;
  /** Use the brand colour for the text. */
  brand?: boolean;
  /** Use the muted grey colour for the text. */
  muted?: boolean;
  indent?: number;
}

export interface PdfDoc {
  /** Brand-coloured cover band with a title and optional subtitle. */
  cover(title: string, subtitle?: string): void;
  /** Section heading (bold, brand colour). */
  heading(text: string): void;
  /** Body line(s), word-wrapped. */
  line(text: string, options?: LineOptions): void;
  /** A `- ` bulleted, indented line. */
  bullet(text: string): void;
  /** A `label: value` metadata row. */
  meta(label: string, value: string): void;
  /** Small muted footnote line. */
  footnote(text: string): void;
  /** Add vertical space. */
  gap(amount: number): void;
  /** Serialise to a PDF buffer. */
  save(): Promise<Buffer>;
}

/**
 * Create a {@link PdfDoc}. Throws if `pdf-lib` cannot be loaded — callers catch
 * this and fall back to HTML.
 */
export async function createPdfDoc(brandColorHex: string): Promise<PdfDoc> {
  const { PDFDocument, StandardFonts, rgb } = await import('pdf-lib');

  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const brand = hexToRgb01(brandColorHex, DEFAULT_BRAND);
  const toColor = (c: Rgb) => rgb(c.r, c.g, c.b);

  let page = doc.addPage([A4_WIDTH, A4_HEIGHT]);
  let cursorY = A4_HEIGHT - PAGE_MARGIN;

  const ensureSpace = (needed: number): void => {
    if (cursorY - needed < PAGE_MARGIN) {
      page = doc.addPage([A4_WIDTH, A4_HEIGHT]);
      cursorY = A4_HEIGHT - PAGE_MARGIN;
    }
  };

  const line = (text: string, options: LineOptions = {}): void => {
    const clean = toPdfText(text);
    if (!clean) {
      return;
    }
    const size = options.size ?? 12;
    const usedFont = options.bold ? bold : font;
    const colorRgb = options.brand ? brand : options.muted ? MUTED_COLOR : TEXT_COLOR;
    const indent = options.indent ?? 0;
    for (const wrapped of wrapText(clean, usedFont, size, CONTENT_WIDTH - indent)) {
      ensureSpace(size * 1.5);
      page.drawText(wrapped, {
        x: PAGE_MARGIN + indent,
        y: cursorY - size,
        size,
        font: usedFont,
        color: toColor(colorRgb),
      });
      cursorY -= size * 1.5;
    }
  };

  return {
    cover(title: string, subtitle?: string): void {
      page.drawRectangle({
        x: 0,
        y: A4_HEIGHT - HEADER_HEIGHT,
        width: A4_WIDTH,
        height: HEADER_HEIGHT,
        color: toColor(brand),
      });
      page.drawText(toPdfText(title) || 'Document', {
        x: PAGE_MARGIN,
        y: A4_HEIGHT - 78,
        size: 26,
        font: bold,
        color: rgb(1, 1, 1),
      });
      const cleanSubtitle = subtitle ? toPdfText(subtitle) : '';
      if (cleanSubtitle) {
        page.drawText(cleanSubtitle, {
          x: PAGE_MARGIN,
          y: A4_HEIGHT - 106,
          size: 12,
          font,
          color: rgb(1, 1, 1),
        });
      }
      cursorY = A4_HEIGHT - HEADER_HEIGHT - 30;
    },
    heading(text: string): void {
      line(text, { size: 15, bold: true, brand: true });
    },
    line,
    bullet(text: string): void {
      line(`- ${text}`, { indent: 12 });
    },
    meta(label: string, value: string): void {
      line(`${label}: ${value}`);
    },
    footnote(text: string): void {
      line(text, { size: 10, muted: true });
    },
    gap(amount: number): void {
      cursorY -= amount;
    },
    async save(): Promise<Buffer> {
      const bytes = await doc.save();
      return Buffer.from(bytes);
    },
  };
}
