import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import Svg, { Path, Rect, Circle } from 'react-native-svg';

import { AppProvider, useApp } from './src/context/AppContext';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import QuizScreen from './src/screens/QuizScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import LeaderboardScreen from './src/screens/LeaderboardScreen';
import ProfileScreen from './src/screens/ProfileScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function HomeIcon({ color }) {
  return <Svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round"><Path d="M3 12L12 3l9 9" /><Path d="M9 21V12h6v9" /></Svg>;
}
function BoardIcon({ color }) {
  return <Svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round"><Rect x="3" y="12" width="4" height="9" /><Rect x="10" y="7" width="4" height="14" /><Rect x="17" y="3" width="4" height="18" /></Svg>;
}
function PersonIcon({ color }) {
  return <Svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round"><Circle cx="12" cy="8" r="4" /><Path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" /></Svg>;
}

function TabLabel({ label, color }) {
  return <Text style={{ fontSize: 10, fontWeight: '800', color, marginTop: 2 }}>{label}</Text>;
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: 'white',
          borderTopWidth: 2,
          borderTopColor: '#F3F0FF',
          paddingBottom: 6,
          paddingTop: 6,
          height: 64,
        },
        tabBarActiveTintColor: '#7C5CBF',
        tabBarInactiveTintColor: '#C5B8E8',
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarIcon: ({ color }) => <HomeIcon color={color} />,
          tabBarLabel: ({ color }) => <TabLabel label="Home" color={color} />,
        }}
      />
      <Tab.Screen
        name="Leaderboard"
        component={LeaderboardScreen}
        options={{
          tabBarIcon: ({ color }) => <BoardIcon color={color} />,
          tabBarLabel: ({ color }) => <TabLabel label="Ranking" color={color} />,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ color }) => <PersonIcon color={color} />,
          tabBarLabel: ({ color }) => <TabLabel label="Me" color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}

function AppNavigator() {
  const { user } = useApp();
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: 'slide_from_right' }}>
        {!user ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : (
          <>
            <Stack.Screen name="Main" component={MainTabs} />
            <Stack.Screen name="Quiz" component={QuizScreen} />
            <Stack.Screen name="Results" component={ResultsScreen} options={{ animation: 'slide_from_bottom' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppNavigator />
    </AppProvider>
  );
}
