import React, { useState } from 'react';
import SEOHead from './SEOHead';
import { generateBreadcrumbSchema } from '../lib/schema';
import { CheckCircle, Clock, Mail, MessageSquare, Phone, Scale } from 'lucide-react';
import { SITE_NAME, absUrl, SUPPORT_EMAIL, PARTNERS_EMAIL } from '../lib/site';
import { api, ApiError } from '../lib/api/client';
import { fact, useLegalProfile } from '../lib/legal';
import PrivacyNote from './legal/PrivacyNote';

const TOPICS = [
  { value: 'booking', label: 'A booking' },
  { value: 'payment', label: 'Payment or refund' },
  { value: 'venue', label: 'A venue or its owner' },
  { value: 'content_report', label: 'Report a listing, photo or review' },
  { value: 'privacy', label: 'My personal data' },
  { value: 'grievance', label: 'A complaint about GroundKart' },
  { value: 'partnership', label: 'Listing my venue or partnering' },
  { value: 'other', label: 'Something else' },
];

interface ContactResponse {
  success: boolean;
  message: string;
  ticket_number?: string | null;
  ack_due_at?: string | null;
  resolve_due_at?: string | null;
}

const field =
  'w-full bg-[#F7F7F2] border border-ink/10 rounded-xl px-4 py-2.5 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-pitch/20';
const labelCls = 'block text-xs font-bold uppercase font-sans text-ink mb-1';

const fmt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : null;

