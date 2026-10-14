import { Pressable, StyleSheet, Text, View } from 'react-native';

const learnerTabs = [['Workspace', 'Home'], ['Explore', 'Explore'], ['MyPurchases', 'Library']];
const creatorTabs = [['Workspace', 'Workspace'], ['CreatorContent', 'Content'], ['CreatorEarnings', 'Earnings'], ['MyPurchases', 'Library']];
const adminTabs = [['AdminDashboard', 'Admin'], ['Explore', 'Explore'], ['MyPurchases', 'Library']];
export function MobileTabBar({ navigation, role, active }) {
  const tabs = role === 'creator' ? creatorTabs : role === 'admin' ? adminTabs : learnerTabs;
  return <View style={styles.bar}>{tabs.map(([route, label]) => <Pressable key={route} accessibilityRole="button" accessibilityState={{ selected: active === route }} onPress={() => navigation.navigate(route)} style={styles.item}><Text style={[styles.label, active === route && styles.selected]}>{label}</Text></Pressable>)}</View>;
}
const styles = StyleSheet.create({ bar: { flexDirection: 'row', justifyContent: 'space-around', borderTopWidth: 1, borderColor: '#E5E5E5', paddingTop: 10, paddingBottom: 4, marginTop: 'auto' }, item: { minWidth: 72, minHeight: 44, alignItems: 'center', justifyContent: 'center' }, label: { color: '#595959', fontWeight: '600', fontSize: 12 }, selected: { color: '#FF0000' } });
