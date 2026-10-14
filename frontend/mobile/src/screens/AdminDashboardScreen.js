import { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';

const lists = [['users', 'Users'], ['creators', 'Creators'], ['learners', 'Learners'], ['content', 'Content'], ['purchases', 'Purchases'], ['ledger', 'Credit ledger'], ['withdrawals', 'Withdrawals']];
export function AdminDashboardScreen({ navigation }) {
  const { user } = useAuth(); const [stats, setStats] = useState(null); const [state, setState] = useState({ loading: true, error: '' });
  useFocusEffect(useCallback(() => { let active = true; setState({ loading: true, error: '' }); api.get(API_PATHS.adminDashboard).then((result) => { if (active) { setStats(result); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []));
  return <Screen scroll><View style={styles.page}><PageHeading eyebrow="Protected administrator tools" title="Platform overview" description="Metrics and read-only lists from the admin API."/>
    {state.loading && <ActivityIndicator color="#FF0000"/>}{state.error ? <Text accessibilityRole="alert" style={styles.error}>{state.error}</Text> : null}
    {stats && <View style={styles.metrics}>{[['Users', stats.total_users], ['Learners', stats.learners], ['Creators', stats.creators], ['Published resources', stats.published_content], ['Purchases', stats.total_purchases], ['Pending withdrawals', stats.pending_withdrawals], ['Unresolved payments', stats.unresolved_payment_records]].map(([label, value]) => <View key={label} style={styles.metric}><Text style={styles.label}>{label}</Text><Text style={styles.value}>{value ?? '—'}</Text></View>)}</View>}
    {lists.map(([section, title]) => <View key={section} style={styles.button}><AppButton title={`View ${title}`} secondary onPress={() => navigation.navigate('AdminRecords', { section })}/></View>)}
    <View style={styles.button}><AppButton title="Wallet adjustments" secondary onPress={() => navigation.navigate('AdminWallet')}/></View><View style={styles.button}><AppButton title="Credit conversion settings" secondary onPress={() => navigation.navigate('AdminSettings')}/></View><View style={styles.button}><AppButton title="Share management" secondary onPress={() => navigation.navigate('ShareManagement')}/></View>
    <MobileTabBar navigation={navigation} role={user?.role} active="AdminDashboard"/>
  </View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, metrics: { gap: 9, marginBottom: 18 }, metric: { padding: 13, borderWidth: 1, borderColor: '#E5E5E5', borderRadius: 10 }, label: { color: '#595959', fontSize: 12 }, value: { color: '#000000', fontWeight: '800', fontSize: 20, marginTop: 5 }, button: { marginVertical: 5 }, error: { color: '#B00000', marginVertical: 14 } });
