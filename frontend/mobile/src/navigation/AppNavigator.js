import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../auth/AuthContext';
import { HomeScreen } from '../screens/HomeScreen';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { RoleHomeScreen } from '../screens/RoleHomeScreen';
const Stack = createNativeStackNavigator();
function RoleHome(props) { const { user } = useAuth(); return <RoleHomeScreen {...props} role={user?.role} />; }
export function AppNavigator() { const { user } = useAuth(); return <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#f7f8f5' }, animation: 'fade' }}>{user ? <Stack.Group><Stack.Screen name="RoleHome" component={RoleHome} /></Stack.Group> : <Stack.Group><Stack.Screen name="Home" component={HomeScreen} /><Stack.Screen name="Login" component={LoginScreen} /><Stack.Screen name="Register" component={RegisterScreen} /></Stack.Group>}</Stack.Navigator>; }
