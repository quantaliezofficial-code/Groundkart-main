import { describe, expect, it } from 'vitest';
import { isSafeInternalPath } from './safeUrl';

describe('isSafeInternalPath', () => {
  it('accepts paths on this site', () => {
    for (const p of ['/', '/search?category=sports', '/venues/abc#photos']) expect(isSafeInternalPath(p)).toBe(true);
  });
  it('rejects anything that can leave the site', () => {
    for (const p of ['//evil.example', '/\\evil.example', '/\\/evil.example', 'https://evil.example', 'javascript:alert(1)', '/a\nb', '', null, undefined]) {
      expect(isSafeInternalPath(p as string)).toBe(false);
    }
  });
});
