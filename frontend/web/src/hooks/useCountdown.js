import { useEffect, useState } from 'react';

export function useCountdown(expiresAt) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [expiresAt]);
  const seconds = Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
  const hours = String(Math.floor(seconds / 3600)).padStart(2, '0');
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
  const remainder = String(seconds % 60).padStart(2, '0');
  return { seconds, label: `${hours}:${minutes}:${remainder}`, expired: seconds === 0 };
}

export function estimateCredits(amountKes, rate) {
  if (!/^\d+(\.\d{1,2})?$/.test(String(amountKes)) || !/^\d+(\.\d{1,4})?$/.test(String(rate))) return '';
  const [moneyWhole, moneyFraction = ''] = String(amountKes).split('.');
  const [whole, fractional = ''] = String(rate).split('.');
  const moneyCents = BigInt(moneyWhole) * 100n + BigInt(moneyFraction.padEnd(2, '0'));
  const rateScaled = BigInt(whole) * 10_000n + BigInt(fractional.padEnd(4, '0'));
  if (!rateScaled) return '';
  const hundredths = (moneyCents * 10_000n) / rateScaled;
  return `${hundredths / 100n}.${String(hundredths % 100n).padStart(2, '0')}`;
}

export function estimateRequiredCredits(amountKes, rate) {
  if (!/^\d+(\.\d{1,2})?$/.test(String(amountKes)) || !/^\d+(\.\d{1,4})?$/.test(String(rate))) return '';
  const [moneyWhole, moneyFraction = ''] = String(amountKes).split('.');
  const [whole, fractional = ''] = String(rate).split('.');
  const moneyCents = BigInt(moneyWhole) * 100n + BigInt(moneyFraction.padEnd(2, '0'));
  const rateScaled = BigInt(whole) * 10_000n + BigInt(fractional.padEnd(4, '0'));
  if (!rateScaled) return '';
  const numerator = moneyCents * 10_000n;
  const hundredths = (numerator + rateScaled - 1n) / rateScaled;
  return `${hundredths / 100n}.${String(hundredths % 100n).padStart(2, '0')}`;
}

export function countdownFor(expiresAt, now = Date.now()) {
  const seconds = Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
  return { seconds, expired: seconds === 0 };
}
