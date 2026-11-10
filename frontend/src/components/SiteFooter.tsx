import React from 'react';
import { SUPPORT_EMAIL } from '../lib/site';

interface SiteFooterProps {
  onNavigate: (path: string) => void;
  onListVenue: () => void;
}

const EXPLORE = [
  { label: 'All venues', path: '/search' },
  { label: 'Sports grounds', path: '/categories/sports' },
  { label: 'Banquet halls', path: '/categories/banquet-halls' },
  { label: 'Farmhouses', path: '/categories/farmhouses' },
  { label: 'Corporate spaces', path: '/categories/corporate' },
];

const COMPANY = [
  { label: 'About', path: '/about' },
  { label: 'Contact', path: '/contact' },
  { label: 'Help and support', path: '/support' },
];

const LEGAL = [
  { label: 'Privacy policy', path: '/privacy' },
  { label: 'Terms of service', path: '/terms' },
];

function FooterLink({ label, path, onNavigate }: { label: string; path: string; onNavigate: (p: string) => void }) {
  return (
    <li>
      <a
        href={path}
        onClick={(e) => {
          e.preventDefault();
          onNavigate(path);
        }}
        className="text-chalk/70 hover:text-marigold"
      >
        {label}
      </a>
    </li>
  );
}

export default function SiteFooter({ onNavigate, onListVenue }: SiteFooterProps) {
  return (
    <footer className="mt-auto bg-pitch pt-14 pb-8 text-[15px]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-12">
          <div className="col-span-2 md:col-span-4 md:pr-8">
            <a
              href="/"
              onClick={(e) => {
                e.preventDefault();
                onNavigate('/');
              }}
              className="inline-block"
            >
              <img src="/logo-full.webp" alt="GroundKart" width={180} height={60} className="h-14 w-auto" loading="lazy" />
            </a>
            <p className="mt-4 max-w-xs leading-relaxed text-chalk/70">
              Book grounds, halls and event venues, from a weekend match to a wedding.
            </p>
            <p className="mt-4 text-chalk/70">
              <a href={`mailto:${SUPPORT_EMAIL}`} className="hover:text-marigold">
                {SUPPORT_EMAIL}
              </a>
            </p>
          </div>

          <div className="md:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-chalk">Explore</h2>
            <ul className="space-y-3">
              {EXPLORE.map((l) => (
                <FooterLink key={l.path} {...l} onNavigate={onNavigate} />
              ))}
            </ul>
          </div>

          <div className="md:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-chalk">Venue owners</h2>
            <ul className="space-y-3">
              <li>
                <button type="button" onClick={onListVenue} className="text-left text-chalk/70 hover:text-marigold cursor-pointer">
                  List your venue
                </button>
              </li>
              <li>
                <button type="button" onClick={onListVenue} className="text-left text-chalk/70 hover:text-marigold cursor-pointer">
                  Owner dashboard
                </button>
              </li>
              <FooterLink label="Become a partner" path="/contact" onNavigate={onNavigate} />
            </ul>
          </div>

          <div className="md:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-chalk">Company</h2>
            <ul className="space-y-3">
              {COMPANY.map((l) => (
                <FooterLink key={l.path} {...l} onNavigate={onNavigate} />
              ))}
            </ul>
          </div>

          <div className="md:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-chalk">Legal</h2>
            <ul className="space-y-3">
              {LEGAL.map((l) => (
                <FooterLink key={l.path} {...l} onNavigate={onNavigate} />
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-2 border-t border-white/10 pt-6 text-sm text-chalk/60 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} GroundKart. All rights reserved.</p>
          <p>
            Designed and created by{' '}
            <a href="https://www.quantaliez.com" target="_blank" rel="noopener" className="text-chalk/80 hover:text-marigold">
              Quantaliez
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
