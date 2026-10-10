import { Text, View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

const roleContent = {
  learner: ['Learner', 'Your learning space', 'Browse resources and keep track of your learning.'],
  creator: ['Creator', 'Your creator space', 'Creator tools and content management are coming soon.'],
  admin: ['Admin', 'Platform overview', 'Administrator tools are available in the web workspace.'],
};
export function RoleHomeScreen({ role, navigation }) {
  const { logout } = useAuth();
  const content = roleContent[role];
  if (!content) return <Screen><View style={{ flex: 1, justifyContent: 'center' }}><PageHeading eyebrow="Workspace unavailable" title="Role not recognized" description="Sign out and log in again to refresh your account role."/><AppButton title="Sign out" secondary onPress={logout}/></View></Screen>;
  const [eyebrow, title, description] = content;
  return <Screen><View style={{ flex: 1, justifyContent: 'center' }}><PageHeading eyebrow={eyebrow} title={title} description={description}/><AppButton title="Explore resources" onPress={() => navigation.navigate('Explore')}/><View style={{ height: 12 }}/><Text style={{ color: '#667274', marginVertical: 12 }}>My library is coming soon.</Text><AppButton title="Sign out" secondary onPress={logout}/></View></Screen>;
}
