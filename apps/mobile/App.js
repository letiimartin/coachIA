import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Home, List, Calendar, User } from 'lucide-react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as Linking from 'expo-linking';
import { supabase } from './src/lib/supabase';

// Screens
import AuthScreen from './src/screens/AuthScreen';
// Pantallas nuevas (TypeScript) contra la API de CoachIA (#18).
import AthleteProfileScreen from './src/screens/athlete/AthleteProfileScreen';
import ThresholdsScreen from './src/screens/athlete/ThresholdsScreen';
import ThresholdFormScreen from './src/screens/athlete/ThresholdFormScreen';
import AvailabilityScreen from './src/screens/athlete/AvailabilityScreen';
import EventsScreen from './src/screens/calendar/EventsScreen';
import EventFormScreen from './src/screens/calendar/EventFormScreen';
import DashboardScreen from './src/screens/home/DashboardScreen';
import WorkoutsScreen from './src/screens/workouts/WorkoutsScreen';
import CoachChatScreen from './src/screens/coach/CoachChatScreen';
import IntegrationsScreen from './src/screens/integrations/IntegrationsScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

const linking = {
  prefixes: [
    Linking.createURL('/'),
    'letismartcoach://',
    ...(process.env.EXPO_PUBLIC_WEB_URL ? [process.env.EXPO_PUBLIC_WEB_URL] : []),
  ],
  config: {
    screens: {
      MainTabs: {
        screens: {
          Home: 'home',
          Entrenos: 'workouts',
          Calendario: 'calendar',
          Perfil: 'profile',
        },
      },
      Thresholds: 'profile/thresholds',
      Availability: 'profile/availability',
      CoachChat: 'chat',
      // Vuelta del OAuth de Wahoo (APP_RETURN_URL_* en la API): ?provider=wahoo&status=…&reason=…
      Integrations: 'integrations',
    },
  },
};

function TabNavigator({ onLogout }) {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0a0a0c',
          borderTopColor: 'rgba(255,255,255,0.1)',
          height: 64,
          paddingBottom: 8,
        },
        tabBarActiveTintColor: '#00f2ff',
        tabBarInactiveTintColor: '#909090',
        tabBarIcon: ({ color, size }) => {
          if (route.name === 'Home') return <Home size={size} color={color} />;
          if (route.name === 'Entrenos') return <List size={size} color={color} />;
          if (route.name === 'Calendario') return <Calendar size={size} color={color} />;
          if (route.name === 'Perfil') return <User size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Home" component={DashboardScreen} />
      <Tab.Screen name="Entrenos" component={WorkoutsScreen} />
      <Tab.Screen name="Calendario" component={EventsScreen} />
      <Tab.Screen name="Perfil">
        {(props) => <AthleteProfileScreen {...props} onLogout={onLogout} />}
      </Tab.Screen>
    </Tab.Navigator>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: '#0a0a0c', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color="#00f2ff" />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer
          theme={{
            ...DarkTheme,
            colors: {
              ...DarkTheme.colors,
              background: '#0a0a0c',
              primary: '#00f2ff',
              card: '#0a0a0c',
              border: 'rgba(255,255,255,0.1)',
              text: '#e0e0e0',
            }
          }}
          linking={linking}
        >
          {session ? (
            <Stack.Navigator screenOptions={{ headerShown: false }}>
              <Stack.Screen name="MainTabs">
                {(props) => <TabNavigator {...props} onLogout={() => supabase.auth.signOut()} />}
              </Stack.Screen>
              <Stack.Screen name="Thresholds" component={ThresholdsScreen} />
              <Stack.Screen name="ThresholdForm" component={ThresholdFormScreen} />
              <Stack.Screen name="Availability" component={AvailabilityScreen} />
              <Stack.Screen name="EventForm" component={EventFormScreen} />
              <Stack.Screen name="CoachChat" component={CoachChatScreen} />
              <Stack.Screen name="Integrations" component={IntegrationsScreen} />
            </Stack.Navigator>
          ) : (
            <AuthScreen onLogin={() => { }} />
          )}
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
