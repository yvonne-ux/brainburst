let currentSubject = null;
let currentLevel = null;
let currentSection = null;
let questions = [];
let currentQ = 0;
let answers = {};
let streak = 0;
let userData = {};

async function loadMe() {
  const res = await fetch('/api/me');
  userData = await res.json();
  document.getElementById('nav-username').textContent = userData.username;
  document.getElementById('nav-tokens').textContent = userData.tokens;
}
loadMe();

function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('section-' + name).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navMap = { home: 'nav-home', leaderboard: 'nav-leaderboard', shop: 'nav-shop', profile: 'nav-profile' };
  if (navMap[name]) document.getElementById(navMap[name]).classList.add('active');
}

function selectSubject(subject) {
  currentSubject = subject;
  document.getElementById('section-picker').classList.add('hidden');
  document.getElementById('level-picker').classList.remove('hidden');
  document.querySelectorAll('.subject-card').forEach(c => c.style.opacity = '0.5');
  event.currentTarget.style.opacity = '1';
}

function cancelSubject() {
  currentSubject = null;
  document.getElementById('level-picker').classList.add('hidden');
  document.getElementById('section-picker').classList.add('hidden');
  document.querySelectorAll('.subject-card').forEach(c => c.style.opacity = '1');
}

async function pickLevel(level) {
  currentLevel = level;
  document.getElementById('level-picker').classList.add('hidden');

  // Fetch available sections for this subject
  const res = await fetch(`/api/sections?subject=${currentSubject}`);
  const data = await res.json();
  const sections = data.sections || ['MCQ'];

  const SECTION_META = {
    MCQ:         { icon: 'A B C D', title: 'Multiple Choice',  desc: 'Choose the correct answer from 4 options' },
    ShortAnswer: { icon: '_ _ _ _', title: 'Short Answer',     desc: 'Type in the answer yourself' },
    ProblemSum:  { icon: '1 + 2 = ?', title: 'Problem Sums',  desc: 'Read and solve word problems' },
    OpenEnded:   { icon: '_ _ _ _', title: 'Open-ended',       desc: 'Write a short answer in your own words' },
  };

  const container = document.getElementById('section-cards-container');
  container.innerHTML = '';
  sections.forEach(sec => {
    const meta = SECTION_META[sec] || { icon: sec, title: sec, desc: '' };
    const card = document.createElement('div');
    card.className = 'section-card';
    card.innerHTML = `<div class="section-card-icon">${meta.icon}</div><div class="section-card-title">${meta.title}</div><div class="section-card-desc">${meta.desc}</div>`;
    card.onclick = () => selectSection(sec);
    container.appendChild(card);
  });

  document.getElementById('section-picker').classList.remove('hidden');
}

function backToLevels() {
  document.getElementById('section-picker').classList.add('hidden');
  document.getElementById('level-picker').classList.remove('hidden');
}

async function selectSection(section) {
  currentSection = section;
  const res = await fetch(`/api/questions?subject=${currentSubject}&level=${currentLevel}&section=${section}`);
  questions = await res.json();
  if (questions.length === 0) { showToast('No questions found for this section yet!'); return; }
  answers = {};
  streak = 0;
  currentQ = 0;
  showSection('quiz');
  const sectionLabel = { MCQ: 'Multiple Choice', ShortAnswer: 'Short Answer', ProblemSum: 'Problem Sums', OpenEnded: 'Open-ended' }[section] || section;
  document.getElementById('quiz-label').textContent = `${currentSubject} P${currentLevel} — ${sectionLabel}`;
  document.getElementById('q-total').textContent = questions.length;
  renderQuestion();
}

