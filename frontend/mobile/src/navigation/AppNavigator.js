import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../auth/AuthContext';
import { HomeScreen } from '../screens/HomeScreen';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { ExploreScreen } from '../screens/ExploreScreen';
import { WorkspaceScreen } from '../screens/WorkspaceScreen';
import { ContentDetailScreen } from '../screens/ContentDetailScreen';
import { CreatorContentScreen } from '../screens/CreatorContentScreen';
import { CreatorEditorScreen } from '../screens/CreatorEditorScreen';
import { CreatorEarningsScreen } from '../screens/CreatorEarningsScreen';
import { AdminDashboardScreen } from '../screens/AdminDashboardScreen';
import { AdminRecordsScreen } from '../screens/AdminRecordsScreen';
import { MyPurchasesScreen } from '../screens/MyPurchasesScreen';
import { WalletScreen } from '../screens/WalletScreen';
import { ShareManagementScreen } from '../screens/ShareManagementScreen';
import { AdminWalletScreen } from '../screens/AdminWalletScreen';
import { AdminSettingsScreen } from '../screens/AdminSettingsScreen';
import { SharedContentScreen } from '../screens/SharedContentScreen';
import { GuestAccessScreen } from '../screens/GuestAccessScreen';
const Stack = createNativeStackNavigator();
export function AppNavigator() { const { user } = useAuth(); return <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#FFFFFF' }, animation: 'fade' }}>
  <Stack.Screen name="SharedContent" component={SharedContentScreen}/><Stack.Screen name="GuestAccess" component={GuestAccessScreen}/>
  {user ? <Stack.Group><Stack.Screen name="Workspace" component={WorkspaceScreen} /><Stack.Screen name="Explore" component={ExploreScreen} /><Stack.Screen name="ContentDetail" component={ContentDetailScreen} /><Stack.Screen name="MyPurchases" component={MyPurchasesScreen} /><Stack.Screen name="Wallet" component={WalletScreen}/>{user.role === 'creator' && <><Stack.Screen name="CreatorContent" component={CreatorContentScreen} /><Stack.Screen name="CreatorEditor" component={CreatorEditorScreen} /><Stack.Screen name="CreatorEarnings" component={CreatorEarningsScreen}/><Stack.Screen name="ShareManagement" component={ShareManagementScreen}/></>}{user.role === 'admin' && <><Stack.Screen name="AdminDashboard" component={AdminDashboardScreen} /><Stack.Screen name="AdminRecords" component={AdminRecordsScreen}/><Stack.Screen name="AdminWallet" component={AdminWalletScreen}/><Stack.Screen name="AdminSettings" component={AdminSettingsScreen}/><Stack.Screen name="ShareManagement" component={ShareManagementScreen}/></>}</Stack.Group> : <Stack.Group><Stack.Screen name="Home" component={HomeScreen} /><Stack.Screen name="Explore" component={ExploreScreen} /><Stack.Screen name="ContentDetail" component={ContentDetailScreen} /><Stack.Screen name="Login" component={LoginScreen} /><Stack.Screen name="Register" component={RegisterScreen} /></Stack.Group>}
</Stack.Navigator>; }
