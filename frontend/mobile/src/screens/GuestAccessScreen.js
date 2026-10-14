import { useEffect, useState } from 'react';
import { Linking, StyleSheet, Text, View } from 'react-native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

function remaining(expiresAt) { const n = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000)); return `${String(Math.floor(n / 3600)).padStart(2, '0')}:${String(Math.floor((n % 3600) / 60)).padStart(2, '0')}:${String(n % 60).padStart(2, '0')}`; }
export function GuestAccessScreen({ route }) {
  const { token } = route.params || {}; const [data, setData] = useState(null); const [error, setError] = useState(''); const [, tick] = useState(0);
  useEffect(() => { let active = true; api.get(API_PATHS.guestContent(token), { authenticated: false }).then((result) => { if (active) setData(result); }).catch((failure) => { if (active) setError(getApiErrorMessage(failure.data, failure.message)); }); const timer = setInterval(() => tick((n) => n + 1), 1000); return () => { active = false; clearInterval(timer); }; }, [token]);
  if (!data) return <Screen><Text style={styles.error}>{error || 'Verifying temporary access…'}</Text></Screen>;
  if (remaining(data.expires_at) === '00:00:00') return <Screen><PageHeading eyebrow="Guest access" title="This link has expired" description="The backend no longer allows access to this resource."/></Screen>;
  const open = () => Linking.openURL(data.content.file_url).catch(() => setError('Could not open the protected resource on this device.'));
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Temporary guest access" title={data.content.title} description={data.content.description}/><Text style={styles.timer}>Access expires in {remaining(data.expires_at)}</Text>
    <AppButton title="View Content" onPress={open}/>{data.content.content_type === 'pdf' ? <View style={{ marginTop: 10 }}><AppButton title="Download PDF" secondary onPress={open}/></View> : <Text style={styles.muted}>Video is available through the authorized streaming link. Download is not enabled.</Text>}{error ? <Text style={styles.error}>{error}</Text> : null}
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, timer: { color: '#B00000', fontSize: 22, fontWeight: '800', marginBottom: 20 }, muted: { color: '#595959', lineHeight: 22, marginVertical: 14 }, error: { color: '#B00000', marginVertical: 12 } });
