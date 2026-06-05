import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { API_BASE } from '../context/AppContext';

export default function LeaderboardScreen() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useFocusEffect(useCallback(() => { load(); }, []));

  async function load() {
    setLoading(true);
    const res = await fetch(`${API_BASE}/api/leaderboard`).then(r => r.json());
    setData(res);
    setLoading(false);
  }

  function rankLabel(i) {
    if (i === 0) return { label: '1st', color: '#D4AC0D', bg: '#FEF9E7' };
    if (i === 1) return { label: '2nd', color: '#808B96', bg: '#F2F3F4' };
    if (i === 2) return { label: '3rd', color: '#A04000', bg: '#FDF2E9' };
    return { label: `${i + 1}`, color: '#9E9E9E', bg: '#F5F5F5' };
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>Who's on top?</Text>
        <TouchableOpacity onPress={load} style={styles.refreshBtn}>
          <Text style={styles.refreshText}>Refresh</Text>
        </TouchableOpacity>
      </View>

      {loading
        ? <ActivityIndicator style={{ marginTop: 40 }} size="large" color="#7C5CBF" />
        : (
          <FlatList
            data={data}
            keyExtractor={(_, i) => String(i)}
            contentContainerStyle={{ padding: 16, gap: 10 }}
            renderItem={({ item, index }) => {
              const rank = rankLabel(index);
              return (
                <View style={[styles.row, index === 0 && styles.rowFirst]}>
                  <View style={[styles.rankBadge, { backgroundColor: rank.bg }]}>
                    <Text style={[styles.rankText, { color: rank.color }]}>{rank.label}</Text>
                  </View>
                  <Text style={styles.nameText}>{item.username}</Text>
                  <Text style={styles.coinsText}>{item.tokens} coins</Text>
                </View>
              );
            }}
          />
        )
      }
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#FFF8F0' },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 20, paddingBottom: 8 },
  title: { fontSize: 22, fontWeight: '900', color: '#2C2C54' },
  refreshBtn: { backgroundColor: '#EDE8FA', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 6 },
  refreshText: { color: '#7C5CBF', fontWeight: '800', fontSize: 13 },
  row: { backgroundColor: 'white', borderRadius: 16, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 12, borderWidth: 2, borderColor: '#F3F0FF', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 6, elevation: 2 },
  rowFirst: { borderColor: '#FFD700', backgroundColor: '#FFFDF0' },
  rankBadge: { borderRadius: 8, paddingHorizontal: 10, paddingVertical: 5, minWidth: 42, alignItems: 'center' },
  rankText: { fontWeight: '900', fontSize: 13 },
  nameText: { flex: 1, fontWeight: '800', color: '#2C2C54', fontSize: 15 },
  coinsText: { fontWeight: '800', color: '#B7791F', fontSize: 14 },
});
