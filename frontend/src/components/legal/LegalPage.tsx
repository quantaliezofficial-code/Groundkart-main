import React, { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import SEOHead from '../SEOHead';
import { generateBreadcrumbSchema } from '../../lib/schema';
import { SITE_NAME, absUrl } from '../../lib/site';
import { LEGAL_DOCS, type LegalDocKey, type LegalLang, fillLegalText, useLegalProfile } from '../../lib/legal';
import { MarkdownDoc, docTitle, draftNotice, sectionHeadings, slugify } from './Markdown';

const DESCRIPTIONS: Record<LegalDocKey, string> = {
  privacy: `What personal data ${SITE_NAME} collects, why, how long it is kept, who receives it, and how to use your rights.`,
  terms: `The rules for booking and listing venues on ${SITE_NAME}: payments, cancellations, reviews, disputes and governing law.`,
  refunds: `${SITE_NAME} cancellation windows and how refunds are paid.`,
  cookies: `The one cookie ${SITE_NAME} sets, what stays in your browser, and the external services that load only when you click.`,
  grievance: `How to complain to ${SITE_NAME}, who handles it, and how fast you get an answer.`,
  'data-rights': `How to get a copy of your data, correct it, delete it, withdraw consent or name a nominee.`,
};

const OTHER_DOCS: LegalDocKey[] = ['privacy', 'terms', 'refunds', 'cookies', 'grievance', 'data-rights'];

export default function LegalPage({ doc }: { doc: LegalDocKey }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: profile } = useLegalProfile();
  const meta = LEGAL_DOCS[doc];
  const params = new URLSearchParams(location.search);
  const requested = (params.get('lang') as LegalLang) || 'en';
  const lang: LegalLang = meta.sources[requested] ? requested : 'en';
  const raw = meta.sources[lang] || meta.sources.en || '';
  const source = useMemo(() => fillLegalText(raw, profile), [raw, profile]);
  const title = docTitle(source) || meta.title;
  const draft = draftNotice(source);
  const toc = sectionHeadings(source);
  const versionLine = /^(Version .+|संस्करण .+)$/m.exec(source)?.[1];
  const body = source.replace(/^> .*(\n> .*)*\n?/m, '').replace(/^(Version .+|संस्करण .+)\n/m, '');

  const setLang = (next: LegalLang) => {
    const p = new URLSearchParams(location.search);
    if (next === 'en') p.delete('lang');
    else p.set('lang', next);
    navigate({ pathname: location.pathname, search: p.toString() ? `?${p}` : '' }, { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] pb-16 pt-10 sm:pt-14" lang={lang === 'hi' ? 'hi' : 'en'}>
      <SEOHead
        title={`${meta.title} | ${SITE_NAME}`}
        description={DESCRIPTIONS[doc]}
        canonicalUrl={absUrl(meta.path)}
        jsonLd={generateBreadcrumbSchema([
          { name: 'Home', path: '/' },
          { name: meta.title, path: meta.path },
        ])}
      />
      <div className="mx-auto max-w-6xl px-5 sm:px-6">
        <nav aria-label="Breadcrumb" className="mb-6">
          <ol className="flex items-center gap-2 text-xs text-on-surface-variant">
            <li>
              <a href="/" onClick={(e) => { e.preventDefault(); navigate('/'); }} className="hover:text-pitch">Home</a>
            </li>
            <li aria-hidden>/</li>
            <li className="font-semibold text-pitch" aria-current="page">{meta.title}</li>
          </ol>
        </nav>

        <div className="grid gap-10 lg:grid-cols-[1fr_15rem]">
          <article className="min-w-0 rounded-2xl bg-chalk p-6 ring-1 ring-ink/5 sm:p-10">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="font-display text-3xl font-bold leading-tight text-pitch sm:text-4xl">{title}</h1>
                {versionLine && <p className="mt-2 text-xs text-on-surface-variant">{versionLine}</p>}
              </div>
              {Object.keys(meta.sources).length > 1 && (
                <div role="group" aria-label="Language" className="inline-flex rounded-full bg-mist p-1 text-xs font-semibold">
                  {(['en', 'hi'] as LegalLang[]).filter((l) => meta.sources[l]).map((l) => (
                    <button
                      key={l}
                      type="button"
                      data-testid={`lang-${l}`}
                      aria-pressed={lang === l}
                      onClick={() => setLang(l)}
                      className={`rounded-full px-3 py-1.5 transition-colors ${lang === l ? 'bg-pitch text-chalk' : 'text-ink/70 hover:text-ink'}`}
                    >
                      {l === 'en' ? 'English' : 'हिन्दी'}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {draft && (
              <p data-testid="draft-banner" className="mt-6 rounded-xl border border-marigold/40 bg-marigold/10 px-4 py-3 text-sm leading-6 text-ink">
                {draft}
              </p>
            )}

            <div className="mt-8">
              <MarkdownDoc source={body} onNavigate={(p) => navigate(p)} skipTitle />
            </div>
          </article>

          <aside className="hidden lg:block">
            <div className="sticky top-28 space-y-6">
              {toc.length > 2 && (
                <nav aria-label="On this page">
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">On this page</p>
                  <ul className="mt-3 space-y-2 border-l border-ink/10 text-sm">
                    {toc.map((h) => (
                      <li key={h}>
                        <a href={`#${slugify(h)}`} className="-ml-px block border-l border-transparent pl-3 text-on-surface-variant hover:border-pitch hover:text-pitch">
                          {h.replace(/^\d+\.\s*/, '')}
                        </a>
                      </li>
                    ))}
                  </ul>
                </nav>
              )}
              <nav aria-label="Other policies">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">Policies</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {OTHER_DOCS.filter((d) => d !== doc).map((d) => (
                    <li key={d}>
                      <a
                        href={LEGAL_DOCS[d].path}
                        onClick={(e) => { e.preventDefault(); navigate(LEGAL_DOCS[d].path); }}
                        className="inline-flex items-center gap-2 text-on-surface-variant hover:text-pitch"
                      >
                        <FileText size={14} aria-hidden /> {LEGAL_DOCS[d].title}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
