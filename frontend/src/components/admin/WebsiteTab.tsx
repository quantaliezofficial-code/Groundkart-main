import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, ExternalLink, ImagePlus, Plus, RotateCcw, Trash2, Upload } from 'lucide-react';
import { siteApi, type SiteAsset } from '../../lib/api/site';
import {
  BUILT_IN_IMAGES,
  DEFAULT_HOMEPAGE,
  OCCASION_CATEGORIES,
  diffFromDefaults,
  mergeHomepage,
  type HomepageContent,
} from '../../lib/homepageContent';
import { compressImage } from '../../lib/imageCompress';
import { useAuth } from '../../lib/auth';
import { dateTime, errorText } from '../../lib/format';
import { Button, CopyButton, Field, Modal, Notice, Panel, Tabs, inputClass } from '../dashboard/kit';

/**
 * Super admin: everything visitors read on the homepage, the images it
 * uses, and the published versions. Regular admins can look but not change.
 *
 * Copy here is shown as plain text. Promises with numbers (hold time,
 * refund tiers, fees) are read from Rules and fees, never typed here.
 */

type View = 'homepage' | 'images' | 'history';

const SECTION_LABELS: { key: keyof HomepageContent['sections']; label: string }[] = [
  { key: 'occasions', label: 'Occasion photo cards' },
  { key: 'protections', label: 'What protects your booking' },
  { key: 'preview', label: 'How booking works (step-through)' },
  { key: 'reviews', label: 'Reviews from completed bookings' },
  { key: 'owners', label: 'List your venue' },
  { key: 'partners', label: 'Referral partners card' },
  { key: 'founder', label: 'Founder and team' },
  { key: 'faq', label: 'Questions people ask' },
  { key: 'closing', label: 'Closing call to action' },
];

function Text({
  label,
  value,
  onChange,
  max,
  multiline = false,
  disabled,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  max: number;
  multiline?: boolean;
  disabled?: boolean;
  hint?: string;
}) {
  const over = value.length > max;
  return (
    <Field label={label} hint={hint ?? `${value.length}/${max}`} error={over ? `At most ${max} characters` : null}>
      {multiline ? (
        <textarea className={`${inputClass} min-h-[84px]`} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input className={inputClass} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      )}
    </Field>
  );
}

/* ------------------------------------------------------------------ */
/* Image picker                                                        */
/* ------------------------------------------------------------------ */

