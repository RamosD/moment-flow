/**
 * Self-contained HTML media kit (CR-701 / CR-602 fallback).
 *
 * Pure string templating with inline CSS — no remote assets, no JS, no public
 * page. Every payload value is HTML-escaped; link URLs pass through `safeUrl`
 * so only http(s)/mailto schemes are emitted.
 */
import { escapeHtml, safeCssColor, safeUrl } from '../shared/html';
import type { MediaKitModel } from './media-kit.model';

function metaRow(label: string, value?: string): string {
  return value ? `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>` : '';
}

function section(title: string, inner: string): string {
  return inner ? `<section class="mk-section"><h2>${escapeHtml(title)}</h2>${inner}</section>` : '';
}

/** Build a complete, standalone HTML document for the media-kit model. */
export function renderMediaKitHtml(model: MediaKitModel): string {
  const brand = safeCssColor(model.brandColor);

  const featured = [model.trackTitle, model.campaignName].filter(Boolean).join(' · ');

  const metaTable = [metaRow('Featured', featured)].filter(Boolean).join('');

  const highlights =
    model.highlights.length > 0
      ? `<ul>${model.highlights.map((h) => `<li>${escapeHtml(h)}</li>`).join('')}</ul>`
      : '';

  const links =
    model.links.length > 0
      ? `<ul class="mk-links">${model.links
          .map((link) => {
            const url = safeUrl(link.url);
            const label = escapeHtml(link.label);
            return url
              ? `<li><a href="${escapeHtml(url)}">${label}</a></li>`
              : `<li>${label}: ${escapeHtml(link.url)}</li>`;
          })
          .join('')}</ul>`
      : '';

  const contacts =
    model.contacts.length > 0
      ? `<table>${model.contacts
          .map((c) => `<tr><th>${escapeHtml(c.label)}</th><td>${escapeHtml(c.value)}</td></tr>`)
          .join('')}</table>`
      : '';

  const assets =
    model.assets.length > 0
      ? `<ul>${model.assets
          .map((a) =>
            a.detail
              ? `<li>${escapeHtml(a.label)} <span class="mk-muted">(${escapeHtml(a.detail)})</span></li>`
              : `<li>${escapeHtml(a.label)}</li>`,
          )
          .join('')}</ul>`
      : '';

  return [
    '<!DOCTYPE html>',
    '<html lang="en">',
    '<head>',
    '<meta charset="utf-8"/>',
    '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
    `<title>${escapeHtml(model.artistName)} — Media Kit</title>`,
    '<style>',
    `:root{--brand:${brand};}`,
    'body{font-family:Arial,Helvetica,sans-serif;color:#1a1a22;margin:0;background:#f4f4f7;}',
    '.cover{background:var(--brand);color:#fff;padding:48px 40px;}',
    '.cover h1{margin:0;font-size:34px;}',
    '.cover .tagline{margin-top:8px;font-size:16px;opacity:.92;}',
    'main{max-width:820px;margin:0 auto;padding:32px 40px;}',
    'table{border-collapse:collapse;width:100%;margin:8px 0 24px;}',
    'th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #e2e2ea;font-size:14px;}',
    'th{width:160px;color:#55555f;font-weight:600;}',
    'h2{font-size:18px;margin:24px 0 8px;color:var(--brand);}',
    '.mk-section p{margin:4px 0;line-height:1.5;}',
    'ul{margin:6px 0;padding-left:20px;}',
    '.mk-links a{color:var(--brand);}',
    '.mk-muted{color:#88888f;}',
    'footer{max-width:820px;margin:0 auto;padding:16px 40px 48px;color:#88888f;font-size:12px;}',
    '</style>',
    '</head>',
    '<body>',
    `<header class="cover"><h1>${escapeHtml(model.artistName)}</h1>${
      model.tagline ? `<div class="tagline">${escapeHtml(model.tagline)}</div>` : ''
    }</header>`,
    '<main>',
    model.bio ? section('About', `<p>${escapeHtml(model.bio)}</p>`) : '',
    metaTable ? `<table>${metaTable}</table>` : '',
    section('Highlights', highlights),
    section('Links', links),
    section('Contact', contacts),
    section('Assets', assets),
    '</main>',
    `<footer>Generated at ${escapeHtml(model.generatedAt)} · content_renderer</footer>`,
    '</body>',
    '</html>',
  ].join('');
}
