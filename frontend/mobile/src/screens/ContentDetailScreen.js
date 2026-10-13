import { useState } from 'react';
import { ActivityIndicator, Linking, StyleSheet, Text, View } from 'react-native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

export function ContentDetailScreen({ route, navigation }) {
  const { user, refreshProfile } = useAuth();
  const item = route.params?.item;
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [protectedUrl, setProtectedUrl] = useState('');
  async function run(action) {
    if (!user) { navigation.navigate('Login'); return; }
    setBusy(action); setError(''); setNotice(''); setProtectedUrl('');
    try {
      if (action === 'purchase') {
        const result = await api.post(API_PATHS.purchase(item.id), {});
        let balanceMessage = `Purchase confirmed by the server. Remaining balance: ${result.remaining_credits} credits.`;
        try { const profile = await refreshProfile(); balanceMessage = `Purchase confirmed by the server. Current balance: ${profile.credits} credits.`; } catch { /* The purchase response remains authoritative if profile refresh fails. */ }
        setNotice(balanceMessage);
      } else {
        const result = await api.get(API_PATHS.contentAccess(item.id));
        if (!result?.content?.file_url) throw new Error('The authorized resource link was not returned.');
        setProtectedUrl(result.content.file_url);
        setNotice('Access confirmed by the server.');
      }
    } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(''); }
  }
  if (!item) return <Screen><Text style={styles.error}>This resource is unavailable. Return to Explore and try again.</Text><AppButton title="Back to Explore" onPress={() => navigation.navigate('Explore')}/></Screen>;
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow={item.content_type?.toUpperCase() || 'Resource'} title={item.title} description={`By ${item.creator_username || 'ElimuBang creator'}`}/><Text style={styles.description}>{item.description}</Text><Text style={styles.price}>{item.price} credits</Text>
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}{notice ? <Text accessibilityRole="status" style={styles.notice}>{notice}</Text> : null}
    <AppButton title={busy === 'purchase' ? 'Processing...' : 'Purchase with credits'} onPress={() => run('purchase')} disabled={Boolean(busy)}/><View style={{ height: 10 }}/><AppButton title={busy === 'access' ? 'Checking access...' : 'Open purchased resource'} secondary onPress={() => run('access')} disabled={Boolean(busy)}/>
    {busy ? <ActivityIndicator style={{ margin: 12 }} color="#FF0000"/> : null}{protectedUrl ? <View style={styles.open}><AppButton title="Open authorized file" onPress={() => Linking.openURL(protectedUrl).catch(() => setError('Could not open the protected resource on this device.'))}/></View> : null}
    {user ? <MobileTabBar navigation={navigation} role={user.role} active="Explore"/> : null}
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, description: { color: '#595959', lineHeight: 24, fontSize: 15, marginBottom: 22 }, price: { color: '#000000', fontWeight: '800', fontSize: 20, marginBottom: 20 }, error: { color: '#B00000', lineHeight: 21, marginBottom: 14 }, notice: { color: '#000000', lineHeight: 21, marginBottom: 14, fontWeight: '600' }, open: { marginTop: 12 } });