function ImagePicker({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (url: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const assets = useQuery({ queryKey: ['site-assets'], queryFn: siteApi.assets, enabled: open });
  return (
    <div>
      <span className="mb-1 block text-sm font-medium text-ink">{label}</span>
      <div className="flex items-center gap-3">
        <img src={value} alt="" className="h-16 w-24 rounded-lg object-cover ring-1 ring-ink/10" />
        <Button disabled={disabled} onClick={() => setOpen(true)}>
          <ImagePlus size={15} aria-hidden="true" /> Change image
        </Button>
      </div>
      {open ? (
        <Modal title={`Choose: ${label}`} onClose={() => setOpen(false)} wide>
          <p className="mb-3 text-sm text-on-surface-variant">Upload new images in the Images tab. Built-in photos are always available.</p>
          <h3 className="mb-2 text-sm font-semibold text-ink">Your uploads</h3>
          {assets.isLoading ? <div className="h-24 rounded-xl shimmer" /> : null}
          {assets.data && assets.data.length === 0 ? <p className="mb-4 text-sm text-on-surface-variant">None yet.</p> : null}
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(assets.data ?? []).map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => {
                  onChange(a.url);
                  setOpen(false);
                }}
                className={`overflow-hidden rounded-xl text-left ring-2 cursor-pointer ${a.url === value ? 'ring-pitch' : 'ring-transparent hover:ring-ink/20'}`}
              >
                <img src={a.url} alt={a.alt_text} className="aspect-[4/3] w-full object-cover" />
                <span className="block truncate px-2 py-1 text-xs text-ink">{a.label}</span>
              </button>
            ))}
          </div>
          <h3 className="mb-2 text-sm font-semibold text-ink">Built-in photos</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {BUILT_IN_IMAGES.map((a) => (
              <button
                key={a.url}
                type="button"
                onClick={() => {
                  onChange(a.url);
                  setOpen(false);
                }}
                className={`overflow-hidden rounded-xl text-left ring-2 cursor-pointer ${a.url === value ? 'ring-pitch' : 'ring-transparent hover:ring-ink/20'}`}
              >
                <img src={a.url} alt="" className="aspect-[4/3] w-full object-cover" />
                <span className="block truncate px-2 py-1 text-xs text-ink">{a.label}</span>
              </button>
            ))}
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Homepage editor                                                     */
/* ------------------------------------------------------------------ */

function move<T>(list: T[], i: number, by: number): T[] {
  const j = i + by;
  if (j < 0 || j >= list.length) return list;
  const out = [...list];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

function HomepageEditor() {
  const qc = useQueryClient();
  const published = useQuery({ queryKey: ['admin-site-homepage'], queryFn: siteApi.adminHomepage });
  const [form, setForm] = useState<HomepageContent | null>(null);
  const [note, setNote] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);
  const canEdit = Boolean(published.data?.can_edit);
  const ro = !canEdit;

  useEffect(() => {
    if (published.data) setForm(mergeHomepage(published.data.data));
  }, [published.data]);

  const baseline = useMemo(() => (published.data ? JSON.stringify(mergeHomepage(published.data.data)) : ''), [published.data]);
  const dirty = form ? JSON.stringify(form) !== baseline : false;

  const onDone = () => {
    qc.invalidateQueries({ queryKey: ['admin-site-homepage'] });
    qc.invalidateQueries({ queryKey: ['site-homepage'] });
    qc.invalidateQueries({ queryKey: ['site-revisions'] });
    setNote('');
  };
  const publish = useMutation({
    mutationFn: () => siteApi.publishHomepage(diffFromDefaults(form!), published.data?.version ?? 0, note),
    onSuccess: onDone,
  });
  const reset = useMutation({
    mutationFn: () => siteApi.resetHomepage(published.data?.version ?? 0),
    onSuccess: () => {
      setConfirmReset(false);
      onDone();
    },
  });

  if (published.isError) return <Notice tone="error">{errorText(published.error)}</Notice>;
  if (!form) return <div className="h-64 rounded-2xl shimmer" />;

  const set = <K extends keyof HomepageContent>(key: K, value: HomepageContent[K]) => setForm({ ...form, [key]: value });
  const patch = <K extends keyof HomepageContent>(key: K, part: Partial<HomepageContent[K]>) =>
    setForm({ ...form, [key]: { ...(form[key] as object), ...part } as HomepageContent[K] });

  return (
    <div className="space-y-6" data-testid="homepage-editor">
      {ro ? <Notice>Only the super admin can change the website. You can see what is published.</Notice> : null}
      <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-surface-container bg-chalk/95 px-5 py-3 backdrop-blur">
        <p className="text-sm text-on-surface-variant">
          Published version {published.data?.version ?? 0}
          {published.data?.updated_at ? ` · ${dateTime(published.data.updated_at)}` : ' · built-in defaults'}
          {dirty ? <span className="ml-2 font-semibold text-clay">Unpublished changes</span> : null}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <a href="/" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-pitch underline-offset-4 hover:underline">
            View homepage <ExternalLink size={14} aria-hidden="true" />
          </a>
          {canEdit ? (
            <>
              <input
                className={`${inputClass} w-56`}
                placeholder="Note for this version (optional)"
                value={note}
                maxLength={300}
                onChange={(e) => setNote(e.target.value)}
              />
              <Button disabled={!dirty} onClick={() => published.data && setForm(mergeHomepage(published.data.data))}>
                Discard
              </Button>
              <Button variant="primary" loading={publish.isPending} disabled={!dirty} onClick={() => publish.mutate()}>
                Publish
              </Button>
            </>
          ) : null}
        </div>
      </div>
      {publish.isError ? <Notice tone="error">{errorText(publish.error)}</Notice> : null}
      {publish.isSuccess && !dirty ? <Notice tone="success">Published. Visitors see it within a minute.</Notice> : null}

      <Panel title="Sections" description="Turn a section off to hide it from the homepage. Nothing is deleted.">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {SECTION_LABELS.map(({ key, label }) => (
            <label key={key} className="flex cursor-pointer items-center gap-2.5 rounded-lg bg-surface-container-low px-3 py-2 text-sm text-ink">
              <input
                type="checkbox"
                disabled={ro}
                checked={form.sections[key]}
                onChange={(e) => patch('sections', { [key]: e.target.checked } as Partial<HomepageContent['sections']>)}
              />
              {label}
            </label>
          ))}
        </div>
      </Panel>

      <Panel title="Top of the page" description="Headline, subtitle and the background photo.">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Text label="Small line above the headline" value={form.hero.eyebrow} max={120} disabled={ro} onChange={(v) => patch('hero', { eyebrow: v })} />
          <Text label="Headline" value={form.hero.title} max={120} disabled={ro} onChange={(v) => patch('hero', { title: v })} />
          <Text label="Headline, gold part" value={form.hero.title_highlight} max={80} disabled={ro} onChange={(v) => patch('hero', { title_highlight: v })} />
          <Text label="Subtitle" value={form.hero.subtitle} max={400} multiline disabled={ro} onChange={(v) => patch('hero', { subtitle: v })} />
          <ImagePicker label="Background photo" value={form.hero.image_url} disabled={ro} onChange={(url) => patch('hero', { image_url: url })} />
          <div className="space-y-3">
            <Text label="Photo description (for screen readers; empty if decorative)" value={form.hero.image_alt} max={200} disabled={ro} onChange={(v) => patch('hero', { image_alt: v })} />
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" disabled={ro} checked={form.hero.show_occasion_chips} onChange={(e) => patch('hero', { show_occasion_chips: e.target.checked })} />
              Show the occasion shortcuts under the search bar
            </label>
          </div>
        </div>
      </Panel>

      <Panel
        title="Occasion cards"
        description="3 to 8 cards. Each opens search filtered to its category."
        actions={
          canEdit && form.occasions.length < 8 ? (
            <Button
              onClick={() =>
                set('occasions', [
                  ...form.occasions,
                  { key: `occasion-${form.occasions.length + 1}`, label: 'New occasion', category: 'sports', image_url: '/img/photos/placeholder-800.webp', alt: 'Venue photo' },
                ])
              }
            >
              <Plus size={15} aria-hidden="true" /> Add card
            </Button>
          ) : null
        }
      >
        <div className="space-y-4">
          {form.occasions.map((o, i) => {
            const update = (part: Partial<typeof o>) => set('occasions', form.occasions.map((x, j) => (j === i ? { ...x, ...part } : x)));
            return (
              <div key={i} className="grid grid-cols-1 gap-4 rounded-xl border border-surface-container p-4 md:grid-cols-[1fr_1fr_auto]">
                <div className="space-y-3">
                  <Text label="Label" value={o.label} max={40} disabled={ro} onChange={(v) => update({ label: v })} />
                  <Field label="Opens search for">
                    <select className={inputClass} disabled={ro} value={o.category} onChange={(e) => update({ category: e.target.value })}>
                      {OCCASION_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
                <div className="space-y-3">
                  <ImagePicker label="Photo" value={o.image_url} disabled={ro} onChange={(url) => update({ image_url: url })} />
                  <Text label="Photo description" value={o.alt} max={200} disabled={ro} onChange={(v) => update({ alt: v })} />
                </div>
                {canEdit ? (
                  <div className="flex items-start gap-1 md:flex-col">
                    <Button variant="ghost" aria-label="Move up" onClick={() => set('occasions', move(form.occasions, i, -1))}>
                      <ArrowUp size={15} aria-hidden="true" />
                    </Button>
                    <Button variant="ghost" aria-label="Move down" onClick={() => set('occasions', move(form.occasions, i, 1))}>
                      <ArrowDown size={15} aria-hidden="true" />
                    </Button>
                    <Button
                      variant="ghost"
                      aria-label="Remove card"
                      disabled={form.occasions.length <= 3}
                      onClick={() => set('occasions', form.occasions.filter((_, j) => j !== i))}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </Button>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        title="Section headings"
        description="The numbers inside 'What protects your booking' (hold time, refunds) always come from Rules and fees."
      >
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {(['protections', 'preview', 'reviews'] as const).map((k) => (
            <div key={k} className="space-y-3">
              <Text label={`${SECTION_LABELS.find((s) => s.key === k)?.label}: title`} value={form[k].title} max={120} disabled={ro} onChange={(v) => patch(k, { title: v })} />
              <Text label="Intro" value={form[k].intro} max={400} multiline disabled={ro} onChange={(v) => patch(k, { intro: v })} />
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="List your venue" description="The owners panel.">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <Text label="Title" value={form.owners.title} max={120} disabled={ro} onChange={(v) => patch('owners', { title: v })} />
            {form.owners.bullets.map((b, i) => (
              <Text
                key={i}
                label={`Point ${i + 1}`}
                value={b}
                max={200}
                disabled={ro}
                onChange={(v) => patch('owners', { bullets: form.owners.bullets.map((x, j) => (j === i ? v : x)) })}
              />
            ))}
            <Text label="Button" value={form.owners.cta_label} max={40} disabled={ro} onChange={(v) => patch('owners', { cta_label: v })} />
          </div>
          <div className="space-y-3">
            <ImagePicker label="Photo" value={form.owners.image_url} disabled={ro} onChange={(url) => patch('owners', { image_url: url })} />
            <Text label="Photo description" value={form.owners.image_alt} max={200} disabled={ro} onChange={(v) => patch('owners', { image_alt: v })} />
          </div>
        </div>
      </Panel>

      <Panel title="Founder and team" description="Only publish facts you can stand behind.">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Text label="Small line" value={form.founder.eyebrow} max={80} disabled={ro} onChange={(v) => patch('founder', { eyebrow: v })} />
          <Text label="Title" value={form.founder.title} max={120} disabled={ro} onChange={(v) => patch('founder', { title: v })} />
          <div className="md:col-span-2">
            <Text label="Story" value={form.founder.body} max={1200} multiline disabled={ro} onChange={(v) => patch('founder', { body: v })} />
          </div>
          <Text label="Name" value={form.founder.name} max={80} disabled={ro} onChange={(v) => patch('founder', { name: v })} />
          <Text label="Role" value={form.founder.role} max={120} disabled={ro} onChange={(v) => patch('founder', { role: v })} />
          <Text label="Link (https://… or /page)" value={form.founder.link_url} max={300} disabled={ro} onChange={(v) => patch('founder', { link_url: v })} />
          <Text label="Link text" value={form.founder.link_label} max={60} disabled={ro} onChange={(v) => patch('founder', { link_label: v })} />
        </div>
        <div className="mt-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink">Background (up to 6 lines)</h3>
            {canEdit && form.founder.timeline.length < 6 ? (
              <Button onClick={() => patch('founder', { timeline: [...form.founder.timeline, { years: '', org: '', role: '' }] })}>
                <Plus size={15} aria-hidden="true" /> Add line
              </Button>
            ) : null}
          </div>
          {form.founder.timeline.map((t, i) => {
            const upd = (part: Partial<typeof t>) => patch('founder', { timeline: form.founder.timeline.map((x, j) => (j === i ? { ...x, ...part } : x)) });
            return (
              <div key={i} className="grid grid-cols-1 gap-3 rounded-xl border border-surface-container p-3 md:grid-cols-[140px_180px_1fr_auto]">
                <Text label="Years" value={t.years} max={30} disabled={ro} onChange={(v) => upd({ years: v })} />
                <Text label="Organisation" value={t.org} max={80} disabled={ro} onChange={(v) => upd({ org: v })} />
                <Text label="What" value={t.role} max={300} disabled={ro} onChange={(v) => upd({ role: v })} />
                {canEdit ? (
                  <Button variant="ghost" aria-label="Remove line" className="self-end" onClick={() => patch('founder', { timeline: form.founder.timeline.filter((_, j) => j !== i) })}>
                    <Trash2 size={15} aria-hidden="true" />
                  </Button>
                ) : null}
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        title="Questions people ask"
        description="Also published to search engines as FAQ data. Answers must match how the product works."
        actions={
          canEdit && form.faq.length < 12 ? (
            <Button onClick={() => set('faq', [...form.faq, { q: '', a: '' }])}>
              <Plus size={15} aria-hidden="true" /> Add question
            </Button>
          ) : null
        }
      >
        <div className="space-y-4">
          {form.faq.map((f, i) => (
            <div key={i} className="grid grid-cols-1 gap-3 rounded-xl border border-surface-container p-4 md:grid-cols-[1fr_auto]">
              <div className="space-y-3">
                <Text label="Question" value={f.q} max={200} disabled={ro} onChange={(v) => set('faq', form.faq.map((x, j) => (j === i ? { ...x, q: v } : x)))} />
                <Text label="Answer" value={f.a} max={1200} multiline disabled={ro} onChange={(v) => set('faq', form.faq.map((x, j) => (j === i ? { ...x, a: v } : x)))} />
              </div>
              {canEdit ? (
                <div className="flex gap-1 md:flex-col">
                  <Button variant="ghost" aria-label="Move up" onClick={() => set('faq', move(form.faq, i, -1))}>
                    <ArrowUp size={15} aria-hidden="true" />
                  </Button>
                  <Button variant="ghost" aria-label="Move down" onClick={() => set('faq', move(form.faq, i, 1))}>
                    <ArrowDown size={15} aria-hidden="true" />
                  </Button>
                  <Button variant="ghost" aria-label="Remove question" onClick={() => set('faq', form.faq.filter((_, j) => j !== i))}>
                    <Trash2 size={15} aria-hidden="true" />
                  </Button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Closing call to action">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Text label="Text" value={form.closing.title} max={160} disabled={ro} onChange={(v) => patch('closing', { title: v })} />
          <Text label="Button" value={form.closing.cta_label} max={40} disabled={ro} onChange={(v) => patch('closing', { cta_label: v })} />
        </div>
      </Panel>

      {canEdit ? (
        <div className="flex justify-end">
          <Button variant="danger" onClick={() => setConfirmReset(true)}>
            <RotateCcw size={15} aria-hidden="true" /> Reset everything to built-in defaults
          </Button>
        </div>
      ) : null}
      {confirmReset ? (
        <Modal
          title="Reset the homepage?"
          onClose={() => setConfirmReset(false)}
          footer={
            <>
              <Button onClick={() => setConfirmReset(false)}>Cancel</Button>
              <Button variant="danger" loading={reset.isPending} onClick={() => reset.mutate()}>
                Reset and publish
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink">
            The homepage goes back to the built-in text and photos straight away. The current version stays in History, so you
            can restore it.
          </p>
          {reset.isError ? <div className="mt-3"><Notice tone="error">{errorText(reset.error)}</Notice></div> : null}
        </Modal>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Images                                                              */
/* ------------------------------------------------------------------ */

function Images({ canEdit }: { canEdit: boolean }) {
  const qc = useQueryClient();
  const assets = useQuery({ queryKey: ['site-assets'], queryFn: siteApi.assets });
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState('');
  const [alt, setAlt] = useState('');
  const [error, setError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: async () => siteApi.uploadAsset(await compressImage(file!, 2400), label.trim(), alt.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['site-assets'] });
      setFile(null);
      setLabel('');
      setAlt('');
      if (fileRef.current) fileRef.current.value = '';
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => siteApi.deleteAsset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['site-assets'] }),
    onError: (e) => setError(errorText(e)),
  });
  const rename = useMutation({
    mutationFn: ({ id, ...body }: { id: string; label?: string; alt_text?: string }) => siteApi.updateAsset(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['site-assets'] }),
  });

  return (
    <div className="space-y-6" data-testid="asset-library">
      {canEdit ? (
        <Panel title="Upload an image" description="JPG, PNG or WebP up to 10 MB. It is resized and saved as WebP, with location data removed. Use photos you own or are licensed to use (for example Unsplash).">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Field label="File">
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className={inputClass}
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null;
                  setFile(f);
                  if (f && !label) setLabel(f.name.replace(/\.[^.]+$/, '').slice(0, 80));
                }}
              />
            </Field>
            <Field label="Name (for you)">
              <input className={inputClass} value={label} maxLength={80} onChange={(e) => setLabel(e.target.value)} />
            </Field>
            <Field label="Description (for screen readers)">
              <input className={inputClass} value={alt} maxLength={200} onChange={(e) => setAlt(e.target.value)} />
            </Field>
          </div>
          {upload.isError ? <div className="mt-3"><Notice tone="error">{errorText(upload.error)}</Notice></div> : null}
          <Button className="mt-4" variant="primary" loading={upload.isPending} disabled={!file || !label.trim()} onClick={() => upload.mutate()}>
            <Upload size={15} aria-hidden="true" /> Upload
          </Button>
        </Panel>
      ) : (
        <Notice>Only the super admin can upload or remove website images.</Notice>
      )}

      {error ? <Notice tone="error">{error}</Notice> : null}
      <Panel title="Website images" description="Images in use on the homepage or a banner cannot be deleted until they are replaced there.">
        {assets.isLoading ? <div className="h-40 rounded-xl shimmer" /> : null}
        {assets.data && assets.data.length === 0 ? <p className="text-sm text-on-surface-variant">No uploads yet. The homepage uses the built-in photos.</p> : null}
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(assets.data ?? []).map((a: SiteAsset) => (
            <li key={a.id} className="overflow-hidden rounded-xl border border-surface-container">
              <img src={a.url} alt={a.alt_text} className="aspect-[16/10] w-full object-cover" />
              <div className="space-y-2 p-3 text-sm">
                {canEdit ? (
                  <>
                    <input className={inputClass} defaultValue={a.label} maxLength={80} onBlur={(e) => e.target.value !== a.label && rename.mutate({ id: a.id, label: e.target.value })} aria-label="Name" />
                    <input className={inputClass} defaultValue={a.alt_text} maxLength={200} placeholder="Description" onBlur={(e) => e.target.value !== a.alt_text && rename.mutate({ id: a.id, alt_text: e.target.value })} aria-label="Description" />
                  </>
                ) : (
                  <p className="font-semibold text-ink">{a.label}</p>
                )}
                <p className="text-xs text-on-surface-variant">
                  {a.width}×{a.height} · {Math.round(a.size_bytes / 1024)} KB · {dateTime(a.created_at)}
                </p>
                <div className="flex flex-wrap gap-2">
                  <CopyButton text={a.url} label="Copy link" />
                  {canEdit ? (
                    <Button variant="danger" loading={remove.isPending && remove.variables === a.id} onClick={() => { setError(null); remove.mutate(a.id); }}>
                      <Trash2 size={14} aria-hidden="true" /> Delete
                    </Button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* History                                                             */
/* ------------------------------------------------------------------ */

function History() {
  const qc = useQueryClient();
  const revs = useQuery({ queryKey: ['site-revisions'], queryFn: siteApi.revisions });
  const restore = useMutation({
    mutationFn: (id: string) => siteApi.restore(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['site-revisions'] });
      qc.invalidateQueries({ queryKey: ['admin-site-homepage'] });
      qc.invalidateQueries({ queryKey: ['site-homepage'] });
    },
  });
  if (revs.isError) return <Notice tone="error">{errorText(revs.error)}</Notice>;
  return (
    <Panel title="Published versions" description="The last 30. Restoring publishes that version again as a new version.">
      {restore.isError ? <Notice tone="error">{errorText(restore.error)}</Notice> : null}
      {revs.isLoading ? <div className="h-32 rounded-xl shimmer" /> : null}
      {revs.data && revs.data.length === 0 ? <p className="text-sm text-on-surface-variant">Nothing published yet: the homepage shows the built-in defaults.</p> : null}
      <ul className="divide-y divide-surface-container">
        {(revs.data ?? []).map((r, i) => (
          <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
            <div>
              <p className="font-semibold text-ink">
                Version {r.version} {i === 0 ? <span className="ml-1 rounded-full bg-pitch/10 px-2 py-0.5 text-xs text-pitch">live</span> : null}
              </p>
              <p className="text-on-surface-variant">
                {dateTime(r.created_at)} · {r.created_by ?? 'Unknown'} · {r.sections.length ? `changed: ${r.sections.join(', ')}` : 'built-in defaults'}
                {r.note ? ` · “${r.note}”` : ''}
              </p>
            </div>
            {i > 0 ? (
              <Button loading={restore.isPending && restore.variables === r.id} onClick={() => restore.mutate(r.id)}>
                <RotateCcw size={14} aria-hidden="true" /> Restore
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export default function WebsiteTab() {
  const { user } = useAuth();
  const isSuper = Boolean(user?.is_super_admin);
  const [view, setView] = useState<View>('homepage');
  return (
    <div className="space-y-6" data-testid="website-tab">
      <Tabs<View>
        value={view}
        onChange={setView}
        items={[
          { id: 'homepage', label: 'Homepage' },
          { id: 'images', label: 'Images' },
          ...(isSuper ? [{ id: 'history' as View, label: 'History' }] : []),
        ]}
      />
      {view === 'homepage' ? <HomepageEditor /> : null}
      {view === 'images' ? <Images canEdit={isSuper} /> : null}
      {view === 'history' && isSuper ? <History /> : null}
      <p className="text-xs text-on-surface-variant">
        Defaults: {DEFAULT_HOMEPAGE.occasions.length} occasion cards, {DEFAULT_HOMEPAGE.faq.length} questions. Every publish, restore, upload and
        deletion is written to the audit log.
      </p>
    </div>
  );
}
