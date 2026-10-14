import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

export function MyPurchasesScreen({ navigation }) {
  const { user } = useAuth(); const [items, setItems] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  useFocusEffect(useCallback(() => { let active = true; setLoading(true); api.get(API_PATHS.myPurchases).then((rows) => { if (active) setItems(rows); }).catch((failure) => { if (active) setError(getApiErrorMessage(failure.data, failure.message)); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, []));
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="My Library" title="Purchased resources" description="Open a resource to request secure access from ElimuBang."/>
    {loading ? <ActivityIndicator color="#FF0000"/> : null}{error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    {!loading && !error && items.length === 0 ? <Text style={styles.muted}>No purchases yet. Browse the catalogue to find a resource for your studies.</Text> : null}
    {items.map((row) => <Pressable accessibilityRole="button" key={row.id} style={styles.card} onPress={() => navigation.navigate('ContentDetail', { item: { id: row.content_id, title: row.title, description: row.description, content_type: row.content_type, price: row.price } })}><Text style={styles.title}>{row.title}</Text><Text style={styles.muted}>{row.content_type?.toUpperCase()} · {row.amount_paid} credits · {new Date(row.purchased_at).toLocaleDateString()}</Text><Text style={styles.link}>Open purchased resource</Text></Pressable>)}
    <MobileTabBar navigation={navigation} role={user?.role} active="MyPurchases"/>
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, card: { borderWidth: 1, borderColor: '#E5E5E5', borderRadius: 12, padding: 16, marginBottom: 12 }, title: { color: '#000000', fontSize: 17, fontWeight: '700', marginBottom: 6 }, muted: { color: '#595959', lineHeight: 22 }, link: { color: '#000000', fontWeight: '700', textDecorationLine: 'underline', marginTop: 10 }, error: { color: '#B00000', marginVertical: 14 } });
