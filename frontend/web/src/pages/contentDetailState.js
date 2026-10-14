// Keep content-detail state decisions independent so missing catalogue rows
// and malformed protected-access responses cannot become render-time crashes.
export function findContent(items, id) {
  if (!Array.isArray(items) || !/^\d+$/.test(String(id ?? ''))) return null;
  return items.find((entry) => entry && String(entry.id) === String(id)) ?? null;
}

export function getAuthorizedContent(result) {
  const content = result?.content;
  if (!content || !['pdf', 'video'].includes(content.content_type) || typeof content.file_url !== 'string') {
    throw new Error('The server did not return a valid protected resource. Please try again.');
  }

  let url;
  try { url = new URL(content.file_url); } catch {
    throw new Error('The server returned an invalid protected resource link. Please try again.');
  }
  // Protected Cloudinary links are HTTPS signed URLs. Never navigate to a
  // script or insecure URL, even if an API response is malformed.
  if (url.protocol !== 'https:' || url.username || url.password || !(url.hostname === 'cloudinary.com' || url.hostname.endsWith('.cloudinary.com'))) {
    throw new Error('The protected resource link is not a secure file-host URL. Please contact support.');
  }
  return { ...content, file_url: url.href };
}

export function getContentAccessError(error) {
  if (error?.status === 401) return { state: 'authentication-required', message: 'Please sign in to check your access.' };
  if (error?.status === 403) return { state: 'purchase-required', message: 'This resource is not in your library yet. Purchase it to unlock access.' };
  if (error?.status === 404) return { state: 'not-found', message: 'This resource is unavailable or has been unpublished.' };
  if (!error?.status) return { state: 'network-error', message: 'We could not reach the server. Check your connection and try again.' };
  return { state: 'access-denied', message: error.message || 'Access could not be granted. Please try again.' };
}
