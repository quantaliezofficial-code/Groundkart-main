/**
 * A link path that stays on this site. Rejects protocol-relative ("//x"),
 * backslash tricks ("/\evil.example", which browsers read as "//evil.example";
 * the pattern behind the React Router open-redirect advisory), control
 * characters and anything with a scheme.
 */
export function isSafeInternalPath(url: string | null | undefined): url is string {
  if (!url) return false;
  if (!url.startsWith('/')) return false;
  if (url.startsWith('//')) return false;
  if (/[\\\u0000-\u001f\u007f]/.test(url)) return false;
  return true;
}
