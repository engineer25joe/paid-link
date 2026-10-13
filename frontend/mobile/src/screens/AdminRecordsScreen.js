import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { ADMIN_LIST_ENDPOINTS } from '../api/config';
import { api } from '../api/client';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

const columns = { users: ['username', 'email', 'role', 'credits', 'is_active'], creators: ['username', 'email', 'credits'], learners: ['username', 'email', 'credits'], content: ['title', 'creator_username', 'content_type', 'price', 'is_published'], purchases: ['user_username', 'content_title', 'amount_paid', 'purchased_at'], ledger: ['user_username', 'transaction_type', 'amount', 'balance_after'], withdrawals: ['creator_username', 'amount', 'status', 'payout_status', 'phone_number'] };
const label = (field) => field.replaceAll('_', ' ');
const display = (value) => typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value == null || value === '' ? '—' : String(value);
export function AdminRecordsScreen({ route, navigation }) {
  const { user } = useAuth(); const section = route.params?.section; const endpoint = ADMIN_LIST_ENDPOINTS[section];
  const [page, setPage] = useState(1); const [data, setData] = useState({ count: 0, results: [], next: null, previous: null }); const [state, setState] = useState({ loading: true, error: '' });
  useFocusEffect(useCallback(() => { if (!endpoint) return undefined; let active = true; setState({ loading: true, error: '' }); api.get(`${endpoint}?page=${page}`).then((response) => { if (active) { setData(response); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, [endpoint, page]));
  const fields = columns[section] || [];
  return <Screen scroll><View style={styles.page}><Pressable accessibilityRole="button" onPress={() => navigation.navigate('AdminDashboard')} style={styles.back}><Text style={styles.backText}>‹  Admin overview</Text></Pressable><PageHeading eyebrow="Protected admin list" title={section ? section[0].toUpperCase() + section.slice(1) : 'Unavailable'} description={`${data.count} records reported by the admin API.`}/>
    {state.loading && <ActivityIndicator color="#FF0000"/>}{state.error ? <Text accessibilityRole="alert" style={styles.error}>{state.error}</Text> : null}
    {!state.loading && !state.error && data.results.length === 0 && <Text style={styles.empty}>No records to show.</Text>}
    {data.results.map((row) => <View key={row.id} style={styles.card}>{fields.map((field) => <View key={field} style={styles.field}><Text style={styles.label}>{label(field)}</Text><Text style={styles.value}>{display(row[field])}</Text></View>)}</View>)}
    <View style={styles.pager}><AppButton title="Previous" secondary disabled={!data.previous || state.loading} onPress={() => setPage((value) => Math.max(1, value - 1))}/><Text style={styles.pageText}>Page {page}</Text><AppButton title="Next" secondary disabled={!data.next || state.loading} onPress={() => setPage((value) => value + 1)}/></View>
    <MobileTabBar navigation={navigation} role={user?.role} active="AdminDashboard"/>
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, back: { minHeight: 42, justifyContent: 'center' }, backText: { color: '#000000', fontWeight: '700' }, card: { borderWidth: 1, borderColor: '#E5E5E5', borderRadius: 10, padding: 14, marginVertical: 6 }, field: { marginVertical: 4 }, label: { color: '#595959', textTransform: 'capitalize', fontSize: 11 }, value: { color: '#000000', marginTop: 2, fontWeight: '600' }, error: { color: '#B00000', marginVertical: 14 }, empty: { color: '#595959', marginVertical: 18 }, pager: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: 14 }, pageText: { color: '#000000', fontWeight: '600' } });
