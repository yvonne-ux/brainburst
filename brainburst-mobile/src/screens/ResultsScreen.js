import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, ScrollView } from 'react-native';
import FoxMascot from '../components/FoxMascot';

export default function ResultsScreen({ route, navigation }) {
  const { result, subject, level } = route.params;
  const { score, total, tokens_earned, new_badges = [] } = result;
  const pct = total > 0 ? score / total : 0;

  let title = "Don't give up — try again!";
  if (pct === 1)       title = 'Perfect! You got everything right!';
  else if (pct >= 0.8) title = 'So close to perfect!';
  else if (pct >= 0.6) title = 'Pretty good going!';
  else if (pct >= 0.4) title = 'Keep practising — you will get there!';

  const scoreColor = pct >= 0.8 ? '#2ECC71' : pct >= 0.5 ? '#F39C12' : '#E74C3C';

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>

        <FoxMascot size={130} style={{ marginBottom: 16 }} />

        <View style={styles.card}>
          <Text style={styles.title}>{title}</Text>

          <View style={[styles.scoreBig, { borderColor: scoreColor }]}>
            <Text style={[styles.scoreNum, { color: scoreColor }]}>{score}/{total}</Text>
            <Text style={styles.scoreLabel}>correct</Text>
          </View>

          <View style={styles.coinsRow}>
            <Text style={styles.coinsText}>+{tokens_earned} coins earned</Text>
          </View>

          {new_badges.length > 0 && (
            <View style={styles.badgesBox}>
              <Text style={styles.badgesTitle}>Badges unlocked!</Text>
              {new_badges.map(b => (
                <View key={b} style={styles.badgeChip}>
                  <Text style={styles.badgeChipText}>{b}</Text>
                </View>
              ))}
            </View>
          )}

          <TouchableOpacity style={styles.btnPrimary} onPress={() => navigation.navigate('Home')} activeOpacity={0.85}>
            <Text style={styles.btnText}>Play again</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.btnSecondary} onPress={() => navigation.navigate('Leaderboard')} activeOpacity={0.85}>
            <Text style={styles.btnTextSecondary}>See rankings</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#FFF8F0' },
  scroll: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  card: { backgroundColor: 'white', borderRadius: 26, padding: 28, width: '100%', maxWidth: 380, alignItems: 'center', shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.12, shadowRadius: 24, elevation: 8, borderWidth: 2, borderColor: '#EDE8FA' },
  title: { fontSize: 20, fontWeight: '900', color: '#2C2C54', textAlign: 'center', marginBottom: 20, lineHeight: 28 },
  scoreBig: { borderWidth: 3, borderRadius: 60, width: 110, height: 110, alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  scoreNum: { fontSize: 34, fontWeight: '900' },
  scoreLabel: { fontSize: 12, color: '#9E9E9E', fontWeight: '700' },
  coinsRow: { backgroundColor: '#FFF3CD', borderRadius: 20, paddingHorizontal: 18, paddingVertical: 8, marginBottom: 20 },
  coinsText: { color: '#B7791F', fontWeight: '800', fontSize: 15 },
  badgesBox: { width: '100%', marginBottom: 20 },
  badgesTitle: { fontWeight: '900', color: '#2C2C54', marginBottom: 10, textAlign: 'center' },
  badgeChip: { backgroundColor: '#FFF8E1', borderWidth: 2, borderColor: '#FFD54F', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 6, marginBottom: 8, alignSelf: 'center' },
  badgeChipText: { color: '#B7791F', fontWeight: '800', fontSize: 13 },
  btnPrimary: { backgroundColor: '#7C5CBF', borderRadius: 14, paddingVertical: 15, paddingHorizontal: 32, width: '100%', alignItems: 'center', marginBottom: 10, shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.35, shadowRadius: 10, elevation: 6 },
  btnText: { color: 'white', fontSize: 16, fontWeight: '900' },
  btnSecondary: { borderWidth: 2, borderColor: '#EDE8FA', borderRadius: 14, paddingVertical: 14, paddingHorizontal: 32, width: '100%', alignItems: 'center' },
  btnTextSecondary: { color: '#7C5CBF', fontSize: 15, fontWeight: '800' },
});
