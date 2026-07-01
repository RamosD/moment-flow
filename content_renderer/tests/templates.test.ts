import { describe, expect, it } from 'vitest';
import sharp from 'sharp';

import {
  FORMAT_DIMENSIONS,
  OUTPUT_FORMATS,
  resolveOutputDimensions,
} from '../src/templates/dimensions';
import {
  buildSvg,
  renderSvgToPng,
  sanitizeColor,
  sanitizeTextForSvg,
  type SvgSpec,
} from '../src/templates/svg';
import { renderTemplate, resolveTemplate, TEMPLATE_KEYS } from '../src/templates/registry';

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function baseSpec(overrides: Partial<SvgSpec> = {}): SvgSpec {
  return {
    width: 1080,
    height: 1080,
    backgroundColor: '#0B0B0F',
    brandColor: '#6C5CE7',
    title: 'Default Title',
    ...overrides,
  };
}

describe('template registry', () => {
  it('resolves a known template_key without fallback', () => {
    const resolved = resolveTemplate('milestone_card');
    expect(resolved.usedFallback).toBe(false);
    expect(resolved.key).toBe('milestone_card');
    expect(resolved.definition.defaultFormat).toBe('post_1_1');
  });

  it('every catalogued key resolves to itself', () => {
    for (const key of TEMPLATE_KEYS) {
      const resolved = resolveTemplate(key);
      expect(resolved.key).toBe(key);
      expect(resolved.usedFallback).toBe(false);
    }
  });

  it('falls back to generic_post for an unknown or missing key', () => {
    expect(resolveTemplate('does_not_exist')).toMatchObject({
      key: 'generic_post',
      usedFallback: true,
    });
    expect(resolveTemplate(undefined)).toMatchObject({
      key: 'generic_post',
      usedFallback: true,
    });
  });
});

describe('sanitizeTextForSvg', () => {
  it('escapes XML-sensitive characters', () => {
    const out = sanitizeTextForSvg('<b> & "x" \'y\'');
    expect(out).not.toContain('<');
    expect(out).not.toContain('>');
    expect(out).toContain('&lt;');
    expect(out).toContain('&amp;');
    expect(out).toContain('&quot;');
    expect(out).toContain('&#39;');
  });

  it('strips control characters', () => {
    const input = `a${String.fromCharCode(7)}b${String.fromCharCode(0)}c`;
    expect(sanitizeTextForSvg(input)).toBe('abc');
  });

  it('clamps text length', () => {
    expect(sanitizeTextForSvg('x'.repeat(500), 50).length).toBeLessThanOrEqual(50);
  });
});

describe('sanitizeColor', () => {
  it('accepts hex and simple named colours', () => {
    expect(sanitizeColor('#00ff88', '#000000')).toBe('#00ff88');
    expect(sanitizeColor('#fff', '#000000')).toBe('#fff');
    expect(sanitizeColor('red', '#000000')).toBe('red');
  });

  it('rejects injection attempts and returns the fallback', () => {
    expect(sanitizeColor('red" onload="x', '#6C5CE7')).toBe('#6C5CE7');
    expect(sanitizeColor('url(http://evil)', '#000000')).toBe('#000000');
    expect(sanitizeColor(42, '#000000')).toBe('#000000');
  });
});

describe('buildSvg', () => {
  it('includes the title and is well-formed SVG of the right size', () => {
    const svg = buildSvg(baseSpec({ title: 'Summer Release' }));
    expect(svg).toContain('<svg');
    expect(svg).toContain('width="1080"');
    expect(svg).toContain('viewBox="0 0 1080 1080"');
    expect(svg).toContain('Summer Release');
  });

  it('escapes a malicious title so no raw markup is injected', () => {
    const svg = buildSvg(baseSpec({ title: '<script>alert(1)</script>' }));
    expect(svg).not.toContain('<script>');
    expect(svg).toContain('&lt;script&gt;');
  });

  it('renders the optional content fields', () => {
    const svg = buildSvg(
      baseSpec({
        title: 'Card Title',
        subtitle: 'A subtitle',
        artistName: 'The Artist',
        trackTitle: 'The Track',
        campaignName: 'Spring Campaign',
        metric: '1,000,000 streams',
        badge: 'MILESTONE',
      }),
    );
    for (const text of [
      'Card Title',
      'A subtitle',
      'The Artist',
      'The Track',
      'Spring Campaign',
      '1,000,000 streams',
      'MILESTONE',
    ]) {
      expect(svg).toContain(text);
    }
  });
});

describe('dimensions', () => {
  it('returns the correct dimensions for each supported format', () => {
    expect(resolveOutputDimensions('post_1_1')).toMatchObject({ width: 1080, height: 1080, usedFallback: false });
    expect(resolveOutputDimensions('post_4_5')).toMatchObject({ width: 1080, height: 1350, usedFallback: false });
    expect(resolveOutputDimensions('story_9_16')).toMatchObject({ width: 1080, height: 1920, usedFallback: false });
    expect(resolveOutputDimensions('thumbnail_16_9')).toMatchObject({ width: 1280, height: 720, usedFallback: false });
  });

  it('falls back to post_1_1 for an unknown format', () => {
    expect(resolveOutputDimensions('banner_3_1')).toMatchObject({
      format: 'post_1_1',
      width: 1080,
      height: 1080,
      usedFallback: true,
    });
  });
});

describe('renderSvgToPng', () => {
  it('produces a real PNG buffer', async () => {
    const png = await renderSvgToPng(buildSvg(baseSpec()), { width: 1080, height: 1080 });
    expect(png.length).toBeGreaterThan(0);
    expect(png.subarray(0, 8).equals(PNG_SIGNATURE)).toBe(true);

    const meta = await sharp(png).metadata();
    expect(meta.format).toBe('png');
    expect(meta.width).toBe(1080);
    expect(meta.height).toBe(1080);
  });
});

describe('renderTemplate (end to end)', () => {
  it('renders a PNG at the exact dimensions for every format', async () => {
    for (const format of OUTPUT_FORMATS) {
      const result = await renderTemplate({
        templateKey: 'generic_post',
        format,
        content: { title: 'Hi' },
      });
      expect(result.format).toBe(format);
      const meta = await sharp(result.png).metadata();
      expect(meta.format).toBe('png');
      expect(meta.width).toBe(FORMAT_DIMENSIONS[format].width);
      expect(meta.height).toBe(FORMAT_DIMENSIONS[format].height);
    }
  });

  it('uses the template fallback for an unknown key and still renders', async () => {
    const result = await renderTemplate({ templateKey: 'nope', content: { title: 'X' } });
    expect(result.usedFallbackTemplate).toBe(true);
    expect(result.templateKey).toBe('generic_post');
    expect(result.png.subarray(0, 8).equals(PNG_SIGNATURE)).toBe(true);
  });

  it('uses the format fallback for an unknown format', async () => {
    const result = await renderTemplate({
      templateKey: 'generic_post',
      format: 'weird_format',
      content: { title: 'X' },
    });
    expect(result.usedFallbackFormat).toBe(true);
    expect(result.format).toBe('post_1_1');
    expect(result.width).toBe(1080);

    const meta = await sharp(result.png).metadata();
    expect(meta.width).toBe(1080);
    expect(meta.height).toBe(1080);
  });

  it('embeds the title and template badge in the SVG', async () => {
    const result = await renderTemplate({
      templateKey: 'release_card',
      content: { title: 'My Track', artistName: 'The Artist' },
    });
    expect(result.svg).toContain('My Track');
    expect(result.svg).toContain('NEW RELEASE');
  });
});
