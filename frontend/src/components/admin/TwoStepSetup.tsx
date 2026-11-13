import React, { useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import QRCode from 'qrcode';
import { KeyRound, ShieldCheck } from 'lucide-react';
import { twoFactorApi } from '../../lib/api/compliance';
import { useAuth } from '../../lib/auth';
import { errorText } from '../../lib/format';
import { Button, CopyButton, Field, Notice, Panel, inputClass } from '../dashboard/kit';

/**
 * Admin two-step sign-in (TOTP). The QR code is drawn in the browser from
 * the otpauth link, so the secret never goes to a third-party service.
 * After it is turned on, the admin signs in again with a code: the current
 * session was opened with the password only.
 */
export default function TwoStepSetup({ required = false }: { required?: boolean }) {
  const { user, logout } = useAuth();
  const [code, setCode] = useState('');
  const [qr, setQr] = useState<string | null>(null);

  const setup = useMutation({ mutationFn: twoFactorApi.setup });
  const enable = useMutation({ mutationFn: (c: string) => twoFactorApi.enable(c) });

  useEffect(() => {
    if (!setup.data) return;
    QRCode.toDataURL(setup.data.otpauth_uri, { margin: 1, width: 220, errorCorrectionLevel: 'M' })
      .then(setQr)
      .catch(() => setQr(null));
  }, [setup.data]);

  if (user?.two_factor_enabled && !enable.data) {
    return (
      <Panel title="Two-step sign-in" description="On. Every sign-in to this account asks for a code from your authenticator app.">
        <p className="flex items-center gap-2 text-sm text-ink">
          <ShieldCheck size={16} className="text-primary-container" aria-hidden="true" /> Your account is protected.
        </p>
      </Panel>
    );
  }

  if (enable.data) {
    return (
      <Panel title="Two-step sign-in is on" description="Save these recovery codes now. Each works once if you lose your phone. They are not shown again.">
        <div className="space-y-4" data-testid="recovery-codes">
          <ul className="grid grid-cols-2 gap-2 rounded-xl bg-surface-container-low p-4 font-mono text-sm text-ink sm:grid-cols-4">
            {enable.data.recovery_codes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            <CopyButton text={enable.data.recovery_codes.join('\n')} label="Copy codes" />
            <Button variant="primary" onClick={() => void logout()}>
              I saved them. Sign in again
            </Button>
          </div>
          <Notice>Sign in again with your password and a code from the app to continue.</Notice>
        </div>
      </Panel>
    );
  }

  return (
    <Panel
      title="Set up two-step sign-in"
      description={
        required
          ? 'Admin accounts must use an authenticator app on this server. Set it up to open the console.'
          : 'Protect this admin account with a code from an authenticator app.'
      }
    >
      {!setup.data ? (
        <div className="space-y-4">
          <p className="text-sm text-on-surface-variant">
            You need an authenticator app on your phone, such as Google Authenticator, Microsoft Authenticator or 2FAS.
          </p>
          {setup.isError ? <Notice tone="error">{errorText(setup.error)}</Notice> : null}
          <Button variant="primary" loading={setup.isPending} onClick={() => setup.mutate()}>
            <KeyRound size={15} aria-hidden="true" /> Start set-up
          </Button>
        </div>
      ) : (
        <form
          className="grid grid-cols-1 gap-6 md:grid-cols-[240px_1fr]"
          onSubmit={(e) => {
            e.preventDefault();
            enable.mutate(code.replace(/\s/g, ''));
          }}
        >
          <div className="flex flex-col items-center gap-2">
            {qr ? (
              <img src={qr} alt="QR code to add GroundKart to your authenticator app" width={220} height={220} className="rounded-lg bg-white p-2 ring-1 ring-ink/10" />
            ) : (
              <div className="h-[220px] w-[220px] rounded-lg shimmer" />
            )}
          </div>
          <div className="space-y-4">
            <ol className="list-decimal space-y-1 pl-5 text-sm text-ink">
              <li>In the app, add an account and scan the QR code.</li>
              <li>Can't scan? Choose "enter a setup key" and type the key below.</li>
              <li>Enter the 6-digit code the app shows.</li>
            </ol>
            <div className="flex flex-wrap items-center gap-2 rounded-lg bg-surface-container-low px-3 py-2">
              <code className="break-all font-mono text-sm text-ink" data-testid="totp-secret">
                {setup.data.secret}
              </code>
              <CopyButton text={setup.data.secret} label="Copy key" />
            </div>
            <Field label="6-digit code">
              <input
                className={`${inputClass} max-w-[180px] tracking-widest`}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={7}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />
            </Field>
            {enable.isError ? <Notice tone="error">{errorText(enable.error)}</Notice> : null}
            <Button type="submit" variant="primary" loading={enable.isPending} disabled={code.replace(/\s/g, '').length < 6}>
              Turn on two-step sign-in
            </Button>
          </div>
        </form>
      )}
    </Panel>
  );
}
