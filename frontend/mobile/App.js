import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider, useAuth } from './src/auth/AuthContext';
import { LoadingScreen } from './src/components/Screen';
import { AppNavigator } from './src/navigation/AppNavigator';
const Stack = createNativeStackNavigator();
const linking = { prefixes: ['paidlink://', 'https://paidlinkweb.onrender.com'], config: { screens: { App: { screens: { SharedContent: 'shared/:token', GuestAccess: 'guest-access/:token' } } } } };
export default function App() { return <AuthProvider><StatusBar style="dark" /><NavigationContainer linking={linking}><RootNavigation /></NavigationContainer></AuthProvider>; }
function RootNavigation() { const { loading } = useAuth(); if (loading) return <LoadingScreen />; return <Stack.Navigator screenOptions={{ headerShown: false }}><Stack.Screen name="App" component={AppNavigator} /></Stack.Navigator>; }