function renderQuestion() {
  const q = questions[currentQ];
  document.getElementById('q-num').textContent = currentQ + 1;
  document.getElementById('streak-count').textContent = streak;
  const pct = (currentQ / questions.length) * 100;
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('question-text').textContent = q.question;
  document.getElementById('feedback-box').classList.add('hidden');
  document.getElementById('next-btn').classList.add('hidden');

  const opts = document.getElementById('options-container');
  const openContainer = document.getElementById('open-answer-container');
  const answerInput = document.getElementById('answer-input');

  if (q.section === 'MCQ') {
    opts.classList.remove('hidden');
    openContainer.classList.add('hidden');
    opts.innerHTML = '';
    const labels = ['A', 'B', 'C', 'D'];
    q.options.forEach((opt, i) => {
      const btn = document.createElement('button');
      btn.className = 'option-btn';
      btn.innerHTML = `<span class="opt-key">${labels[i]}</span><span class="opt-text">${opt.text}</span>`;
      btn.onclick = () => selectAnswer(opt.text, q.answer_text, q.id);
      opts.appendChild(btn);
    });
  } else {
    opts.classList.add('hidden');
    openContainer.classList.remove('hidden');
    answerInput.value = '';
    answerInput.disabled = false;
    document.getElementById('submit-answer-btn').disabled = false;
    answerInput.focus();
  }
}

function selectAnswer(selected, correct, qId) {
  answers[qId] = selected;
  const allBtns = document.querySelectorAll('.option-btn');
  allBtns.forEach(b => {
    b.disabled = true;
    const text = b.querySelector('.opt-text').textContent;
    if (text === correct) b.classList.add('correct');
    else if (text === selected && selected !== correct) b.classList.add('wrong');
  });
  showFeedback(selected, correct, qId);
}

function submitTextAnswer() {
  const input = document.getElementById('answer-input');
  const selected = input.value.trim();
  if (!selected) { showToast('Please type your answer!'); return; }
  const q = questions[currentQ];
  input.disabled = true;
  document.getElementById('submit-answer-btn').disabled = true;
  answers[q.id] = selected;
  showFeedback(selected, q.answer_text, q.id);
}

function showFeedback(selected, correct, qId) {
  const correctMessages = [
    'Yes! That\'s right!', 'Nailed it!', 'Spot on!',
    'You got it!', 'That\'s correct!', 'Nice one!', 'Brilliant!',
  ];
  const wrongMessages = [
    'Oops! The answer was', 'Not quite — it\'s',
    'So close! It was', 'Good try! The answer is',
  ];

  const feedback = document.getElementById('feedback-box');
  feedback.classList.remove('hidden', 'correct', 'wrong');

  // Normalise for open-answer comparison
  function norm(t) {
    return String(t).trim().toLowerCase().replace(/^\$/, '').replace(/\s*(cm|m|kg|km\/h|litres?|degrees?|%)(\s|$)/g, '').trim();
  }

  const isCorrect = (selected === correct) || (norm(selected) === norm(correct));

  if (isCorrect) {
    streak++;
    const msg = streak >= 5
      ? `${streak} in a row — you are on fire!`
      : streak >= 3
      ? `${streak} in a row! Keep going!`
      : correctMessages[Math.floor(Math.random() * correctMessages.length)];
    feedback.textContent = msg;
    feedback.classList.add('correct');
  } else {
    streak = 0;
    const msg = wrongMessages[Math.floor(Math.random() * wrongMessages.length)];
    feedback.textContent = `${msg} ${correct}.`;
    feedback.classList.add('wrong');
  }

  document.getElementById('next-btn').textContent = currentQ + 1 >= questions.length ? 'See my results' : 'Next';
  document.getElementById('next-btn').classList.remove('hidden');
}

async function nextQuestion() {
  if (currentQ + 1 >= questions.length) {
    await submitQuiz();
    return;
  }
  currentQ++;
  renderQuestion();
}

async function submitQuiz() {
  const res = await fetch('/api/submit_quiz', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject: currentSubject, level: currentLevel, section: currentSection, answers, streak })
  });
  const data = await res.json();
  showResults(data);
  await loadMe();
}

