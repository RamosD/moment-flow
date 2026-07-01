/**
 * Self-contained HTML report (CR-602 fallback).
 *
 * Pure string templating with inline CSS — no remote assets, no browser, no JS.
 * Every value coming from the payload is HTML-escaped before being embedded.
 * Used as the report output when PDF generation is unavailable/disabled.
 */
import { escapeHtml, safeCssColor } from '../shared/html';
import type { ReportModel } from './report.model';

// Re-exported for API stability (previously defined here).
export { escapeHtml } from '../shared/html';

function renderMetaRow(label: string, value?: string): string {
  if (!value) {
    return '';
  }
  return `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`;
}

/** Build a complete, standalone HTML document for the report model. */
export function renderReportHtml(model: ReportModel): string {
  const brand = safeCssColor(model.brandColor);

  const metaRows = [
    renderMetaRow('Report type', model.reportType),
    renderMetaRow('Period', model.periodLabel),
    renderMetaRow('Artist', model.artistName),
    renderMetaRow('Campaign', model.campaignName),
    renderMetaRow('Track', model.trackTitle),
  ]
    .filter(Boolean)
    .join('');

  const statsBlock =
    model.stats.length > 0
      ? `<section class="stats"><h2>Statistics</h2><table>${model.stats
          .map(
            (stat) =>
              `<tr><th>${escapeHtml(stat.label)}</th><td>${escapeHtml(stat.value)}</td></tr>`,
          )
          .join('')}</table></section>`
      : '';

  const sectionsBlock = model.sections
    .map((section) => {
      const body = section.body ? `<p>${escapeHtml(section.body)}</p>` : '';
      const items =
        section.items.length > 0
          ? `<ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
          : '';
      return `<section class="report-section"><h2>${escapeHtml(section.heading)}</h2>${body}${items}</section>`;
    })
    .join('');

  return [
    '<!DOCTYPE html>',
    '<html lang="en">',
    '<head>',
    '<meta charset="utf-8"/>',
    '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
    `<title>${escapeHtml(model.title)}</title>`,
    '<style>',
    `:root{--brand:${brand};}`,
    'body{font-family:Arial,Helvetica,sans-serif;color:#1a1a22;margin:0;background:#f4f4f7;}',
    '.cover{background:var(--brand);color:#fff;padding:48px 40px;}',
    '.cover h1{margin:0;font-size:32px;}',
    '.cover .period{margin-top:8px;font-size:15px;opacity:.92;}',
    'main{max-width:820px;margin:0 auto;padding:32px 40px;}',
    'table{border-collapse:collapse;width:100%;margin:8px 0 24px;}',
    'th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #e2e2ea;font-size:14px;}',
    'th{width:160px;color:#55555f;font-weight:600;}',
    'h2{font-size:18px;margin:24px 0 8px;color:var(--brand);}',
    '.report-section p{margin:4px 0;line-height:1.5;}',
    'ul{margin:6px 0;padding-left:20px;}',
    'footer{max-width:820px;margin:0 auto;padding:16px 40px 48px;color:#88888f;font-size:12px;}',
    '</style>',
    '</head>',
    '<body>',
    `<header class="cover"><h1>${escapeHtml(model.title)}</h1>${
      model.periodLabel ? `<div class="period">${escapeHtml(model.periodLabel)}</div>` : ''
    }</header>`,
    '<main>',
    metaRows ? `<table>${metaRows}</table>` : '',
    statsBlock,
    sectionsBlock,
    '</main>',
    `<footer>Generated at ${escapeHtml(model.generatedAt)} · content_renderer</footer>`,
    '</body>',
    '</html>',
  ].join('');
}
