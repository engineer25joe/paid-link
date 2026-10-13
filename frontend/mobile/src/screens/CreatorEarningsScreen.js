import { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

export function CreatorEarningsScreen({ navigation }) {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [state, setState] = useState({ loading: true, error: '' });
  useFocusEffect(useCallback(() => { let active = true; setState({ loading: true, error: '' }); Promise.all([api.get(API_PATHS.creatorEarnings), api.get(API_PATHS.creatorContentEarnings)]).then(([stats, content]) => { if (active) { setSummary(stats); setRows(Array.isArray(content) ? content : []); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []));
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Creator studio" title="Earnings" description="Figures returned by the creator earnings API."/>
    {state.loading ? <ActivityIndicator color="#FF0000"/> : null}{state.error ? <Text accessibilityRole="alert" style={styles.error}>{state.error}</Text> : null}
    {summary && <><View style={styles.grid}>{[['Sales', summary.total_sales_count], ['Gross earnings', `${summary.gross_earnings} credits`], ['Available credits', summary.available_credit_balance], ['Published resources', summary.published_contents_count]].map(([label, value]) => <View key={label} style={styles.metric}><Text style={styles.label}>{label}</Text><Text style={styles.value}>{value ?? '—'}</Text></View>)}</View>
      <Text style={styles.section}>Sales by resource</Text>{rows.length ? rows.map((row) => <View key={row.content_id} style={styles.row}><Text style={styles.title}>{row.title}</Text><Text style={styles.sub}>{row.purchase_count} purchases · {row.gross_sales} credits gross</Text></View>) : <Text style={styles.sub}>No content earnings are available yet.</Text>}
      <Text style={styles.note}>Sales and balances are shown only from the server. Payout requests are not available in this mobile app.</Text></>}
    <MobileTabBar navigation={navigation} role={user?.role} active="CreatorEarnings"/>
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, grid: { gap: 10, marginBottom: 22 }, metric: { borderWidth: 1, borderColor: '#E5E5E5', borderRadius: 10, padding: 14 }, label: { color: '#595959', fontSize: 12 }, value: { color: '#000000', fontSize: 20, fontWeight: '700', marginTop: 6 }, section: { color: '#000000', fontWeight: '800', fontSize: 18, marginBottom: 8 }, row: { paddingVertical: 12, borderBottomWidth: 1, borderColor: '#E5E5E5' }, title: { color: '#000000', fontWeight: '700' }, sub: { color: '#595959', marginTop: 5 }, note: { color: '#595959', lineHeight: 20, marginVertical: 18 }, error: { color: '#B00000', marginVertical: 14 } });
