import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { Linking } from 'react-native';
import { AuthProvider, useAuth } from './src/auth/AuthContext';
import { LoadingScreen } from './src/components/Screen';
import { AppNavigator } from './src/navigation/AppNavigator';
import { createGuestLinking } from './src/navigation/guestLinks.mjs';
const Stack = createNativeStackNavigator();
const linking = createGuestLinking(
  () => Linking.getInitialURL(),
  (listener) => { const subscription = Linking.addEventListener('url', ({ url }) => listener(url)); return () => subscription.remove(); },
);
export default function App() { return <AuthProvider><StatusBar style="dark" /><NavigationContainer linking={linking}><RootNavigation /></NavigationContainer></AuthProvider>; }
function RootNavigation() { const { loading } = useAuth(); if (loading) return <LoadingScreen />; return <Stack.Navigator screenOptions={{ headerShown: false }}><Stack.Screen name="App" component={AppNavigator} /></Stack.Navigator>; }
