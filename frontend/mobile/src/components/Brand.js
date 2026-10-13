import { Image, StyleSheet, Text, View } from 'react-native';

// The same supplied brand asset is used in the app UI and native shell assets.
export function Brand({ compact = false }) {
  return <View style={styles.row}><Image source={require('../../assets/brand.png')} resizeMode="contain" style={compact ? styles.compact : styles.logo} accessibilityLabel="Official ElimuBang logo"/><View><Text style={styles.name}>ElimuBang</Text>{!compact && <Text style={styles.slogan}>Quality Tuition for a Brighter You.</Text>}</View></View>;
}

const styles = StyleSheet.create({ row: { flexDirection: 'row', alignItems: 'center', gap: 12 }, logo: { width: 72, height: 72 }, compact: { width: 48, height: 48 }, name: { color: '#000000', fontSize: 20, fontWeight: '800' }, slogan: { color: '#000000', fontSize: 12, fontWeight: '600', marginTop: 3 } });
