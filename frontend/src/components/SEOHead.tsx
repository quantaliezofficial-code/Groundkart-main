import React from 'react';
import { Helmet } from 'react-helmet-async';
import { SITE_NAME, absUrl } from '../lib/site';

export interface SEOHeadProps {
  title?: string;
  description?: string;
  canonicalUrl?: string;
  ogImage?: string;
  ogType?: 'website' | 'article' | 'place' | 'business.business';
  /** Alt text for the share image. Defaults to the page title. */
  ogImageAlt?: string;
  noindex?: boolean;
  jsonLd?: Record<string, any> | Array<Record<string, any>>;
}

const DEFAULT_TITLE = `${SITE_NAME} — Book Grounds, Halls and Event Venues`;
const DEFAULT_DESC =
  `Find and book sports grounds, banquet halls, party venues, farmhouses and meeting spaces on ${SITE_NAME}. Compare photos, prices and availability, then request your date.`;
const DEFAULT_CANONICAL = absUrl('/');
const DEFAULT_OG_IMAGE = absUrl('/og-image.jpg');

export default function SEOHead({
  title = DEFAULT_TITLE,
  description = DEFAULT_DESC,
  canonicalUrl = DEFAULT_CANONICAL,
  ogImage = DEFAULT_OG_IMAGE,
  ogType = 'website',
  ogImageAlt,
  noindex = false,
  jsonLd,
}: SEOHeadProps) {
  // Ensure canonical URL is absolute and uses HTTPS
  const resolvedCanonical = canonicalUrl.startsWith('http')
    ? canonicalUrl
    : absUrl(canonicalUrl);

  const resolvedOgImage = ogImage.startsWith('http')
    ? ogImage
    : absUrl(ogImage);

  const isDefaultImage = resolvedOgImage === DEFAULT_OG_IMAGE;
  const robotsContent = noindex ? 'noindex, nofollow' : 'index, follow';

  return (
    <Helmet>
      {/* Standard Metadata */}
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={resolvedCanonical} />
      <meta name="robots" content={robotsContent} />

      {/* Open Graph / Facebook */}
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:type" content={ogType} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={resolvedCanonical} />
      <meta property="og:locale" content="en_IN" />
      <meta property="og:image" content={resolvedOgImage} />
      {/* Dimensions are only known for our own 1200x630 card; a venue's
          cover photo can be any shape, so they are omitted for those
          rather than stated wrongly. */}
      {isDefaultImage && <meta property="og:image:width" content="1200" />}
      {isDefaultImage && <meta property="og:image:height" content="630" />}
      <meta property="og:image:alt" content={ogImageAlt || title} />

      {/* Twitter / X */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={resolvedOgImage} />
      <meta name="twitter:image:alt" content={ogImageAlt || title} />

      {/* Structured Data (JSON-LD) */}
      {jsonLd && (
        <script type="application/ld+json">
          {JSON.stringify(jsonLd)}
        </script>
      )}
    </Helmet>
  );
}
