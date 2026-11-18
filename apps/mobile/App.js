import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator, Text, useWindowDimensions } from 'react-native';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';
// Sólo los dos pesos del sistema (importar el índice del paquete empaquetaría los ocho).
import { Arimo_400Regular } from '@expo-google-fonts/arimo/400Regular';
import { Arimo_700Bold } from '@expo-google-fonts/arimo/700Bold';
import * as Linking from 'expo-linking';
import { supabase } from './src/lib/supabase';
import { Icon } from './src/ui/Icon';
import { colors, fonts, isWeb, layout, lines, radius, spacing, typography } from './src/ui/theme';

// Screens
import AuthScreen from './src/screens/AuthScreen';
// Pantallas (TypeScript) contra la API de CoachIA (#18).
import AthleteProfileScreen from './src/screens/athlete/AthleteProfileScreen';
import ThresholdsScreen from './src/screens/athlete/ThresholdsScreen';
import ThresholdFormScreen from './src/screens/athlete/ThresholdFormScreen';
import AvailabilityScreen from './src/screens/athlete/AvailabilityScreen';
import EventsScreen from './src/screens/calendar/EventsScreen';
import EventFormScreen from './src/screens/calendar/EventFormScreen';
import DashboardScreen from './src/screens/home/DashboardScreen';
import PerformanceScreen from './src/screens/performance/PerformanceScreen';
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
          Hoy: 'today',
          Plan: 'plan',
          Coach: 'coach',
          Rendimiento: 'performance',
          Perfil: 'profile',
        },
      },
      Thresholds: 'profile/thresholds',
      Availability: 'profile/availability',
      // Vuelta del OAuth de Wahoo (APP_RETURN_URL_* en la API): ?provider=wahoo&status=…&reason=…
      Integrations: 'integrations',
    },
  },
};

/** Pestañas: nombre de ruta (y etiqueta) → icono semántico. */
const TAB_ICONS = {
  Hoy: 'today',
  Plan: 'plan',
  Coach: 'coach',
  Rendimiento: 'performance',
  Perfil: 'profile',
};

/** Tema de React Navigation a partir de los tokens (sólo modo claro). */
const navigationTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.background,
    primary: colors.textActive,
    card: colors.background,
    border: colors.separator,
    text: colors.text,
    notification: colors.accent,
  },
  fonts: {
    regular: { fontFamily: fonts.regular, fontWeight: '400' },
    medium: { fontFamily: fonts.regular, fontWeight: '400' },
    bold: { fontFamily: fonts.bold, fontWeight: '700' },
    heavy: { fontFamily: fonts.bold, fontWeight: '700' },
  },
};

function TabNavigator({ onLogout }) {
  const { width } = useWindowDimensions();
  // Web: barra inferior y columna centrada en pantallas estrechas; barra lateral en las anchas.
  const sidebar = isWeb && width >= layout.sidebarBreakpoint;
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarPosition: sidebar ? 'left' : 'bottom',
        tabBarLabelPosition: sidebar ? 'beside-icon' : 'below-icon',
        tabBarActiveTintColor: colors.textActive,
        tabBarInactiveTintColor: colors.textSecondary,
        // Sin fondo en la pestaña activa: la librería le pone esquinas de 10 px en la barra lateral.
        tabBarActiveBackgroundColor: 'transparent',
        tabBarStyle: sidebar
          ? {
              width: layout.sidebarWidth,
              backgroundColor: colors.background,
              borderRightColor: colors.separator,
              borderRightWidth: lines.hairline,
              paddingTop: spacing.xl,
              paddingHorizontal: spacing.sm,
            }
          : {
              backgroundColor: colors.background,
              borderTopColor: colors.separator,
              borderTopWidth: lines.hairline,
              elevation: 0,
              shadowOpacity: 0,
            },
        tabBarItemStyle: sidebar
          ? { justifyContent: 'flex-start', paddingHorizontal: spacing.md, marginBottom: spacing.xs, borderRadius: radius.sm }
          : { borderRadius: radius.none },
        tabBarLabel: ({ focused, color }) => (
          <Text
            style={[
              { fontSize: sidebar ? typography.body.fontSize : typography.caption.fontSize },
              { color, fontFamily: focused ? fonts.bold : fonts.regular },
              sidebar ? { marginLeft: spacing.md } : null,
            ]}
            numberOfLines={1}
          >
            {route.name}
          </Text>
        ),
        tabBarIcon: ({ color }) => <Icon name={TAB_ICONS[route.name]} size={sidebar ? 20 : 22} color={color} />,
      })}
    >
      <Tab.Screen name="Hoy" component={DashboardScreen} />
      <Tab.Screen name="Plan" component={EventsScreen} />
      <Tab.Screen name="Coach" component={CoachChatScreen} />
      <Tab.Screen name="Rendimiento" component={PerformanceScreen} />
      <Tab.Screen name="Perfil">
        {(props) => <AthleteProfileScreen {...props} onLogout={onLogout} />}
      </Tab.Screen>
    </Tab.Navigator>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  // Arimo se carga antes de mostrar la app; si falla, se sigue con la fuente del sistema.
  const [fontsLoaded, fontError] = useFonts({ Arimo_400Regular, Arimo_700Bold });

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

  if (loading || (!fontsLoaded && !fontError)) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.background, justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <NavigationContainer theme={navigationTheme} linking={linking}>
        {session ? (
          <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
            <Stack.Screen name="MainTabs">
              {(props) => <TabNavigator {...props} onLogout={() => supabase.auth.signOut()} />}
            </Stack.Screen>
            <Stack.Screen name="Thresholds" component={ThresholdsScreen} />
            <Stack.Screen name="ThresholdForm" component={ThresholdFormScreen} />
            <Stack.Screen name="Availability" component={AvailabilityScreen} />
            <Stack.Screen name="EventForm" component={EventFormScreen} />
            <Stack.Screen name="Integrations" component={IntegrationsScreen} />
          </Stack.Navigator>
        ) : (
          <AuthScreen onLogin={() => { }} />
        )}
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