export default function Contact() {
  const { data: profile } = useLegalProfile();
  const [result, setResult] = useState<ContactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [topic, setTopic] = useState('booking');
  const [bookingRef, setBookingRef] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');

  const breadcrumbs = [
    { name: 'Home', path: '/' },
    { name: 'Contact Us', path: '/contact' },
  ];

  const reset = () => {
    setResult(null);
    setError(null);
    setSubject('');
    setMessage('');
    setBookingRef('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<ContactResponse>('/api/v1/contact', {
        name,
        email,
        phone: phone || undefined,
        subject,
        message,
        category: topic,
        booking_reference: bookingRef || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'We could not send your message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] py-12 sm:py-16">
      <SEOHead
        title={`Contact ${SITE_NAME} | Support, complaints and venue partnerships`}
        description={`Contact ${SITE_NAME} about a booking, a refund, a venue listing or your personal data. Every message gets a ticket number.`}
        canonicalUrl={absUrl('/contact')}
        jsonLd={generateBreadcrumbSchema(breadcrumbs)}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav aria-label="Breadcrumb" className="mb-8">
          <ol className="flex items-center gap-2 text-xs font-sans text-on-surface-variant">
            <li><a href="/" className="hover:text-pitch transition-colors">Home</a></li>
            <li>/</li>
            <li className="text-pitch font-semibold" aria-current="page">Contact Us</li>
          </ol>
        </nav>

        <header className="mb-10 max-w-2xl">
          <h1 className="font-display text-3xl sm:text-5xl text-ink font-bold tracking-tight mb-4">Contact us</h1>
          <p className="font-sans text-base sm:text-lg text-on-surface-variant leading-relaxed">
            Questions about a booking, a refund, a listing or your data. Every message gets a ticket number, and we acknowledge it within 48 hours.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-ink/10 space-y-4">
              <h2 className="font-sans text-lg font-bold text-ink">Contact channels</h2>
              <Channel icon={<Mail size={20} />} title="Customer support">
                <a href={`mailto:${SUPPORT_EMAIL}`} className="font-sans text-sm font-bold text-pitch hover:underline">{SUPPORT_EMAIL}</a>
              </Channel>
              <Channel icon={<Phone size={20} />} title="Customer care">
                <p className="font-sans text-sm text-ink">{fact(profile, 'customer_care_phone', 'customer care phone')}</p>
              </Channel>
              <Channel icon={<Clock size={20} />} title="Hours">
                <p className="font-sans text-sm text-ink">{profile?.customer_care_hours || 'Messages are answered on working days; the form is open all the time.'}</p>
              </Channel>
              <Channel icon={<MessageSquare size={20} />} title="Venue partnerships">
                <a href={`mailto:${PARTNERS_EMAIL}`} className="font-sans text-sm font-bold text-pitch hover:underline">{PARTNERS_EMAIL}</a>
              </Channel>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-ink/10 space-y-3">
              <div className="flex items-center gap-2">
                <Scale size={18} className="text-pitch" aria-hidden />
                <h2 className="font-sans text-lg font-bold text-ink">Grievance Officer</h2>
              </div>
              <p className="text-sm text-ink">
                {fact(profile, 'grievance_officer_name', 'Grievance Officer name')}, {fact(profile, 'grievance_officer_designation', 'designation')}
              </p>
              <p className="text-sm text-on-surface-variant">
                {fact(profile, 'grievance_email', 'grievance email')} · {fact(profile, 'grievance_phone', 'grievance phone')}
              </p>
              <p className="text-xs leading-5 text-on-surface-variant">
                Complaints are acknowledged within 48 hours and resolved within one month; content complaints within 24 hours and 15 days.{' '}
                <a href="/grievance" className="font-medium text-pitch underline underline-offset-2">How we handle complaints</a>
              </p>
            </div>
          </div>

          <div className="lg:col-span-7 bg-white p-8 rounded-3xl border border-ink/10">
            {result ? (
              <div className="text-center py-10 space-y-4" role="status">
                <div className="w-16 h-16 rounded-full bg-pitch/10 text-pitch flex items-center justify-center mx-auto">
                  <CheckCircle size={36} />
                </div>
                <h2 className="font-display text-2xl font-bold text-ink">Message received</h2>
                {result.ticket_number && (
                  <p className="text-sm text-on-surface-variant">
                    Your ticket number is{' '}
                    <span data-testid="ticket-number" className="font-mono text-base font-bold text-pitch">{result.ticket_number}</span>
                  </p>
                )}
                <p className="font-sans text-sm text-on-surface-variant max-w-sm mx-auto leading-relaxed">{result.message}</p>
                {result.ack_due_at && (
                  <p className="text-xs text-on-surface-variant">
                    We will acknowledge it by {fmt(result.ack_due_at)} and aim to resolve it by {fmt(result.resolve_due_at)}.
                  </p>
                )}
                <button onClick={reset} className="bg-pitch text-chalk px-6 py-2.5 rounded-full text-xs font-bold transition hover:bg-[#15462E]">
                  Send another message
                </button>
              </div>
            ) : (
              <form data-testid="contact-form" onSubmit={handleSubmit} className="space-y-5">
                <h2 className="font-display text-2xl font-bold text-ink mb-2">Send a message</h2>
                {error && (
                  <div role="alert" className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-xs font-sans">{error}</div>
                )}
                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label htmlFor="contact-name" className={labelCls}>Your name</label>
                    <input id="contact-name" type="text" required minLength={2} value={name} onChange={(e) => setName(e.target.value)} className={field} autoComplete="name" />
                  </div>
                  <div>
                    <label htmlFor="contact-email" className={labelCls}>Email address</label>
                    <input id="contact-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={field} autoComplete="email" />
                  </div>
                  <div>
                    <label htmlFor="contact-phone" className={labelCls}>Phone (optional)</label>
                    <input id="contact-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className={field} autoComplete="tel" />
                  </div>
                  <div>
                    <label htmlFor="contact-topic" className={labelCls}>Topic</label>
                    <select id="contact-topic" value={topic} onChange={(e) => setTopic(e.target.value)} className={field}>
                      {TOPICS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                </div>
                {(topic === 'booking' || topic === 'payment') && (
                  <div>
                    <label htmlFor="contact-ref" className={labelCls}>Booking reference (if you have one)</label>
                    <input id="contact-ref" type="text" value={bookingRef} onChange={(e) => setBookingRef(e.target.value)} className={field} />
                  </div>
                )}
                <div>
                  <label htmlFor="contact-subject" className={labelCls}>Subject</label>
                  <input id="contact-subject" type="text" required minLength={2} value={subject} onChange={(e) => setSubject(e.target.value)} className={field} />
                </div>
                <div>
                  <label htmlFor="contact-message" className={labelCls}>Message</label>
                  <textarea id="contact-message" required minLength={5} rows={5} value={message} onChange={(e) => setMessage(e.target.value)} className={`${field} resize-none`} />
                  <p className="mt-1 text-xs text-on-surface-variant">Please do not include card numbers, passwords or children's personal details.</p>
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-pitch hover:bg-[#15462E] disabled:opacity-60 text-chalk font-sans font-bold py-3 rounded-xl text-sm transition active:scale-[0.98] cursor-pointer"
                >
                  {loading ? 'Sending…' : 'Send message'}
                </button>
                <PrivacyNote>We use your name, email and phone only to answer this message and keep a record of the complaint.</PrivacyNote>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Channel({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-10 h-10 rounded-lg bg-pitch/10 flex items-center justify-center text-pitch shrink-0">{icon}</div>
      <div>
        <h3 className="font-sans text-xs uppercase font-semibold text-on-surface-variant">{title}</h3>
        {children}
      </div>
    </div>
  );
}
