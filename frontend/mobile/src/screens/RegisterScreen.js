import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';
import { Brand } from '../components/Brand';

const fields = [{ key: 'username', label: 'Username', autoCapitalize: 'none' }, { key: 'email', label: 'Email', keyboardType: 'email-address', autoCapitalize: 'none' }, { key: 'phone_number', label: 'Phone number', keyboardType: 'phone-pad' }, { key: 'password', label: 'Password (at least 8 characters)', secureTextEntry: true, autoCapitalize: 'none' }];
export function RegisterScreen() {
  const { register } = useAuth();
  const [form, setForm] = useState({ username: '', email: '', phone_number: '', password: '' }); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function submit() { setBusy(true); setError(''); try { await register({ ...form, username: form.username.trim(), email: form.email.trim(), phone_number: form.phone_number.trim() }); } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } finally { setBusy(false); } }
  const valid = Object.values(form).every(Boolean) && form.password.length >= 8 && /.+@.+\..+/.test(form.email);
  return <Screen scroll><KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.page}><Brand compact/><View style={{ height: 18 }}/><PageHeading eyebrow="Join ElimuBang" title="Create account" description="New accounts start with learner access."/>
    {fields.map((field) => <View key={field.key} style={styles.field}><Text style={styles.label}>{field.label}</Text><TextInput style={styles.input} value={form[field.key]} onChangeText={(value) => setForm((current) => ({ ...current, [field.key]: value }))} autoCapitalize={field.autoCapitalize || 'sentences'} keyboardType={field.keyboardType || 'default'} secureTextEntry={field.secureTextEntry} autoComplete={field.key === 'phone_number' ? 'tel' : field.key}/></View>)}
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}<View style={styles.button}><AppButton title={busy ? 'Creating account...' : 'Create learner account'} onPress={submit} disabled={busy || !valid}/></View>
  </KeyboardAvoidingView></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1, justifyContent: 'center' }, field: { marginBottom: 11 }, label: { color: '#000000', fontSize: 13, fontWeight: '700', marginBottom: 7 }, input: { minHeight: 49, borderColor: '#B8B8B8', borderWidth: 1, borderRadius: 9, backgroundColor: '#FFFFFF', paddingHorizontal: 12, fontSize: 16, color: '#000000' }, button: { marginTop: 14 }, error: { color: '#B00000', marginTop: 10, lineHeight: 21 } });
