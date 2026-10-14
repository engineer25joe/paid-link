import { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TextInput, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

export function AdminSettingsScreen() {
  const [rate, setRate] = useState(''); const [history, setHistory] = useState([]); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const load = useCallback(async () => { const result = await api.get(API_PATHS.adminCreditRate); setRate(result.rate); setHistory(result.history || []); }, []);
  useFocusEffect(useCallback(() => { let active = true; load().catch((failure) => { if (active) setError(getApiErrorMessage(failure.data, failure.message)); }); return () => { active = false; }; }, [load]));
  async function save() { setBusy(true); setError(''); try { const result = await api.put(API_PATHS.adminCreditRate, { rate }); setNotice(`Saved: 1 credit = KES ${result.rate}. Historical transactions remain unchanged.`); await load(); } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } finally { setBusy(false); } }
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Platform configuration" title="Credit conversion" description="Money amounts in completed transactions are never recalculated when this rate changes."/><Text style={styles.label}>1 credit = KES</Text><TextInput keyboardType="decimal-pad" value={rate} onChangeText={setRate} style={styles.input}/><AppButton title={busy ? 'Saving…' : 'Save conversion rate'} disabled={busy || !rate} onPress={save}/>{error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}{notice ? <Text accessibilityRole="status" style={styles.notice}>{notice}</Text> : null}<Text style={styles.section}>Rate history</Text>{history.map((row, index) => <View key={`${row.created_at}-${index}`} style={styles.row}><Text style={styles.label}>KES {row.rate} / credit</Text><Text style={styles.muted}>By {row.changed_by} · {new Date(row.created_at).toLocaleString()}</Text></View>)}</View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, label: { color: '#000000', fontWeight: '700' }, input: { minHeight: 48, borderWidth: 1, borderColor: '#B8B8B8', borderRadius: 9, padding: 12, marginVertical: 10 }, section: { color: '#000000', fontSize: 20, fontWeight: '800', marginTop: 25 }, row: { borderBottomWidth: 1, borderBottomColor: '#E5E5E5', paddingVertical: 12 }, muted: { color: '#595959', marginTop: 5 }, error: { color: '#B00000', marginTop: 12 }, notice: { color: '#176343', marginTop: 12 } });
