import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, SafeAreaView,
  ScrollView, Animated, ActivityIndicator,
} from 'react-native';
import { useApp } from '../context/AppContext';
import { API_BASE } from '../context/AppContext';

const CORRECT_MSGS = [
  "Yes! That's right!", 'Nailed it!', 'Spot on!',
  'You got it!', 'Nice one!', 'Brilliant!',
];
const WRONG_MSGS = [
  'Oops! The answer was', 'Not quite — it\'s',
  'So close! It was', 'Good try! The answer is',
];

export default function QuizScreen({ route, navigation }) {
  const { subject, level } = route.params;
  const { apiCall, refreshUser } = useApp();

  const [questions, setQuestions] = useState([]);
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState({});
  const [streak, setStreak] = useState(0);
  const [selected, setSelected] = useState(null);
  const [correct, setCorrect] = useState(null);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadQuestions();
  }, []);

  async function loadQuestions() {
    const data = await fetch(`${API_BASE}/api/questions?subject=${subject}&level=${level}`).then(r => r.json());
    setQuestions(data);
    setLoading(false);
    animateProgress(0, 0, data.length);
  }

  function animateProgress(from, to, total) {
    Animated.timing(progressAnim, {
      toValue: total > 0 ? (to / total) : 0,
      duration: 400,
      useNativeDriver: false,
    }).start();
  }

  function pickAnswer(key) {
    if (selected) return;
    const q = questions[current];
    const isCorrect = key === q.answer;
    const newStreak = isCorrect ? streak + 1 : 0;

    setSelected(key);
    setCorrect(q.answer);
    setStreak(newStreak);
    setAnswers(prev => ({ ...prev, [q.id]: key }));

    let msg = '';
    if (isCorrect) {
      if (newStreak >= 5) msg = `${newStreak} in a row — you are on fire!`;
      else if (newStreak >= 3) msg = `${newStreak} in a row! Keep going!`;
      else msg = CORRECT_MSGS[Math.floor(Math.random() * CORRECT_MSGS.length)];
    } else {
      const m = WRONG_MSGS[Math.floor(Math.random() * WRONG_MSGS.length)];
      msg = `${m} ${q.answer}.`;
    }
    setFeedback(msg);

    Animated.timing(fadeAnim, { toValue: 1, duration: 250, useNativeDriver: true }).start();
  }

  async function next() {
    const nextIdx = current + 1;
    if (nextIdx >= questions.length) {
      await submitQuiz();
      return;
    }
    fadeAnim.setValue(0);
    setSelected(null);
    setCorrect(null);
    setFeedback('');
    setCurrent(nextIdx);
    animateProgress(current / questions.length, nextIdx / questions.length, questions.length);
  }

  async function submitQuiz() {
    setSubmitting(true);
    const data = await apiCall('/api/submit_quiz', {
      method: 'POST',
      body: JSON.stringify({ subject, level, answers, streak }),
    });
    await refreshUser();
    setSubmitting(false);
    navigation.replace('Results', { result: data, subject, level });
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#7C5CBF" />
      </View>
    );
  }

  if (questions.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>No questions for this level yet!</Text>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backLink}>Go back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const q = questions[current];
  const opts = [
    { key: 'A', text: q.option_a },
    { key: 'B', text: q.option_b },
    { key: 'C', text: q.option_c },
    { key: 'D', text: q.option_d },
  ];
  const isCorrectAnswer = selected === correct;

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>Back</Text>
        </TouchableOpacity>
        <View style={styles.headerMid}>
          <Text style={styles.headerLabel}>{subject} P{level}</Text>
          <Text style={styles.headerCounter}>Question {current + 1} of {questions.length}</Text>
        </View>
        <View style={styles.streakBadge}>
          <Text style={styles.streakText}>{streak} in a row</Text>
        </View>
      </View>

      {/* Progress bar */}
      <View style={styles.progressBg}>
        <Animated.View style={[styles.progressFill, {
          width: progressAnim.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] })
        }]} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Question */}
        <View style={styles.questionCard}>
          <Text style={styles.questionText}>{q.question}</Text>
          <View style={styles.optionsGrid}>
            {opts.map(o => {
              let bg = '#FAFAFE', borderColor = '#EDE8FA', textColor = '#2C2C54', keyBg = '#EDE8FA', keyColor = '#7C5CBF';
              if (selected) {
                if (o.key === correct) { bg = '#E8FFF3'; borderColor = '#2ECC71'; textColor = '#1A7A4A'; keyBg = '#C8F5DC'; keyColor = '#1A7A4A'; }
                else if (o.key === selected) { bg = '#FFF3F3'; borderColor = '#E74C3C'; textColor = '#C0392B'; keyBg = '#FFD5D5'; keyColor = '#C0392B'; }
              }
              return (
                <TouchableOpacity
                  key={o.key}
                  style={[styles.optBtn, { backgroundColor: bg, borderColor }]}
                  onPress={() => pickAnswer(o.key)}
                  disabled={!!selected}
                  activeOpacity={0.8}
                >
                  <View style={[styles.optKey, { backgroundColor: keyBg }]}>
                    <Text style={[styles.optKeyText, { color: keyColor }]}>{o.key}</Text>
                  </View>
                  <Text style={[styles.optText, { color: textColor }]}>{o.text}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        {/* Feedback */}
        {selected && (
          <Animated.View style={[
            styles.feedbackBox,
            isCorrectAnswer ? styles.feedbackCorrect : styles.feedbackWrong,
            { opacity: fadeAnim }
          ]}>
            <Text style={[styles.feedbackText, isCorrectAnswer ? styles.feedbackTextCorrect : styles.feedbackTextWrong]}>
              {feedback}
            </Text>
          </Animated.View>
        )}

        {selected && (
          <TouchableOpacity style={styles.nextBtn} onPress={next} disabled={submitting} activeOpacity={0.85}>
            {submitting
              ? <ActivityIndicator color="white" />
              : <Text style={styles.nextBtnText}>
                  {current + 1 >= questions.length ? 'See my results' : 'Next'}
                </Text>
            }
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#FFF8F0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFF8F0' },
  emptyText: { fontSize: 16, fontWeight: '700', color: '#9E9E9E', marginBottom: 16 },
  backLink: { color: '#7C5CBF', fontWeight: '800', fontSize: 15 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, gap: 8 },
  backBtn: { backgroundColor: 'white', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 7, borderWidth: 1.5, borderColor: '#EDE8FA' },
  backBtnText: { color: '#7C5CBF', fontWeight: '800', fontSize: 13 },
  headerMid: { flex: 1, alignItems: 'center' },
  headerLabel: { fontSize: 16, fontWeight: '900', color: '#7C5CBF' },
  headerCounter: { fontSize: 11, color: '#9E9E9E', fontWeight: '600' },
  streakBadge: { backgroundColor: '#FFF3CD', borderRadius: 20, paddingHorizontal: 10, paddingVertical: 5 },
  streakText: { color: '#B7791F', fontWeight: '800', fontSize: 11 },
  progressBg: { height: 8, backgroundColor: '#EDE8FA', marginHorizontal: 16, borderRadius: 4, marginBottom: 16, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: '#7C5CBF', borderRadius: 4 },
  scroll: { padding: 16, paddingBottom: 40 },
  questionCard: { backgroundColor: 'white', borderRadius: 22, padding: 22, marginBottom: 14, borderWidth: 2, borderColor: '#EDE8FA', shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 4 },
  questionText: { fontSize: 17, fontWeight: '800', color: '#2C2C54', marginBottom: 18, lineHeight: 25 },
  optionsGrid: { gap: 10 },
  optBtn: { flexDirection: 'row', alignItems: 'center', gap: 12, borderWidth: 2.5, borderRadius: 14, padding: 14 },
  optKey: { width: 30, height: 30, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  optKeyText: { fontSize: 13, fontWeight: '900' },
  optText: { flex: 1, fontSize: 14, fontWeight: '700', lineHeight: 20 },
  feedbackBox: { borderRadius: 14, padding: 14, marginBottom: 14, borderWidth: 2 },
  feedbackCorrect: { backgroundColor: '#E8FFF3', borderColor: '#6FCFA0' },
  feedbackWrong: { backgroundColor: '#FFF3F3', borderColor: '#F1948A' },
  feedbackText: { fontSize: 15, fontWeight: '800' },
  feedbackTextCorrect: { color: '#1A7A4A' },
  feedbackTextWrong: { color: '#C0392B' },
  nextBtn: { backgroundColor: '#7C5CBF', borderRadius: 14, padding: 16, alignItems: 'center', shadowColor: '#7C5CBF', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.35, shadowRadius: 10, elevation: 6 },
  nextBtnText: { color: 'white', fontSize: 16, fontWeight: '900' },
});
