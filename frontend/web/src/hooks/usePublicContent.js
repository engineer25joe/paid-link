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
      if (active && !Array.isArray(result)) {
        setStatus({ loading: false, error: 'The server returned an unexpected catalogue response. Please retry or return later.' });
        return;
      }
      if (active) { setItems(result); setStatus({ loading: false, error: '' }); }
    }).catch((error) => {
      if (active) setStatus({ loading: false, error: getApiErrorMessage(error.data, error.message) });
    });
    return () => { active = false; };
  }, []);
  return { items, ...status };
}
