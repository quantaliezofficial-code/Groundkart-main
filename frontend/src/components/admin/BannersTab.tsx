import React, { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ImagePlus, Plus } from 'lucide-react';
import { platformApi, type Banner, type BannerBody, type BannerPlacement } from '../../lib/api/platform';
import { compressImage } from '../../lib/imageCompress';
import { dateTime, errorText } from '../../lib/format';
import { StatusBadge } from '../dashboard';
import { Button, Field, Modal, Notice, Panel, inputClass } from '../dashboard/kit';

/**
 * Banners an admin controls without a deploy. Several can be live per
 * placement; each can be scheduled to start and stop on its own.
 */

const PLACEMENTS: { id: BannerPlacement; label: string; help: string }[] = [
  { id: 'home_hero', label: 'Homepage feature', help: 'A large card under the homepage search. Visitors can step through several.' },
  { id: 'home_strip', label: 'Homepage announcement', help: 'A slim line above the homepage. The first live one is shown; visitors can dismiss it.' },
  { id: 'search_top', label: 'Search results', help: 'A slim line above search results.' },
];

function liveState(b: Banner): 'active' | 'scheduled' | 'expired' | 'paused' {
  if (!b.enabled) return 'paused';
  const now = Date.now();
  if (b.start_at && new Date(b.start_at).getTime() > now) return 'scheduled';
  if (b.end_at && new Date(b.end_at).getTime() <= now) return 'expired';
  return 'active';
}

