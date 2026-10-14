import { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TextInput, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

export function WalletScreen() {
  const { user, refreshProfile } = useAuth(); const [wallet, setWallet] = useState({ transactions: [], payments: [] });
  const [rate, setRate] = useState(''); const [amount, setAmount] = useState(''); const [phone, setPhone] = useState(user?.phone_number || '');
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const load = useCallback(async () => { const [rows, conversion] = await Promise.all([api.get(API_PATHS.walletTransactions), api.get(API_PATHS.creditRate, { authenticated: false })]); setWallet(rows); setRate(conversion.credit_to_kes_rate); }, []);
  useFocusEffect(useCallback(() => { let active = true; Promise.all([api.get(API_PATHS.walletTransactions), api.get(API_PATHS.creditRate, { authenticated: false })]).then(([rows, conversion]) => { if (active) { setWallet(rows); setRate(conversion.credit_to_kes_rate); } }).catch((failure) => { if (active) setError(getApiErrorMessage(failure.data, failure.message)); }); return () => { active = false; }; }, []));
  async function topUp() { setBusy(true); setError(''); setNotice(''); try { const result = await api.post(API_PATHS.initiateTopup, { amount, phone_number: phone }); setNotice(`M-Pesa request started for KES ${result.amount_kes}. ${result.credits_awarded} credits will be added after provider verification.`); await load(); } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } finally { setBusy(false); } }
  async function refresh() { setBusy(true); try { const before = wallet.payments || []; await load(); const next = await api.get(API_PATHS.walletTransactions); if (next.payments?.some((row) => row.status === 'completed' && before.some((old) => old.id === row.id && old.status !== 'completed'))) await refreshProfile(); setWallet(next); } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } finally { setBusy(false); } }
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Wallet" title={`${user?.credits ?? '—'} credits`} description={`M-Pesa top-ups use the live rate: 1 credit = KES ${rate || '…'}. Balance changes only after verified payment.`}/>
    <Text style={styles.label}>Top Up Credits · amount in KES</Text><TextInput accessibilityLabel="Top-up KES amount" keyboardType="number-pad" value={amount} onChangeText={setAmount} placeholder="100" style={styles.input}/><Text style={styles.label}>M-Pesa phone number</Text><TextInput accessibilityLabel="M-Pesa phone number" keyboardType="phone-pad" value={phone} onChangeText={setPhone} placeholder="0712345678" style={styles.input}/><AppButton title={busy ? 'Waiting…' : 'Top Up Credits'} disabled={busy || !amount || !phone} onPress={topUp}/>
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}{notice ? <Text accessibilityRole="status" style={styles.notice}>{notice}</Text> : null}
    <Text style={styles.section}>Wallet history</Text>{[...(wallet.payments || []).map((row) => ({ ...row, label: 'M-Pesa top-up', value: `${row.credits_awarded ?? '—'} credits · KES ${row.amount_kes ?? row.amount} · ${row.status}` })), ...(wallet.transactions || []).map((row) => ({ ...row, label: row.reason || row.description || row.type, value: `${row.amount} credits · balance ${row.balance_after}` }))].map((row, index) => <View key={`${row.id}-${index}`} style={styles.row}><Text style={styles.label}>{row.label}</Text><Text style={styles.muted}>{row.value}</Text></View>)}
    <AppButton title="Refresh payment status" secondary disabled={busy} onPress={refresh}/>{busy ? <ActivityIndicator color="#FF0000" style={{ margin: 10 }}/> : null}
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, label: { color: '#000000', fontWeight: '700', marginBottom: 7 }, input: { minHeight: 48, borderWidth: 1, borderColor: '#B8B8B8', borderRadius: 9, padding: 12, color: '#000000', fontSize: 16, marginBottom: 12 }, section: { color: '#000000', fontSize: 20, fontWeight: '800', marginTop: 26, marginBottom: 10 }, row: { borderBottomWidth: 1, borderBottomColor: '#E5E5E5', paddingVertical: 12 }, muted: { color: '#595959', marginTop: 5 }, error: { color: '#B00000', marginVertical: 12 }, notice: { color: '#176343', marginVertical: 12 } });
