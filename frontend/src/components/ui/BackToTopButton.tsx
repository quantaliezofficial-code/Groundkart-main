import React, { useEffect, useState } from 'react';
import { ArrowUp } from 'lucide-react';
import { useSmoothScroll } from '../SmoothScroll';

/** Appears after the first screen of scrolling. Desktop and tablet only:
 * on phones the browser's own tap-the-status-bar gesture does this job and
 * a floating button would sit on top of content. */
export default function BackToTopButton() {
  const [isVisible, setIsVisible] = useState(false);
  const { scrollTo } = useSmoothScroll();

  useEffect(() => {
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        setIsVisible(window.scrollY > 600);
        ticking = false;
      });
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  if (!isVisible) return null;

  return (
    <button
      type="button"
      onClick={() => scrollTo(0)}
      aria-label="Scroll to top"
      title="Back to top"
      className="fixed bottom-6 right-6 z-40 hidden sm:flex h-11 w-11 items-center justify-center rounded-full border border-pitch/10 bg-chalk text-pitch shadow-[0_8px_24px_rgba(6,40,29,0.14)] transition-colors hover:bg-pitch hover:text-chalk focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marigold focus-visible:ring-offset-2 cursor-pointer"
    >
      <ArrowUp size={18} aria-hidden="true" />
    </button>
  );
}
