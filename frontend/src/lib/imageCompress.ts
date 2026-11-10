/**
 * Shrinks a photo in the browser before it is uploaded.
 *
 * Phone photos are often 4–12 MB. Resizing to the largest size the site
 * ever shows and re-encoding as WebP typically cuts that to a few hundred
 * KB, so uploads finish quickly on mobile data and never hit the 10 MB
 * limit. The server re-encodes everything again regardless (and strips
 * location metadata), so this step is about speed, not trust.
 *
 * Anything that isn't a still image, or that the browser can't decode, is
 * returned unchanged and left for the server to accept or refuse.
 */
const MAX_EDGE = 2000;
const QUALITY = 0.82;
const SKIP_BELOW_BYTES = 350 * 1024;

export async function compressImage(file: File, maxEdge = MAX_EDGE): Promise<File> {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return file;
  if (typeof document === 'undefined' || typeof createImageBitmap !== 'function') return file;

  let bitmap: ImageBitmap;
  try {
    // 'from-image' applies the camera's EXIF rotation, so portrait photos stay upright.
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' } as ImageBitmapOptions);
  } catch {
    return file;
  }

  const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
  if (scale === 1 && file.size <= SKIP_BELOW_BYTES) {
    bitmap.close?.();
    return file;
  }
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    bitmap.close?.();
    return file;
  }
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close?.();

  const blob: Blob | null = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', QUALITY));
  // Some browsers (older Safari) silently fall back to PNG for WebP; keep
  // whichever result is actually smaller.
  if (!blob || blob.size >= file.size) return file;
  const type = blob.type || 'image/webp';
  const ext = type === 'image/webp' ? 'webp' : type === 'image/png' ? 'png' : 'jpg';
  const base = file.name.replace(/\.[^.]+$/, '') || 'photo';
  return new File([blob], `${base}.${ext}`, { type, lastModified: Date.now() });
}