function showResults(data) {
  showSection('results');
  const pct = data.total > 0 ? (data.score / data.total) : 0;
  let title = 'Good effort!';
  if (pct === 1)       title = 'Perfect! You got everything right!';
  else if (pct >= 0.8) title = 'So close to perfect!';
  else if (pct >= 0.6) title = 'Pretty good going!';
  else if (pct >= 0.4) title = 'Keep practising — you will get there!';
  else                 title = 'Don\'t give up — try again!';

  document.getElementById('result-title').textContent = title;
  document.getElementById('result-score').textContent = `${data.score} out of ${data.total} correct`;
  document.getElementById('result-tokens').textContent = `+${data.tokens_earned} coins earned`;

  const badgeRow = document.getElementById('new-badges');
  badgeRow.innerHTML = '';
  (data.new_badges || []).forEach(b => {
    const chip = document.createElement('div');
    chip.className = 'badge-chip';
    chip.textContent = 'Badge unlocked: ' + b;
    badgeRow.appendChild(chip);
  });

  document.getElementById('level-picker').classList.add('hidden');
  document.getElementById('section-picker').classList.add('hidden');
  document.querySelectorAll('.subject-card').forEach(c => c.style.opacity = '1');
}

// LEADERBOARD
async function loadLeaderboard() {
  const res = await fetch('/api/leaderboard');
  const data = await res.json();
  const list = document.getElementById('leaderboard-list');
  list.innerHTML = '';
  const rankLabel = ['1st', '2nd', '3rd'];
  data.forEach((u, i) => {
    const row = document.createElement('div');
    row.className = 'lb-row';
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    row.innerHTML = `
      <div class="lb-rank ${rankClass}">${rankLabel[i] || i + 1}</div>
      <div class="lb-name">${u.username}</div>
      <div class="lb-tokens">${u.tokens} coins</div>
    `;
    list.appendChild(row);
  });
}

// SHOP
async function refreshShop() {
  const res = await fetch('/api/me');
  const me = await res.json();
  const unlocked = me.unlocked_games || [];

  document.querySelectorAll('[id^="game-card-"]').forEach(card => {
    const slug = card.id.replace('game-card-', '');
    if (unlocked.includes(slug)) {
      card.classList.add('unlocked');
      const btn = card.querySelector('.btn');
      btn.textContent = 'Play';
      btn.onclick = () => window.location = '/play/' + slug;
    }
  });

  const currentAvatar = me.avatar;
  document.querySelectorAll('[id^="avatar-card-"]').forEach(card => {
    const avId = card.id.replace('avatar-card-', '');
    const btn = card.querySelector('.btn');
    if (avId === currentAvatar) { btn.textContent = 'Active'; btn.disabled = true; }
  });
}

async function unlockGame(slug, cost) {
  const res = await fetch('/api/shop/unlock_game', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slug })
  });
  const data = await res.json();
  if (data.ok) {
    showToast('Game unlocked!');
    await loadMe();
    await refreshShop();
  } else {
    showToast(data.error === 'Not enough tokens' ? 'Not enough coins!' : data.error);
  }
}

async function unlockAvatar(avatarId, cost) {
  const res = await fetch('/api/shop/unlock_avatar', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ avatar_id: avatarId })
  });
  const data = await res.json();
  if (data.ok) {
    showToast('Avatar equipped!');
    await loadMe();
    await refreshShop();
  } else {
    showToast(data.error === 'Not enough tokens' ? 'Not enough coins!' : data.error);
  }
}

function shopTab(tab, btn) {
  document.querySelectorAll('.shop-tabs .tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('shop-games').classList.add('hidden');
  document.getElementById('shop-avatars').classList.add('hidden');
  document.getElementById('shop-' + tab).classList.remove('hidden');
}

// PROFILE
async function loadProfile() {
  const res = await fetch('/api/me');
  const me = await res.json();
  document.getElementById('profile-username').textContent = me.username;
  document.getElementById('profile-tokens').textContent = me.tokens;

  const grid = document.getElementById('profile-badges');
  grid.innerHTML = '';
  if (me.badges.length === 0) {
    grid.innerHTML = '<p class="no-badges">Complete quizzes to earn badges!</p>';
  } else {
    me.badges.forEach(b => {
      const item = document.createElement('div');
      item.className = 'badge-item';
      item.innerHTML = `<div class="badge-icon-text">${b.icon}</div><div class="badge-name">${b.name}</div><div class="badge-desc">${b.description}</div>`;
      grid.appendChild(item);
    });
  }
}

let toastTimer;
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 2500);
}
