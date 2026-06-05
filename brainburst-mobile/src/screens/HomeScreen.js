import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  SafeAreaView, StatusBar,
} from 'react-native';
import { useApp } from '../context/AppContext';

const SUBJECTS = [
  { id: 'Math',    label: 'Maths',   color: '#FF7043', light: '#FFF3EF', border: '#FFCCBC' },
  { id: 'Science', label: 'Science', color: '#26A69A', light: '#E0F2F1', border: '#B2DFDB' },
  { id: 'English', label: 'English', color: '#7C5CBF', light: '#EDE7F6', border: '#D1C4E9' },
  { id: 'Chinese', label: 'Chinese', color: '#EC407A', light: '#FCE4EC', border: '#F8BBD0' },
  { id: 'Art',     label: 'Art',     color: '#FF8F00', light: '#FFF8E1', border: '#FFE0B2' },
];

const SUBJECT_ICONS = {
  Math:    require('../components/SubjectIcons').MathIcon,
  Science: require('../components/SubjectIcons').ScienceIcon,
  English: require('../components/SubjectIcons').EnglishIcon,
  Chinese: require('../components/SubjectIcons').ChineseIcon,
  Art:     require('../components/SubjectIcons').ArtIcon,
};

export default function HomeScreen({ navigation }) {
  const { user } = useApp();
  const [selected, setSelected] = useState(null);

  function pickSubject(s) {
    setSelected(s);
  }

  function pickLevel(level) {
    navigation.navigate('Quiz', { subject: selected.id, level });
    setSelected(null);
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFF8F0" />
      <ScrollView contentContainerStyle={styles.scroll}>

        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hey, {user?.username}!</Text>
            <Text style={styles.subGreeting}>What are we studying today?</Text>
          </View>
          <View style={styles.coinBadge}>
            <Text style={styles.coinText}>{user?.tokens ?? 0} coins</Text>
          </View>
        </View>

        {/* Subject grid */}
        <View style={styles.grid}>
          {SUBJECTS.map(s => {
            const Icon = SUBJECT_ICONS[s.id];
            return (
              <TouchableOpacity
                key={s.id}
                style={[styles.card, { borderColor: s.border, backgroundColor: s.light },
                  selected?.id === s.id && { borderColor: s.color, borderWidth: 3 }]}
                onPress={() => pickSubject(s)}
                activeOpacity={0.8}
              >
                <View style={[styles.iconCircle, { backgroundColor: s.color + '22' }]}>
                  <Icon size={36} color={s.color} />
                </View>
                <Text style={[styles.cardLabel, { color: s.color }]}>{s.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Level picker */}
        {selected && (
          <View style={styles.levelBox}>
            <Text style={styles.levelTitle}>Which level are you in?</Text>
            <View style={styles.levelRow}>
              {[1, 2, 3, 4, 5, 6].map(l => (
                <TouchableOpacity
                  key={l}
                  style={[styles.levelBtn, { borderColor: selected.color }]}
                  onPress={() => pickLevel(l)}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.levelBtnText, { color: selected.color }]}>P{l}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity onPress={() => setSelected(null)}>
              <Text style={styles.back}>Back</Text>
            </TouchableOpacity>
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#FFF8F0' },
  scroll: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  greeting: { fontSize: 22, fontWeight: '900', color: '#2C2C54' },
  subGreeting: { fontSize: 14, color: '#9E9E9E', fontWeight: '600', marginTop: 2 },
  coinBadge: { backgroundColor: '#FFF3CD', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 6 },
  coinText: { color: '#B7791F', fontWeight: '800', fontSize: 13 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 16 },
  card: {
    width: '47%', borderRadius: 20, padding: 18,
    borderWidth: 2, alignItems: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07, shadowRadius: 8, elevation: 3,
  },
  iconCircle: { width: 60, height: 60, borderRadius: 30, alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
  cardLabel: { fontSize: 15, fontWeight: '900' },
  levelBox: {
    backgroundColor: 'white', borderRadius: 20, padding: 20,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08, shadowRadius: 12, elevation: 4,
  },
  levelTitle: { fontSize: 16, fontWeight: '900', color: '#2C2C54', marginBottom: 14 },
  levelRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 14 },
  levelBtn: {
    borderWidth: 2.5, borderRadius: 14, paddingVertical: 12, paddingHorizontal: 14,
    backgroundColor: 'white',
  },
  levelBtnText: { fontSize: 14, fontWeight: '900' },
  back: { color: '#9E9E9E', fontWeight: '700', textAlign: 'center', fontSize: 14 },
});
