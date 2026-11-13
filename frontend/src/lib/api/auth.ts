import { api } from './client';
import type { AccessTokenResponse, SignupResponse, UserMe } from './types';

import { LEGAL_VERSIONS } from '../legal';

export const authApi = {
  /** ageConfirmed: the unticked "I confirm I am 18 years or older" box (adults only). */
  signup: (name: string, email: string, password: string, phone: string, ageConfirmed = false) =>
    api.post<SignupResponse>(
      '/api/v1/auth/signup',
      {
        name,
        email,
        password,
        phone,
        age_confirmed: ageConfirmed,
        terms_version: LEGAL_VERSIONS.terms,
        notice_version: LEGAL_VERSIONS.notice,
      },
      { skipAuth: true },
    ),

  /** otp: authenticator or recovery code, for admins with two-step sign-in. */
  login: (loginId: string, password: string, otp?: string) =>
    api.post<AccessTokenResponse>(
      '/api/v1/auth/login',
      { login_id: loginId, password, ...(otp ? { otp } : {}) },
      { skipAuth: true, skipRefreshRetry: true },
    ),

  logout: () => api.post<void>('/api/v1/auth/logout', undefined, { skipRefreshRetry: true }),

  me: () => api.get<UserMe>('/api/v1/users/me'),

  deleteAccount: () => api.delete<void>('/api/v1/users/me'),
};
