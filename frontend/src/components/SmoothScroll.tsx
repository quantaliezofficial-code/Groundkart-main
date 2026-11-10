import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

/**
 * Scroll management for the app: restores position on back/forward, resets
 * to the top on a new page, honours #hash links, and exposes a small
 * scrollTo() helper.
 *
 * Scrolling itself is the browser's own. An earlier version replaced it
 * with a JavaScript scroll engine that eased every wheel tick; that is what
 * made pages feel laggy and jittery, fought with nested scroll areas
 * (drawers, dashboards, dropdowns) and added weight to every page. Native
 * scrolling is smoother, respects the user's OS settings and costs nothing.
 */

export interface ScrollToOptions {
  /** Pixels to offset the final position by (negative leaves room for a sticky header). */
  offset?: number;
  /** Jump without animating. */
  immediate?: boolean;
  /** Accepted for backwards compatibility; native scrolling picks its own duration. */
  duration?: number;
}

interface SmoothScrollContextType {
  scrollTo: (target: string | number | HTMLElement, options?: ScrollToOptions) => void;
}

const SmoothScrollContext = createContext<SmoothScrollContextType>({ scrollTo: () => {} });

export const useSmoothScroll = () => useContext(SmoothScrollContext);

const SCROLL_POSITIONS_STORAGE_KEY = 'groundkart_scroll_positions';

function readStoredPositions(): Record<string, number> {
  try {
    const raw = sessionStorage.getItem(SCROLL_POSITIONS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;
}

function nativeScrollTo(top: number, immediate: boolean) {
  const behavior: ScrollBehavior = immediate || prefersReducedMotion() ? 'auto' : 'smooth';
  try {
    window.scrollTo({ top: Math.max(0, top), behavior });
  } catch {
    // Very old engines only accept the two-argument form.
    window.scrollTo(0, Math.max(0, top));
  }
}

export default function SmoothScroll({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navType = useNavigationType();

  const prevPathname = useRef(location.pathname);
  const positions = useRef<Record<string, number>>(readStoredPositions());
  const routeKey = useRef(location.key || location.pathname + location.search);

  // Remember where the user was on each page so Back returns them there.
  useEffect(() => {
    routeKey.current = location.key || location.pathname + location.search;
    const pathKey = location.pathname + location.search;
    let ticking = false;

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        const y = window.scrollY;
        positions.current[routeKey.current] = y;
        positions.current[pathKey] = y;
        try {
          sessionStorage.setItem(SCROLL_POSITIONS_STORAGE_KEY, JSON.stringify(positions.current));
        } catch {
          // Storage can be unavailable (private mode, quota). Not worth surfacing.
        }
        ticking = false;
      });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [location.pathname, location.search, location.key]);

  useEffect(() => {
    const isNewPage = prevPathname.current !== location.pathname;
    prevPathname.current = location.pathname;

    if (location.hash) {
      let target: Element | null = null;
      try {
        target = document.querySelector(location.hash);
      } catch {
        target = null; // not a valid selector — ignore
      }
      if (target instanceof HTMLElement) {
        nativeScrollTo(target.getBoundingClientRect().top + window.scrollY - 80, false);
        return;
      }
    }

    if (navType === 'POP') {
      const key = location.key || location.pathname + location.search;
      const y = positions.current[key] ?? positions.current[location.pathname + location.search] ?? 0;
      nativeScrollTo(y, true);
      // Again next frame: content that loads asynchronously may not have
      // been tall enough to reach y on the first attempt.
      const raf = window.requestAnimationFrame(() => nativeScrollTo(y, true));
      return () => window.cancelAnimationFrame(raf);
    }

    if (isNewPage) nativeScrollTo(0, true);
  }, [location.pathname, location.search, location.hash, location.key, navType]);

  const scrollTo = useCallback((target: string | number | HTMLElement, options: ScrollToOptions = {}) => {
    const { offset = 0, immediate = false } = options;
    if (typeof target === 'number') {
      nativeScrollTo(target + offset, immediate);
      return;
    }
    let el: Element | null = null;
    if (typeof target === 'string') {
      try {
        el = document.querySelector(target);
      } catch {
        el = null;
      }
    } else {
      el = target;
    }
    if (el instanceof HTMLElement) {
      nativeScrollTo(el.getBoundingClientRect().top + window.scrollY + offset, immediate);
    }
  }, []);

  const value = useMemo(() => ({ scrollTo }), [scrollTo]);
  return <SmoothScrollContext.Provider value={value}>{children}</SmoothScrollContext.Provider>;
}
