import { useEffect, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

function estimateCredits(price, rate) {
  if (!/^\d+(\.\d{1,2})?$/.test(String(price)) || !/^\d+(\.\d{1,4})?$/.test(String(rate))) return '—';
  const [moneyWhole, moneyFraction = ''] = String(price).split('.');
  const [rateWhole, rateFraction = ''] = String(rate).split('.');
  const cents = BigInt(moneyWhole) * 100n + BigInt(moneyFraction.padEnd(2, '0'));
  const rateUnits = BigInt(rateWhole) * 10000n + BigInt(rateFraction.padEnd(4, '0'));
  if (!rateUnits) return '—';
  const creditCents = (cents * 10000n + rateUnits - 1n) / rateUnits;
  return `${creditCents / 100n}.${String(creditCents % 100n).padStart(2, '0')}`;
}

export function CreatorEditorScreen({ route, navigation }) {
  const item = route.params?.item;
  const [form, setForm] = useState({ title: item?.title || '', description: item?.description || '', price_kes: item?.price_kes || '', thumbnail_url: item?.thumbnail_url || '' });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [rate, setRate] = useState('');
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  useEffect(() => { let active = true; api.get('/api/accounts/credit-rate/', { authenticated: false }).then((result) => { if (active) setRate(result.credit_to_kes_rate); }).catch(() => {}); return () => { active = false; }; }, []);
  async function chooseFile() { setError(''); try { const result = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'video/mp4', 'video/webm', 'video/quicktime'], copyToCacheDirectory: true }); if (!result.canceled) setFile(result.assets[0]); } catch (failure) { setError(getApiErrorMessage(null, failure.message)); } }
  async function submit() {
    setBusy(true); setError(''); setMessage('');
    try {
      if (item) {
        const response = await api.patch(API_PATHS.contentUpdate(item.id), { title: form.title, description: form.description, price_kes: form.price_kes, thumbnail_url: form.thumbnail_url });
        setMessage(response.message || 'Changes saved by the server.');
      } else {
        if (!file) throw new Error('Choose a PDF or video before uploading.');
        const body = new FormData();
        Object.entries({ title: form.title, description: form.description, content_type: file.mimeType?.startsWith('video/') ? 'video' : 'pdf', price_kes: form.price_kes, thumbnail_url: form.thumbnail_url }).forEach(([key, value]) => { if (value) body.append(key, value); });
        body.append('file', { uri: file.uri, name: file.name, type: file.mimeType || 'application/octet-stream' });
        const response = await api.post(API_PATHS.contentCreate, body);
        setMessage(response.message || 'Upload confirmed by the server.');
      }
      navigation.navigate('CreatorContent');
    } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(false); }
  }
  return <Screen scroll><KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.page}><PageHeading eyebrow="Creator studio" title={item ? 'Edit resource' : 'Upload a resource'} description={item ? 'Update details supported by the content API.' : 'Upload a PDF guide or supported video. New content is saved as a draft.'}/>
    {['title', 'description', 'price_kes', 'thumbnail_url'].map((key) => <View key={key} style={styles.field}><Text style={styles.label}>{({ title: 'Title', description: 'Description', price_kes: 'Content price in KES', thumbnail_url: 'Thumbnail URL (optional)' })[key]}</Text><TextInput value={form[key]} onChangeText={(value) => update(key, value)} multiline={key === 'description'} keyboardType={key === 'price_kes' ? 'decimal-pad' : 'default'} autoCapitalize={key === 'thumbnail_url' ? 'none' : 'sentences'} style={[styles.input, key === 'description' && styles.multiline]} accessibilityLabel={key}/>{key === 'price_kes' ? <Text style={styles.hint}>At 1 credit = KES {rate || '…'}, current equivalent: {estimateCredits(form.price_kes, rate) || '—'} credits.</Text> : null}</View>)}
    {!item && <><AppButton title={file ? `Selected: ${file.name}` : 'Choose PDF or video'} secondary onPress={chooseFile}/><Text style={styles.hint}>Supported: PDF, MP4, WebM, and QuickTime. The server enforces file size and format limits.</Text></>}
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}{message ? <Text accessibilityRole="status" style={styles.message}>{message}</Text> : null}
    <View style={{ height: 14 }}/><AppButton title={busy ? item ? 'Saving...' : 'Uploading...' : item ? 'Save changes' : 'Upload as draft'} onPress={submit} disabled={busy || !form.title || !form.description || !form.price_kes || (!item && !file)}/>{busy ? <ActivityIndicator style={{ margin: 12 }} color="#FF0000"/> : null}
  </KeyboardAvoidingView></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, field: { marginBottom: 14 }, label: { color: '#000000', fontWeight: '700', marginBottom: 7 }, input: { minHeight: 48, borderWidth: 1, borderColor: '#B8B8B8', borderRadius: 9, padding: 12, color: '#000000', fontSize: 16 }, multiline: { minHeight: 110, textAlignVertical: 'top' }, hint: { color: '#595959', lineHeight: 20, marginTop: 8 }, error: { color: '#B00000', marginTop: 12, lineHeight: 21 }, message: { color: '#000000', marginTop: 12 } });
