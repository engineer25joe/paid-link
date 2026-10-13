import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { MobileTabBar } from '../components/MobileTabBar';
import { PageHeading, Screen } from '../components/Screen';
import { Brand } from '../components/Brand';
import { Text, View } from 'react-native';

export function WorkspaceScreen({ navigation }) {
  const { user, logout } = useAuth();
  const role = user?.role;
  const isCreator = role === 'creator';
  return <Screen><View style={{ flex: 1, paddingTop: 12 }}><Brand compact/><View style={{ height: 16 }}/><PageHeading eyebrow={role || 'Learner'} title={`Welcome, ${user?.username || 'learner'}`} description={isCreator ? 'Manage your learning resources and follow sales reported by the ElimuBang API.' : 'Explore practical resources and use your credits for learning.'}/>
    <Text style={{ color: '#595959', marginBottom: 16 }}>Available credits: <Text style={{ color: '#000000', fontWeight: '700' }}>{user?.credits ?? '—'}</Text></Text>
    <AppButton title="Browse learning resources" onPress={() => navigation.navigate('Explore')}/>
    {isCreator && <><View style={{ height: 12 }}/><AppButton title="Manage my content" secondary onPress={() => navigation.navigate('CreatorContent')}/><View style={{ height: 12 }}/><AppButton title="Creator earnings" secondary onPress={() => navigation.navigate('CreatorEarnings')}/></>}
    {role === 'admin' && <><View style={{ height: 12 }}/><AppButton title="Administrator dashboard" secondary onPress={() => navigation.navigate('AdminDashboard')}/></>}
    <View style={{ height: 12 }}/><AppButton title="Log out" secondary onPress={logout}/><MobileTabBar navigation={navigation} role={role} active={role === 'admin' ? 'AdminDashboard' : 'Workspace'}/>
  </View></Screen>;
}
