import { View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';
const roleContent = { learner: ['Learner', 'Your learning space'], creator: ['Creator', 'Your creator space'], admin: ['Admin', 'Platform overview'] };
export function RoleHomeScreen({ role }) { const { logout } = useAuth(); const [eyebrow, title] = roleContent[role] || roleContent.learner; return <Screen><View style={{ flex: 1, justifyContent: 'center' }}><PageHeading eyebrow={eyebrow} title={title} description="This space is ready for the next stage of Paid Link."/><AppButton title="Sign out" secondary onPress={logout}/></View></Screen>; }
