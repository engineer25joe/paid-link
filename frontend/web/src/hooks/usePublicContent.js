import { useEffect, useState } from 'react';
import { getPublicContent } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';

// Fetch only published catalogue data; backend access checks guard every protected file.
export function usePublicContent() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState({ loading: true, error: '' });
  useEffect(() => {
    let active = true;
    getPublicContent().then((result) => {
      if (active) { setItems(Array.isArray(result) ? result : []); setStatus({ loading: false, error: '' }); }
    }).catch((error) => {
      if (active) setStatus({ loading: false, error: getApiErrorMessage(error.data, error.message) });
    });
    return () => { active = false; };
  }, []);
  return { items, ...status };
}
