import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator, Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useApp } from '../context/AppContext';
import FoxMascot from '../components/FoxMascot';

export default function LoginScreen({ navigation }) {
  const { login, register } = useApp();
  const [tab, setTab] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit() {
    setError('');
    if (!username.trim() || !password) { setError('Please fill in all fields.'); return; }
    if (tab === 'register') {
      if (username.trim().length < 3) { setError('Username must be at least 3 characters.'); return; }
      if (password !== confirm) { setError("Passwords don't match!"); return; }
    }
    setLoading(true);
    const fn = tab === 'login' ? login : register;
    const data = await fn(username.trim(), password);
    setLoading(false);
    if (!data.ok) setError(data.error || 'Something went wrong.');
  }

  return (
    <LinearGradient colors={['#FFECD2', '#FCB69F', '#C4A8E8']} style={styles.gradient}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

          <FoxMascot size={160} style={styles.fox} />

          <Text style={styles.title}>BrainBurst</Text>
          <Text style={styles.subtitle}>Quiz your way to the top</Text>

          <View style={styles.card}>
            {/* Tabs */}
            <View style={styles.tabs}>
              <TouchableOpacity
                style={[styles.tab, tab === 'login' && styles.tabActive]}
                onPress={() => { setTab('login'); setError(''); }}
              >
                <Text style={[styles.tabText, tab === 'login' && styles.tabTextActive]}>Log in</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.tab, tab === 'register' && styles.tabActive]}
                onPress={() => { setTab('register'); setError(''); }}
              >
                <Text style={[styles.tabText, tab === 'register' && styles.tabTextActive]}>New here?</Text>
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.input}
              placeholder="Your username"
              placeholderTextColor="#C5B8E8"
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TextInput
              style={styles.input}
              placeholder="Your password"
              placeholderTextColor="#C5B8E8"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
            />
            {tab === 'register' && (
              <TextInput
                style={styles.input}
                placeholder="Type password again"
                placeholderTextColor="#C5B8E8"
                value={confirm}
                onChangeText={setConfirm}
                secureTextEntry
              />
            )}

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <TouchableOpacity style={styles.btn} onPress={handleSubmit} disabled={loading}>
              {loading
                ? <ActivityIndicator color="white" />
                : <Text style={styles.btnText}>{tab === 'login' ? "Let's go!" : 'Join the fun!'}</Text>
              }
            </TouchableOpacity>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: { flex: 1 },
  scroll: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  fox: { marginBottom: 8 },
  title: { fontSize: 34, fontWeight: '900', color: '#7C5CBF', letterSpacing: -0.5, marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#9E9E9E', fontWeight: '600', marginBottom: 24 },
  card: {
    backgroundColor: 'white', borderRadius: 28, padding: 24,
    width: '100%', maxWidth: 380,
    shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.18, shadowRadius: 24, elevation: 12,
  },
  tabs: { flexDirection: 'row', backgroundColor: '#F5F0FF', borderRadius: 14, padding: 4, marginBottom: 18 },
  tab: { flex: 1, paddingVertical: 10, borderRadius: 11, alignItems: 'center' },
  tabActive: { backgroundColor: 'white', shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.15, shadowRadius: 6, elevation: 3 },
  tabText: { fontSize: 14, fontWeight: '700', color: '#9E9E9E' },
  tabTextActive: { color: '#7C5CBF', fontWeight: '800' },
  input: {
    borderWidth: 2.5, borderColor: '#EDE8FA', borderRadius: 14,
    padding: 14, fontSize: 15, fontWeight: '700', color: '#2C2C54',
    backgroundColor: '#FAFAFE', marginBottom: 12,
  },
  error: { color: '#E74C3C', fontSize: 13, fontWeight: '700', marginBottom: 10, textAlign: 'center' },
  btn: {
    backgroundColor: '#7C5CBF', borderRadius: 14, padding: 16,
    alignItems: 'center', marginTop: 4,
    shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35, shadowRadius: 10, elevation: 6,
  },
  btnText: { color: 'white', fontSize: 16, fontWeight: '900' },
});
