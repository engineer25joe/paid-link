import { API_PATHS } from './config.js';
import { api } from './client.js';

// Marketplace and workspace requests stay outside page components.
export const ADMIN_LIST_ENDPOINTS = {
  users: '/api/admin/users/', creators: '/api/admin/creators/', learners: '/api/admin/learners/',
  content: '/api/admin/content/', purchases: '/api/admin/purchases/', ledger: '/api/admin/ledger/',
  withdrawals: '/api/admin/withdrawals/',
};
export const getPublicContent = () => api.get(API_PATHS.content, { authenticated: false });
export const getMyContent = () => api.get(API_PATHS.myContent);
export const getContentAccess = (id) => api.get(API_PATHS.contentAccess(id));
export const purchaseContent = (id) => api.post(API_PATHS.purchase(id), {});
export const createContent = (formData) => api.post(API_PATHS.contentCreate, formData);
export const updateContent = (id, changes) => api.patch(API_PATHS.contentUpdate(id), changes);
export const setContentPublished = (id, isPublished) => api.patch(API_PATHS.contentPublish(id), { is_published: isPublished });
export const getCreatorEarnings = () => api.get(API_PATHS.creatorEarnings);
export const getCreatorContentEarnings = () => api.get(API_PATHS.creatorContentEarnings);
export const getAdminDashboard = () => api.get(API_PATHS.adminDashboard);
export const getAdminList = (path) => api.get(path);
export const getAdminContent = (id) => api.get(`/api/admin/content/${id}/`);
export const updateAdminContent = (id, changes) => api.patch(API_PATHS.contentUpdate(id), changes);
export const publishAdminContent = (id, published) => api.patch(API_PATHS.contentPublish(id), { is_published: published });
export const runAdminWithdrawalAction = (id, action) => {
  if (!['approve', 'cancel'].includes(action)) throw new Error('Unsupported withdrawal action.');
  return api.post(`/api/admin/withdrawals/${id}/${action}/`, {});
};
