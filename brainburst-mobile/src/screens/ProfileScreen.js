import React, { useCallback } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useApp } from '../context/AppContext';
import FoxMascot from '../components/FoxMascot';

export default function ProfileScreen({ navigation }) {
  const { user, refreshUser, logout } = useApp();

  useFocusEffect(useCallback(() => { refreshUser(); }, []));

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>

        <Text style={styles.title}>My Profile</Text>

        <View style={styles.profileCard}>
          <FoxMascot size={90} />
          <Text style={styles.username}>{user?.username}</Text>
          <View style={styles.coinBadge}>
            <Text style={styles.coinText}>{user?.tokens ?? 0} coins</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Badges earned</Text>
        {user?.badges?.length > 0 ? (
          <View style={styles.badgeGrid}>
            {user.badges.map(b => (
              <View key={b.id} style={styles.badgeItem}>
                <Text style={styles.badgeIcon}>{b.icon}</Text>
                <Text style={styles.badgeName}>{b.name}</Text>
                <Text style={styles.badgeDesc}>{b.description}</Text>
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.noBadges}>Complete quizzes to earn badges!</Text>
        )}

        <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
          <Text style={styles.logoutText}>Log out</Text>
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#FFF8F0' },
  scroll: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: '900', color: '#2C2C54', marginBottom: 20 },
  profileCard: { backgroundColor: 'white', borderRadius: 22, padding: 28, alignItems: 'center', marginBottom: 24, borderWidth: 2, borderColor: '#EDE8FA', shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 4 },
  username: { fontSize: 22, fontWeight: '900', color: '#2C2C54', marginBottom: 10, marginTop: 6 },
  coinBadge: { backgroundColor: '#FFF3CD', borderRadius: 20, paddingHorizontal: 18, paddingVertical: 8 },
  coinText: { color: '#B7791F', fontWeight: '800', fontSize: 16 },
  sectionTitle: { fontSize: 17, fontWeight: '900', color: '#2C2C54', marginBottom: 14 },
  badgeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 24 },
  badgeItem: { backgroundColor: 'white', borderRadius: 16, padding: 14, alignItems: 'center', width: '30%', borderWidth: 2, borderColor: '#FFF8E1', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 6, elevation: 2 },
  badgeIcon: { fontSize: 24, marginBottom: 5 },
  badgeName: { fontSize: 11, fontWeight: '900', color: '#2C2C54', textAlign: 'center' },
  badgeDesc: { fontSize: 9, color: '#9E9E9E', textAlign: 'center', marginTop: 2, fontWeight: '600' },
  noBadges: { color: '#9E9E9E', fontSize: 14, fontWeight: '600', marginBottom: 24 },
  logoutBtn: { borderWidth: 2, borderColor: '#EDE8FA', borderRadius: 14, padding: 15, alignItems: 'center' },
  logoutText: { color: '#9E9E9E', fontWeight: '800', fontSize: 15 },
});
