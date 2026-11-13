import { api } from './client';
import type { HomepageOverrides, PublishedContent } from '../homepageContent';

/** Super admin website control (backend/app/routers/site.py). */

export interface SiteAsset {
  id: string;
  url: string;
  label: string;
  alt_text: string;
  width: number | null;
  height: number | null;
  size_bytes: number;
  created_at: string | null;
}

export interface ContentRevision {
  id: string;
  version: number;
  note: string | null;
  created_at: string | null;
  created_by: string | null;
  sections: string[];
}

export interface ReviewModeration {
  id: string;
  hidden_at: string | null;
  hidden_reason: string | null;
  featured: boolean;
}

export const siteApi = {
  adminHomepage: () => api.get<PublishedContent>('/api/v1/admin/site/homepage'),
  publishHomepage: (data: HomepageOverrides, baseVersion: number, note?: string) =>
    api.put<PublishedContent>('/api/v1/admin/site/homepage', { data, base_version: baseVersion, note: note || undefined }),
  resetHomepage: (baseVersion: number) =>
    api.delete<PublishedContent>('/api/v1/admin/site/homepage', { query: { base_version: baseVersion } }),
  revisions: () => api.get<ContentRevision[]>('/api/v1/admin/site/homepage/revisions'),
  restore: (revisionId: string) => api.post<PublishedContent>(`/api/v1/admin/site/homepage/revisions/${revisionId}/restore`, {}),

  assets: () => api.get<SiteAsset[]>('/api/v1/admin/site/assets'),
  uploadAsset: (file: File, label: string, altText: string) => {
    const form = new FormData();
    form.append('image', file);
    form.append('label', label);
    form.append('alt_text', altText);
    return api.postForm<SiteAsset>('/api/v1/admin/site/assets', form);
  },
  updateAsset: (id: string, body: { label?: string; alt_text?: string }) => api.patch<SiteAsset>(`/api/v1/admin/site/assets/${id}`, body),
  deleteAsset: (id: string) => api.delete<void>(`/api/v1/admin/site/assets/${id}`),

  moderateReview: (id: string, body: { hidden?: boolean; reason?: string; featured?: boolean }) =>
    api.patch<ReviewModeration>(`/api/v1/admin/reviews/${id}/moderation`, body),
};
