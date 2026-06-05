# 🧠 BrainBurst

> Quiz your way to the top!

A playful primary-school quiz app — pick a subject and level, answer questions, earn coins, unlock avatars, and play mini-games. Comes in two parts:

| Folder | What it is | Stack |
|---|---|---|
| [`quiz_game/`](quiz_game) | Backend API + web app | Python · Flask · SQLite |
| [`brainburst-mobile/`](brainburst-mobile) | Mobile app | React Native · Expo |

## ✨ Features

- **5 subjects** — Maths, Science, English, Chinese, Art — across primary levels P1–P6
- **Multiple question types** — multiple choice, short answer, problem sums, open-ended
- **Coins & rewards** — earn coins from quizzes, with streak bonuses
- **Avatar shop** — 17 unlockable avatars
- **7 mini-games** — Memory Flip, Word Scramble, Balloon Pop, Quick Math, Memory Beats, Mole Whack, and Odd One Out
- **Badges & leaderboard** — earn badges and climb the rankings

## 🚀 Getting started

### Backend (Flask web app + API)

```bash
cd quiz_game
pip install -r requirements.txt
python app.py
```

The server runs on `http://0.0.0.0:5001`. The SQLite database (`game.db`) and quiz content are created automatically on first run. Open `http://localhost:5001` in a browser for the web version.

### Mobile app (Expo)

```bash
cd brainburst-mobile
npm install
npm start
```

Set `API_BASE` in [`src/context/AppContext.js`](brainburst-mobile/src/context/AppContext.js) to your computer's LAN IP (find it with `ipconfig getifaddr en0`) so your phone can reach the Flask server. Then scan the QR code with the Expo Go app, or run `npm run ios` / `npm run android` / `npm run web`.

## 📝 Notes

- The database file is git-ignored — it holds user accounts and is regenerated locally on first run.
- The Flask dev server is for local development only; use a production WSGI server to deploy.

## 📄 License

See [LICENSE](brainburst-mobile/LICENSE).