/** datetime-local value <-> ISO, in the admin's own time zone. */
function toLocalInput(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function fromLocalInput(v: string): string | null {
  return v ? new Date(v).toISOString() : null;
}

export default function BannersTab() {
  const qc = useQueryClient();
  const banners = useQuery({ queryKey: ['admin-banners'], queryFn: platformApi.listBanners });
  const [editing, setEditing] = useState<Banner | 'new' | null>(null);
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['admin-banners'] });
    qc.invalidateQueries({ queryKey: ['public-banners'] });
  };
  const toggle = useMutation({
    mutationFn: (b: Banner) => platformApi.updateBanner(b.id, { enabled: !b.enabled }),
    onSuccess: refresh,
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="primary" onClick={() => setEditing('new')}>
          <Plus size={15} aria-hidden="true" /> New banner
        </Button>
      </div>
      {banners.isError ? <Notice tone="error">{errorText(banners.error)}</Notice> : null}
      {PLACEMENTS.map((p) => {
        const rows = (banners.data ?? []).filter((b) => b.placement === p.id);
        return (
          <Panel key={p.id} title={p.label} description={p.help} padded={false}>
            {banners.isLoading ? (
              <div className="m-5 h-20 rounded shimmer" />
            ) : rows.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-on-surface-variant">No banners here.</p>
            ) : (
              <ul className="divide-y divide-surface-container">
                {rows.map((b) => (
                  <li key={b.id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                    <div className="h-16 w-28 shrink-0 overflow-hidden rounded-lg bg-surface-container">
                      {b.image_url ? <img src={b.image_url} alt="" className="h-full w-full object-cover" loading="lazy" /> : null}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink">{b.title}</p>
                      <p className="truncate text-sm text-on-surface-variant">{b.subtitle || 'No subtitle'}</p>
                      <p className="mt-1 text-xs text-on-surface-variant">
                        Order {b.priority}
                        {b.start_at ? ` · from ${dateTime(b.start_at)}` : ''}
                        {b.end_at ? ` · until ${dateTime(b.end_at)}` : ''}
                        {b.cta_url ? ` · links to ${b.cta_url}` : ''}
                      </p>
                    </div>
                    <StatusBadge status={liveState(b) === 'scheduled' ? 'pending' : liveState(b)} />
                    <div className="flex gap-2">
                      <Button onClick={() => toggle.mutate(b)} loading={toggle.isPending && toggle.variables?.id === b.id}>
                        {b.enabled ? 'Turn off' : 'Turn on'}
                      </Button>
                      <Button onClick={() => setEditing(b)}>Edit</Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        );
      })}
      {editing && (
        <BannerEditor
          banner={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function BannerEditor({ banner, onClose, onSaved }: { banner: Banner | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    placement: (banner?.placement ?? 'home_hero') as BannerPlacement,
    title: banner?.title ?? '',
    subtitle: banner?.subtitle ?? '',
    cta_label: banner?.cta_label ?? '',
    cta_url: banner?.cta_url ?? '',
    priority: String(banner?.priority ?? 0),
    enabled: banner?.enabled ?? true,
    start_at: toLocalInput(banner?.start_at ?? null),
    end_at: toLocalInput(banner?.end_at ?? null),
  });
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(banner?.image_url ?? null);
  const fileRef = useRef<HTMLInputElement>(null);

  const save = useMutation({
    mutationFn: async () => {
      const body: BannerBody & { title: string } = {
        placement: form.placement,
        title: form.title.trim(),
        subtitle: form.subtitle.trim() || null,
        cta_label: form.cta_label.trim() || null,
        cta_url: form.cta_url.trim() || null,
        priority: Number(form.priority) || 0,
        enabled: form.enabled,
        start_at: fromLocalInput(form.start_at),
        end_at: fromLocalInput(form.end_at),
      };
      const saved = banner ? await platformApi.updateBanner(banner.id, body) : await platformApi.createBanner(body);
      if (file) {
        const small = await compressImage(file, 2400);
        await platformApi.uploadBannerImage(saved.id, small, small.name);
      }
      return saved;
    },
    onSuccess: onSaved,
  });
  const remove = useMutation({ mutationFn: () => platformApi.deleteBanner(banner!.id), onSuccess: onSaved });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value } as typeof form);

  return (
    <Modal
      title={banner ? 'Edit banner' : 'New banner'}
      onClose={onClose}
      wide
      footer={
        <>
          {banner ? (
            <Button
              variant="danger"
              className="mr-auto"
              loading={remove.isPending}
              onClick={() => {
                if (window.confirm('Delete this banner? This cannot be undone.')) remove.mutate();
              }}
            >
              Delete
            </Button>
          ) : null}
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={save.isPending} disabled={form.title.trim().length < 2} onClick={() => save.mutate()}>
            Save banner
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Where it appears">
          <select className={inputClass} value={form.placement} onChange={set('placement')}>
            {PLACEMENTS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Order" hint="Lower numbers show first">
          <input className={inputClass} type="number" min={0} max={999} value={form.priority} onChange={set('priority')} />
        </Field>
        <Field label="Headline" className="sm:col-span-2" hint={`${form.title.length}/90`}>
          <input className={inputClass} value={form.title} onChange={set('title')} maxLength={90} />
        </Field>
        <Field label="Supporting line (optional)" className="sm:col-span-2" hint={`${form.subtitle.length}/180`}>
          <input className={inputClass} value={form.subtitle} onChange={set('subtitle')} maxLength={180} />
        </Field>
        <Field label="Button text (optional)">
          <input className={inputClass} value={form.cta_label} onChange={set('cta_label')} maxLength={32} placeholder="See venues" />
        </Field>
        <Field label="Button link (optional)" hint="A page here, like /search?category=banquet, or a full https:// address">
          <input className={inputClass} value={form.cta_url} onChange={set('cta_url')} maxLength={300} />
        </Field>
        <Field label="Show from (optional)">
          <input className={inputClass} type="datetime-local" value={form.start_at} onChange={set('start_at')} />
        </Field>
        <Field label="Show until (optional)">
          <input className={inputClass} type="datetime-local" value={form.end_at} onChange={set('end_at')} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-ink sm:col-span-2">
          <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
          Turned on
        </label>
        {form.placement === 'home_hero' ? (
          <div className="sm:col-span-2">
            <span className="mb-1 block text-sm font-medium text-ink">Image</span>
            <div className="flex flex-wrap items-center gap-4">
              <div className="h-24 w-44 overflow-hidden rounded-lg bg-surface-container">
                {preview ? <img src={preview} alt="" className="h-full w-full object-cover" /> : null}
              </div>
              <div>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setFile(f);
                      setPreview(URL.createObjectURL(f));
                    }
                  }}
                />
                <Button onClick={() => fileRef.current?.click()}>
                  <ImagePlus size={15} aria-hidden="true" /> {preview ? 'Replace image' : 'Choose image'}
                </Button>
                <p className="mt-1 text-xs text-on-surface-variant">Landscape, at least 1200 px wide. It is resized and compressed for you.</p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
      {save.isError || remove.isError ? (
        <div className="mt-4">
          <Notice tone="error">{errorText(save.error || remove.error)}</Notice>
        </div>
      ) : null}
    </Modal>
  );
}
