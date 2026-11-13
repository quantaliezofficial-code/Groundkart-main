import React from 'react';

/**
 * A deliberately small Markdown renderer for the legal pages: headings,
 * paragraphs, line breaks, bullet and numbered lists, tables, blockquotes,
 * **bold**, `code` and [links](/path). Content is our own (src/content/legal),
 * rendered as React elements, never as HTML, so nothing can be injected.
 * Each "## " heading opens a <section>, so tests and screen readers can scope
 * to one part of a policy.
 */

type Block =
  | { kind: 'h'; level: number; text: string }
  | { kind: 'p'; lines: string[] }
  | { kind: 'ul' | 'ol'; items: string[] }
  | { kind: 'table'; head: string[]; rows: string[][] }
  | { kind: 'quote'; text: string };

function parse(md: string): Block[] {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    const h = /^(#{1,4}) (.+)$/.exec(line);
    if (h) {
      blocks.push({ kind: 'h', level: h[1].length, text: h[2].trim() });
      i++;
      continue;
    }
    if (line.startsWith('> ')) {
      const parts: string[] = [];
      while (i < lines.length && lines[i].startsWith('> ')) parts.push(lines[i++].slice(2));
      blocks.push({ kind: 'quote', text: parts.join(' ') });
      continue;
    }
    if (line.startsWith('| ')) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        const cells = lines[i].trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
        if (!cells.every((c) => /^-+$/.test(c))) rows.push(cells);
        i++;
      }
      blocks.push({ kind: 'table', head: rows[0] || [], rows: rows.slice(1) });
      continue;
    }
    if (/^[-*] /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*] /.test(lines[i])) items.push(lines[i++].slice(2));
      blocks.push({ kind: 'ul', items });
      continue;
    }
    if (/^\d+\. /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\. /.test(lines[i])) items.push(lines[i++].replace(/^\d+\. /, ''));
      blocks.push({ kind: 'ol', items });
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4} |> |\| |[-*] |\d+\. )/.test(lines[i])) para.push(lines[i++]);
    blocks.push({ kind: 'p', lines: para });
  }
  return blocks;
}

const PLACEHOLDER = /(\[\[OWNER TO FILL: [^\]]+\]\])/;

function inline(text: string, onNavigate?: (path: string) => void, keyBase = ''): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\[\[OWNER TO FILL: [^\]]+\]\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let n = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyBase}-${n++}`;
    if (tok.startsWith('**')) out.push(<strong key={key} className="font-semibold text-ink">{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith('`')) out.push(<code key={key} className="rounded bg-ink/5 px-1 py-0.5 font-mono text-[0.85em]">{tok.slice(1, -1)}</code>);
    else if (PLACEHOLDER.test(tok)) out.push(<mark key={key} className="rounded bg-marigold/25 px-1 text-ink">{tok}</mark>);
    else {
      const lm = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(tok)!;
      const href = lm[2];
      const internal = href.startsWith('/');
      out.push(
        <a
          key={key}
          href={href}
          className="font-medium text-pitch underline underline-offset-2 hover:text-pitch/80"
          {...(internal
            ? {
                onClick: (e: React.MouseEvent) => {
                  if (onNavigate) {
                    e.preventDefault();
                    onNavigate(href);
                  }
                },
              }
            : { target: '_blank', rel: 'noopener noreferrer' })}
        >
          {lm[1]}
        </a>,
      );
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function slugify(text: string) {
  return text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/(^-|-$)/g, '');
}

export function MarkdownDoc({ source, onNavigate, skipTitle = false }: { source: string; onNavigate?: (path: string) => void; skipTitle?: boolean }) {
  const blocks = parse(source);
  const sections: { heading?: Block & { kind: 'h' }; body: Block[] }[] = [{ body: [] }];
  for (const b of blocks) {
    if (b.kind === 'h' && b.level === 1 && skipTitle) continue;
    if (b.kind === 'h' && b.level === 2) sections.push({ heading: b, body: [] });
    else sections[sections.length - 1].body.push(b);
  }

  const renderBlock = (b: Block, idx: number) => {
    const k = `b${idx}`;
    switch (b.kind) {
      case 'h': {
        const Tag = (`h${Math.min(b.level + 0, 4)}` as unknown) as keyof React.JSX.IntrinsicElements;
        const cls = b.level === 1 ? 'font-display text-3xl font-bold text-pitch sm:text-4xl' : 'mt-6 text-base font-bold text-ink';
        return <Tag key={k} id={slugify(b.text)} className={cls}>{inline(b.text, onNavigate, k)}</Tag>;
      }
      case 'p':
        return (
          <p key={k} className="mt-3 text-[15px] leading-7 text-on-surface-variant">
            {b.lines.map((l, j) => (
              <React.Fragment key={j}>
                {j > 0 && <br />}
                {inline(l, onNavigate, `${k}-${j}`)}
              </React.Fragment>
            ))}
          </p>
        );
      case 'ul':
        return (
          <ul key={k} className="mt-3 list-disc space-y-2 pl-5 text-[15px] leading-7 text-on-surface-variant marker:text-pitch/60">
            {b.items.map((it, j) => <li key={j}>{inline(it, onNavigate, `${k}-${j}`)}</li>)}
          </ul>
        );
      case 'ol':
        return (
          <ol key={k} className="mt-3 list-decimal space-y-2 pl-5 text-[15px] leading-7 text-on-surface-variant marker:font-semibold marker:text-pitch">
            {b.items.map((it, j) => <li key={j}>{inline(it, onNavigate, `${k}-${j}`)}</li>)}
          </ol>
        );
      case 'quote':
        return null; // rendered by LegalPage as the draft banner
      case 'table':
        return (
          <div key={k} className="mt-4 overflow-x-auto rounded-xl ring-1 ring-ink/10">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead className="bg-mist text-xs uppercase tracking-wide text-ink/70">
                <tr>{b.head.map((h, j) => <th key={j} scope="col" className="px-3 py-2.5 font-semibold">{inline(h, onNavigate, `${k}-h${j}`)}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-ink/5 bg-chalk">
                {b.rows.map((r, j) => (
                  <tr key={j} className="align-top">
                    {r.map((c, x) => (
                      <td key={x} className={`px-3 py-2.5 leading-6 text-on-surface-variant ${x === 0 ? 'font-medium text-ink' : ''}`}>
                        {inline(c, onNavigate, `${k}-${j}-${x}`)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
    }
  };

  return (
    <div>
      {sections.map((s, si) =>
        s.heading ? (
          <section key={si} aria-labelledby={slugify(s.heading.text)} className="mt-10 scroll-mt-28 border-t border-ink/10 pt-8 first:mt-0">
            <h2 id={slugify(s.heading.text)} className="font-display text-xl font-bold text-pitch">{inline(s.heading.text, onNavigate, `s${si}`)}</h2>
            {s.body.map((b, bi) => renderBlock(b, si * 1000 + bi))}
          </section>
        ) : (
          <div key={si}>{s.body.map((b, bi) => renderBlock(b, bi))}</div>
        ),
      )}
    </div>
  );
}

export function draftNotice(source: string): string | null {
  const m = /^> (DRAFT FOR LAWYER REVIEW|वकील की समीक्षा हेतु मसौदा)[^\n]*(\n> [^\n]*)*/m.exec(source);
  return m ? m[0].split('\n').map((l) => l.replace(/^> /, '')).join(' ') : null;
}

export function docTitle(source: string): string {
  return /^# (.+)$/m.exec(source)?.[1] ?? '';
}

export function sectionHeadings(source: string): string[] {
  return [...source.matchAll(/^## (.+)$/gm)].map((m) => m[1]);
}
