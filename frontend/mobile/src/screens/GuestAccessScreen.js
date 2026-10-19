import { useEffect, useState } from 'react';
import { Linking, StyleSheet, Text, View } from 'react-native';
import { getGuestContent } from '../api/guestShares';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

function remaining(expiresAt) { const n = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000)); return `${String(Math.floor(n / 3600)).padStart(2, '0')}:${String(Math.floor((n % 3600) / 60)).padStart(2, '0')}:${String(n % 60).padStart(2, '0')}`; }
export function GuestAccessScreen({ route }) {
  const token = route.params?.token; const [data, setData] = useState(null); const [error, setError] = useState(''); const [networkError, setNetworkError] = useState(false); const [, tick] = useState(0);
  const load = () => { setError(''); setNetworkError(false); if (!token) { setError('This guest access link is invalid.'); return; } getGuestContent(token).then(setData).catch((failure) => { setNetworkError(!failure.status || failure.status >= 500); setError(failure.status ? getApiErrorMessage(failure.data, failure.message) : 'Guest access could not be checked. Check your connection and retry.'); }); };
  useEffect(() => { let active = true; if (token) getGuestContent(token).then((result) => { if (active) setData(result); }).catch((failure) => { if (active) { setNetworkError(!failure.status || failure.status >= 500); setError(failure.status ? getApiErrorMessage(failure.data, failure.message) : 'Guest access could not be checked. Check your connection and retry.'); } }); else setError('This guest access link is invalid.'); const timer = setInterval(() => tick((n) => n + 1), 1000); return () => { active = false; clearInterval(timer); }; }, [token]);
  if (!data) return <Screen><PageHeading eyebrow="Guest access" title={networkError ? 'Unable to verify access' : error ? 'Guest access unavailable' : 'Verifying temporary access'} description={error || 'Checking this access with ElimuBang…'}/>{networkError ? <AppButton title="Retry" secondary onPress={load}/> : null}</Screen>;
  if (remaining(data.expires_at) === '00:00:00') return <Screen><PageHeading eyebrow="Guest access" title="This link has expired" description="The backend no longer allows access to this resource."/></Screen>;
  const open = () => Linking.openURL(data.content.file_url).catch(() => setError('Could not open the protected resource on this device.'));
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Temporary guest access" title={data.content.title} description={data.content.description}/><Text style={styles.timer}>Access expires in {remaining(data.expires_at)}</Text>
    <AppButton title="View Content" onPress={open}/>{data.content.content_type === 'pdf' ? <View style={{ marginTop: 10 }}><AppButton title="Download PDF" secondary onPress={open}/></View> : <Text style={styles.muted}>Video is available through the authorized streaming link. Download is not enabled.</Text>}{error ? <Text style={styles.error}>{error}</Text> : null}
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, timer: { color: '#B00000', fontSize: 22, fontWeight: '800', marginBottom: 20 }, muted: { color: '#595959', lineHeight: 22, marginVertical: 14 }, error: { color: '#B00000', marginVertical: 12 } });
