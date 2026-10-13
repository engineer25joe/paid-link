import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';
import { Brand } from '../components/Brand';

export function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState(''); const [password, setPassword] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function submit() { setBusy(true); setError(''); try { await login({ username: username.trim(), password }); } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } finally { setBusy(false); } }
  return <Screen><KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.page}><Brand compact/><View style={{ height: 18 }}/><PageHeading eyebrow="Welcome back" title="Log in" description="Sign in to continue learning."/>
    <Text style={styles.label}>Username</Text><TextInput style={styles.input} value={username} onChangeText={setUsername} autoCapitalize="none" autoComplete="username" returnKeyType="next"/>
    <Text style={styles.label}>Password</Text><TextInput style={styles.input} value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" onSubmitEditing={submit}/>
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}<View style={styles.button}><AppButton title={busy ? 'Logging in...' : 'Log in'} onPress={submit} disabled={busy || !username.trim() || !password}/></View>
  </KeyboardAvoidingView></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1, justifyContent: 'center' }, label: { color: '#000000', fontSize: 14, fontWeight: '700', marginBottom: 7, marginTop: 14 }, input: { minHeight: 50, borderColor: '#B8B8B8', borderWidth: 1, borderRadius: 9, backgroundColor: '#FFFFFF', paddingHorizontal: 13, fontSize: 16, color: '#000000' }, button: { marginTop: 24 }, error: { color: '#B00000', marginTop: 14, lineHeight: 21 } });
