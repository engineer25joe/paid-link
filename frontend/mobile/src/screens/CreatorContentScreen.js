import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

export function CreatorContentScreen({ navigation }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [state, setState] = useState({ loading: true, error: '' });
  const [busyId, setBusyId] = useState(null);
  const load = useCallback(() => { let active = true; setState({ loading: true, error: '' }); api.get(API_PATHS.myContent).then((rows) => { if (!Array.isArray(rows)) throw new Error('The content service returned an unsupported response.'); if (active) { setItems(rows); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []);
  useFocusEffect(load);
  async function toggle(item) { setBusyId(item.id); setState((current) => ({ ...current, error: '' })); try { const response = await api.patch(API_PATHS.contentPublish(item.id), { is_published: !item.is_published }); setItems((rows) => rows.map((row) => row.id === item.id ? response.content : row)); } catch (error) { setState((current) => ({ ...current, error: getApiErrorMessage(error.data, error.message) })); } finally { setBusyId(null); } }
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Creator studio" title="My content" description="Create and manage your own uploaded learning resources."/><AppButton title="Create a resource" onPress={() => navigation.navigate('CreatorEditor')}/>
    {state.loading ? <ActivityIndicator style={{ margin: 20 }} color="#FF0000"/> : null}{state.error ? <Text accessibilityRole="alert" style={styles.error}>{state.error}</Text> : null}
    {!state.loading && !state.error && items.length === 0 ? <Text style={styles.muted}>You have not uploaded any resources yet.</Text> : null}
    {items.map((item) => <View key={item.id} style={styles.card}><Text style={styles.title}>{item.title}</Text><Text style={styles.meta}>{item.content_type?.toUpperCase()} · {item.price} credits · {item.is_published ? 'Published' : 'Draft'}</Text><View style={styles.actions}><Pressable accessibilityRole="button" onPress={() => navigation.navigate('CreatorEditor', { item })} style={styles.link}><Text style={styles.linkText}>Edit</Text></Pressable><Pressable accessibilityRole="button" disabled={busyId === item.id} onPress={() => toggle(item)} style={styles.link}><Text style={styles.linkText}>{busyId === item.id ? 'Saving...' : item.is_published ? 'Unpublish' : 'Publish'}</Text></Pressable></View></View>)}
    <MobileTabBar navigation={navigation} role={user?.role} active="CreatorContent"/>
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, card: { padding: 16, borderWidth: 1, borderColor: '#E5E5E5', borderRadius: 12, marginTop: 12 }, title: { color: '#000000', fontSize: 18, fontWeight: '700' }, meta: { color: '#595959', marginTop: 7 }, actions: { flexDirection: 'row', gap: 22, marginTop: 14 }, link: { minHeight: 42, justifyContent: 'center' }, linkText: { color: '#000000', fontWeight: '700', textDecorationLine: 'underline' }, muted: { color: '#595959', marginVertical: 16 }, error: { color: '#B00000', marginVertical: 14 } });
