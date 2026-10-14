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
const Stack = createNativeStackNavigator();
export function AppNavigator() { const { user } = useAuth(); return <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#FFFFFF' }, animation: 'fade' }}>{user ? <Stack.Group><Stack.Screen name="Workspace" component={WorkspaceScreen} /><Stack.Screen name="Explore" component={ExploreScreen} /><Stack.Screen name="ContentDetail" component={ContentDetailScreen} /><Stack.Screen name="MyPurchases" component={MyPurchasesScreen} />{user.role === 'creator' && <><Stack.Screen name="CreatorContent" component={CreatorContentScreen} /><Stack.Screen name="CreatorEditor" component={CreatorEditorScreen} /><Stack.Screen name="CreatorEarnings" component={CreatorEarningsScreen} /></>}{user.role === 'admin' && <><Stack.Screen name="AdminDashboard" component={AdminDashboardScreen} /><Stack.Screen name="AdminRecords" component={AdminRecordsScreen} /></>}</Stack.Group> : <Stack.Group><Stack.Screen name="Home" component={HomeScreen} /><Stack.Screen name="Explore" component={ExploreScreen} /><Stack.Screen name="ContentDetail" component={ContentDetailScreen} /><Stack.Screen name="Login" component={LoginScreen} /><Stack.Screen name="Register" component={RegisterScreen} /></Stack.Group>}</Stack.Navigator>; }
