import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';
import { Brand } from '../components/Brand';
import { Text, TextInput, View } from 'react-native';
import { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { createIdempotencyKey } from '../api/idempotency';

export function WorkspaceScreen({ navigation }) {
  const { user, logout, refreshProfile } = useAuth();
  const [amount, setAmount] = useState(''); const [phone, setPhone] = useState(user?.phone_number || '');
  const [wallet, setWallet] = useState({ transactions: [], payments: [] }); const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [notice, setNotice] = useState('');
  const [requestKey, setRequestKey] = useState('');
  const [conversionRate, setConversionRate] = useState('');
  const [application, setApplication] = useState(null); const [motivation, setMotivation] = useState('');
  useFocusEffect(useCallback(() => { let active = true; api.get(API_PATHS.walletTransactions).then((value) => { if (active) setWallet(value); }).catch((error) => { if (active) setLoadError(getApiErrorMessage(error.data, error.message)); }); api.get(API_PATHS.creditRate, { authenticated: false }).then((value) => { if (active) setConversionRate(value.credit_to_kes_rate); }).catch(() => {}); if (user?.role === 'learner') api.get(API_PATHS.creatorApplications).then((value) => { if (active) setApplication(value.application); }).catch(() => {}); return () => { active = false; }; }, [user?.role]));
  async function topUp() { setBusy(true); setLoadError(''); setNotice(''); try { const key = requestKey || createIdempotencyKey(); setRequestKey(key); const result = await api.post(API_PATHS.initiateTopup, { amount, phone_number: phone, idempotency_key: key }); setNotice(`Provider status: ${result.status}. Credits are added after provider confirmation.`); setWallet(await api.get(API_PATHS.walletTransactions)); if (result.status === 'completed') await refreshProfile(); if (result.status !== 'outcome_unknown') setRequestKey(''); } catch (error) { setLoadError(getApiErrorMessage(error.data, error.message)); } finally { setBusy(false); } }
  async function refreshWallet() { setBusy(true); setLoadError(''); try { const updated = await api.get(API_PATHS.walletTransactions); const verified = updated.payments?.some((payment) => payment.status === 'completed' && !wallet.payments?.some((old) => old.id === payment.id && old.status === 'completed')); setWallet(updated); if (verified) await refreshProfile(); } catch (error) { setLoadError(getApiErrorMessage(error.data, error.message)); } finally { setBusy(false); } }
  async function applyCreator() { setBusy(true); setLoadError(''); try { const result = await api.post(API_PATHS.creatorApplications, { motivation }); setApplication(result.application); } catch (error) { setLoadError(getApiErrorMessage(error.data, error.message)); } finally { setBusy(false); } }
  const role = user?.role;
  const isCreator = role === 'creator';
  return <Screen scroll><View style={{ paddingTop: 12 }}><Brand compact/><View style={{ height: 16 }}/><PageHeading eyebrow={role || 'Learner'} title={`Welcome, ${user?.username || 'learner'}`} description={isCreator ? 'Manage your learning resources and follow sales reported by the ElimuBang API.' : 'Explore practical resources and use your credits for learning.'}/>
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}><Text style={{ color: '#595959', flex: 1 }}>Credit balance: <Text style={{ color: '#000000', fontWeight: '700' }}>{user?.credits ?? '—'}</Text></Text><AppButton title="Top Up Credits" secondary onPress={() => navigation.navigate('Wallet')}/></View><Text style={{ color: '#595959', marginBottom: 16 }}>Conversion rate: 1 credit = KES {conversionRate || '…'}</Text>
    <Text style={{ color: '#000000', fontWeight: '700', marginBottom: 8 }}>Top up credits</Text>
    <TextInput accessibilityLabel="Top-up amount in Kenyan shillings" placeholder="Amount in KES" keyboardType="number-pad" value={amount} onChangeText={(value) => { setAmount(value); setRequestKey(''); }} style={{ borderWidth: 1, borderColor: '#D8D8D8', borderRadius: 10, padding: 12, marginBottom: 8 }}/>
    <TextInput accessibilityLabel="M-Pesa phone number" placeholder="M-Pesa phone number" keyboardType="phone-pad" value={phone} onChangeText={(value) => { setPhone(value); setRequestKey(''); }} style={{ borderWidth: 1, borderColor: '#D8D8D8', borderRadius: 10, padding: 12, marginBottom: 8 }}/>
    <AppButton title={busy ? 'Starting payment…' : 'Top Up Credits'} disabled={busy || !amount || !phone} onPress={topUp}/>
    {loadError ? <Text accessibilityRole="alert" style={{ color: '#B00000', marginVertical: 8 }}>{loadError}</Text> : null}
    {notice ? <Text accessibilityRole="status" style={{ color: '#595959', marginVertical: 8 }}>{notice}</Text> : null}
    <Text style={{ color: '#595959', marginVertical: 8 }}>Wallet activity: {wallet.payments?.length || 0} top-ups, {wallet.transactions?.length || 0} credit entries.</Text>
    {[...(wallet.payments || []).map((row) => ({ ...row, label: 'Top-up' })), ...(wallet.transactions || []).map((row) => ({ ...row, label: row.description || row.type }))].slice(0, 5).map((row) => <Text key={`${row.label}-${row.id}`} style={{ color: '#595959', marginBottom: 6 }}>{row.label}: {row.amount} credits · {row.status || `balance ${row.balance_after}`}</Text>)}
    <AppButton title="Refresh wallet status" secondary disabled={busy} onPress={refreshWallet}/>
    {role === 'learner' && <>{application ? <Text style={{ color: '#595959', marginVertical: 8 }}>Creator application status: {application.status}</Text> : <><Text style={{ color: '#000000', fontWeight: '700', marginVertical: 8 }}>Apply to become a creator</Text><TextInput accessibilityLabel="Creator application motivation" placeholder="Describe the learning content you plan to create" multiline maxLength={2000} value={motivation} onChangeText={setMotivation} style={{ minHeight: 80, borderWidth: 1, borderColor: '#D8D8D8', borderRadius: 10, padding: 12, marginBottom: 8 }}/><AppButton title="Submit creator application" disabled={busy || !motivation.trim()} onPress={applyCreator}/></>}</>}
    <AppButton title="Browse learning resources" onPress={() => navigation.navigate('Explore')}/>
    <View style={{ height: 10 }}/><AppButton title="My purchases" secondary onPress={() => navigation.navigate('MyPurchases')}/>
    {isCreator && <><View style={{ height: 12 }}/><AppButton title="Manage my content" secondary onPress={() => navigation.navigate('CreatorContent')}/><View style={{ height: 12 }}/><AppButton title="Creator earnings" secondary onPress={() => navigation.navigate('CreatorEarnings')}/></>}
    {role === 'admin' && <><View style={{ height: 12 }}/><AppButton title="Administrator dashboard" secondary onPress={() => navigation.navigate('AdminDashboard')}/></>}
    <View style={{ height: 12 }}/><AppButton title="Log out" secondary onPress={logout}/><MobileTabBar navigation={navigation} role={role} active={role === 'admin' ? 'AdminDashboard' : 'Workspace'}/>
  </View></Screen>;
}
