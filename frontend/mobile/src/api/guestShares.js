import { api } from './client';
import { API_PATHS } from './config';

// Guest tokens are sent only to the public backend endpoint. The backend
// checks expiry, revocation, usage, payment and protected content access.
export const getSharedLink = (token) => api.get(API_PATHS.sharedContent(token), { authenticated: false });
export const getGuestContent = (token) => api.get(API_PATHS.guestContent(token), { authenticated: false });
export const startGuestPayment = (token, phoneNumber) => api.post(API_PATHS.guestPayment(token), { phone_number: phoneNumber }, { authenticated: false });
export const getGuestPaymentStatus = (token) => api.get(API_PATHS.guestPaymentStatus(token), { authenticated: false });
