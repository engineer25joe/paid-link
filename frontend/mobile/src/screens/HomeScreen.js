import { StyleSheet, Text, View } from 'react-native';
import { Brand } from '../components/Brand';
import { AppButton } from '../components/AppButton';
import { Screen } from '../components/Screen';

export function HomeScreen({ navigation }) {
  return <Screen><View style={styles.page}><Brand/><View style={styles.hero}><Text style={styles.title}>Learning for a brighter you.</Text><Text style={styles.copy}>Discover practical lessons and resources from people who care about what they teach.</Text><AppButton title="Explore ElimuBang" onPress={() => navigation.navigate('Explore')}/><View style={styles.gap}/><AppButton title="Log in" secondary onPress={() => navigation.navigate('Login')}/><AppButton title="Create a learner account" secondary onPress={() => navigation.navigate('Register')}/></View></View></Screen>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, hero: { flex: 1, justifyContent: 'center', gap: 12 }, title: { color: '#000000', fontSize: 36, lineHeight: 42, fontWeight: '800' }, copy: { color: '#595959', fontSize: 16, lineHeight: 24, marginBottom: 14 }, gap: { height: 4 } });
