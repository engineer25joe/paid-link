import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getSharedContent, getGuestPaymentStatus, initiateGuestPayment } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';
import { useCountdown } from '../hooks/useCountdown.js';

export function SharedContentPage() {
  const { token } = useParams(); const navigate = useNavigate();
  const [share, setShare] = useState(null); const [phone, setPhone] = useState(''); const [paymentToken, setPaymentToken] = useState('');
  const [state, setState] = useState({ loading: true, busy: false, error: '', notice: '' });
  const countdown = useCountdown(share?.expires_at || new Date().toISOString());
  useEffect(() => { let active = true; getSharedContent(token).then((data) => { if (active) { setShare(data); setState((s) => ({ ...s, loading: false, error: data.status === 'ACTIVE' ? '' : `This link is ${data.status.toLowerCase()}.` })); } }).catch((error) => { if (active) setState((s) => ({ ...s, loading: false, error: getApiErrorMessage(error.data, error.message) })); }); return () => { active = false; }; }, [token]);
  useEffect(() => { if (!paymentToken) return undefined; let active = true; const poll = async () => { try { const result = await getGuestPaymentStatus(paymentToken); if (!active) return; if (result.status === 'completed' && result.access_url) navigate(result.access_url, { replace: true }); else if (result.status === 'completed_no_access') setState((s) => ({ ...s, busy: false, error: 'The payment was verified, but this share link is no longer available. Contact the sharer for help.' })); else if (['failed', 'cancelled'].includes(result.status)) setState((s) => ({ ...s, busy: false, error: `M-Pesa payment ${result.status}. You may try again while the link is active.` })); } catch { /* Retry with the private payment status token. */ } }; poll(); const timer = window.setInterval(poll, 4000); return () => { active = false; window.clearInterval(timer); }; }, [paymentToken, navigate]);
  async function pay(event) { event.preventDefault(); setState((s) => ({ ...s, busy: true, error: '', notice: '' })); try { const result = await initiateGuestPayment(token, phone); setPaymentToken(result.payment_token); setState((s) => ({ ...s, notice: `${result.message} Amount: KES ${result.amount_kes}.` })); } catch (error) { setState((s) => ({ ...s, busy: false, error: getApiErrorMessage(error.data, error.message) })); } }
  if (state.loading) return <section className="page-shell narrow-shell"><p className="notice" role="status">Loading shared resource…</p></section>;
  if (!share?.content || share.status !== 'ACTIVE' || countdown.expired) return <section className="page-shell narrow-shell"><PageIntro eyebrow="Guest link" title="This link is unavailable" description={countdown.expired ? 'This access link has expired.' : state.error || 'The share cannot accept payments.'}/><Link className="button button-light" to="/explore">Explore ElimuBang</Link></section>;
  return <section className="page-shell narrow-shell"><PageIntro eyebrow="Guest access · M-Pesa only" title={share.content.title} description={share.content.description}/>
    <div className="share-expiry"><span>Share link expires in</span><strong>{countdown.label}</strong></div><p className="detail-price"><span>One-time price</span><strong>KES {share.content.price_kes}</strong></p><p>Maximum remaining purchases: {share.remaining_uses}. Payment conversion rate: 1 credit = KES {share.content.conversion_rate}.</p>
    <form className="editor-form" onSubmit={pay}><label>M-Pesa phone number<input type="tel" autoComplete="tel" required value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="0712345678"/></label>{state.error && <p className="notice notice-error" role="alert">{state.error}</p>}{state.notice && <p className="notice" role="status">{state.notice}</p>}<button className="button button-primary" disabled={state.busy || countdown.expired || share.remaining_uses <= 0}>{state.busy ? 'Waiting for verified M-Pesa payment…' : 'Pay with M-Pesa'}</button></form>
    <p className="fine-print">No ElimuBang account is required. Access is issued only after the backend verifies the M-Pesa payment and expires two hours later.</p>
  </section>;
}
