import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { API_PATHS } from '../api/config';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errors';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

export function ExploreScreen({ navigation }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [format, setFormat] = useState('all');
  const [status, setStatus] = useState({ loading: true, error: '' });
  useEffect(() => {
    let active = true;
    api.get(API_PATHS.content, { authenticated: false }).then((result) => {
      if (!Array.isArray(result)) throw new Error('The catalogue returned an unsupported response.');
      if (active) { setItems(result); setStatus({ loading: false, error: '' }); }
    }).catch((error) => { if (active) setStatus({ loading: false, error: getApiErrorMessage(error.data, error.message) }); });
    return () => { active = false; };
  }, []);
  const filtered = useMemo(() => items.filter((item) => `${item.title} ${item.description} ${item.creator_username}`.toLowerCase().includes(search.trim().toLowerCase()) && (format === 'all' || item.content_type === format)), [items, search, format]);
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Explore ElimuBang" title="Learning resources" description="Search published lessons and guides."/>
    <TextInput accessibilityLabel="Search resources" placeholder="Search title, topic, or creator" value={search} onChangeText={setSearch} style={styles.search}/>
    <View style={styles.filters}>{[['all', 'All'], ['pdf', 'PDF'], ['video', 'Video']].map(([value, label]) => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: format === value }} onPress={() => setFormat(value)} style={[styles.filter, format === value && styles.filterActive]}><Text style={[styles.filterText, format === value && styles.filterTextActive]}>{label}</Text></Pressable>)}</View>
    {status.loading && <ActivityIndicator accessibilityLabel="Loading resources" color="#FF0000"/>}
    {status.error ? <Text accessibilityRole="alert" style={styles.error}>Could not load resources: {status.error}</Text> : null}
    {!status.loading && !status.error && filtered.length === 0 && <Text style={styles.muted}>{items.length ? 'No resources match your search.' : 'No resources have been published yet.'}</Text>}
    {filtered.map((item) => <Pressable key={item.id} accessibilityRole="button" onPress={() => navigation.navigate('ContentDetail', { item })} style={styles.card}><Text style={styles.meta}>{item.content_type?.toUpperCase()}  ·  {item.creator_username}</Text><Text style={styles.title}>{item.title}</Text><Text style={styles.description} numberOfLines={3}>{item.description}</Text><Text style={styles.price}>{item.price} credits  ·  View details</Text></Pressable>)}
    {user ? <MobileTabBar navigation={navigation} role={user.role} active="Explore"/> : null}
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, search: { minHeight: 48, borderWidth: 1, borderColor: '#B8B8B8', borderRadius: 10, paddingHorizontal: 14, fontSize: 16, color: '#000000', marginBottom: 12 }, filters: { flexDirection: 'row', gap: 8, marginBottom: 16 }, filter: { borderWidth: 1, borderColor: '#000000', borderRadius: 22, paddingVertical: 9, paddingHorizontal: 16, minHeight: 40 }, filterActive: { backgroundColor: '#FF0000', borderColor: '#FF0000' }, filterText: { color: '#000000', fontWeight: '600' }, filterTextActive: { color: '#FFFFFF' }, card: { borderWidth: 1, borderColor: '#E5E5E5', backgroundColor: '#FFFFFF', borderRadius: 12, padding: 16, marginVertical: 6 }, meta: { color: '#595959', fontSize: 11, fontWeight: '700' }, title: { color: '#000000', fontSize: 19, fontWeight: '700', marginVertical: 8 }, description: { color: '#595959', lineHeight: 21 }, price: { color: '#000000', marginTop: 12, fontWeight: '700' }, muted: { color: '#595959', marginVertical: 16 }, error: { color: '#B00000', marginVertical: 14, lineHeight: 21 } });
