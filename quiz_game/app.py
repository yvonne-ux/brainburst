from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3, hashlib, os, random, json, re

app = Flask(__name__)
# Use a stable secret in production so sessions survive restarts/workers.
# Falls back to a random key for quick local runs.
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

DB = os.path.join(os.path.dirname(__file__), "game.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            tokens INTEGER DEFAULT 0,
            avatar TEXT DEFAULT 'star',
            last_seen_q_ids TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            level INTEGER NOT NULL,
            section TEXT NOT NULL DEFAULT 'MCQ',
            question TEXT NOT NULL,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            answer TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT NOT NULL,
            token_cost INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS user_badges (
            user_id INTEGER,
            badge_id INTEGER,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, badge_id)
        );
        CREATE TABLE IF NOT EXISTS unlocked_games (
            user_id INTEGER,
            game_slug TEXT,
            PRIMARY KEY (user_id, game_slug)
        );
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            level INTEGER,
            score INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            tokens_earned INTEGER DEFAULT 0,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    _seed_questions(c)
    _seed_badges(c)
    conn.commit()
    conn.close()

def _seed_questions(c):
    c.execute("SELECT COUNT(*) FROM questions")
    if c.fetchone()[0] >= 1000:
        return
    # MCQ questions: (subject, level, section, question, opt_a, opt_b, opt_c, opt_d, answer)
    questions = [
        # MATH P1 MCQ
        ("Math", 1, "MCQ", "What is 3 + 4?", "6", "7", "8", "9", "B"),
        ("Math", 1, "MCQ", "What is 10 - 3?", "5", "6", "7", "8", "C"),
        ("Math", 1, "MCQ", "What is 2 × 5?", "8", "9", "10", "11", "C"),
        ("Math", 1, "MCQ", "How many sides does a triangle have?", "2", "3", "4", "5", "B"),
        ("Math", 1, "MCQ", "What is 15 ÷ 3?", "3", "4", "5", "6", "C"),
        # MATH P2
        ("Math", 2, "MCQ", "What is 25 + 37?", "52", "62", "72", "82", "B"),
        ("Math", 2, "MCQ", "What is 100 - 48?", "42", "52", "62", "72", "B"),
        ("Math", 2, "MCQ", "What is 6 × 7?", "36", "42", "48", "54", "B"),
        ("Math", 2, "MCQ", "What is 56 ÷ 8?", "6", "7", "8", "9", "B"),
        ("Math", 2, "MCQ", "What is half of 80?", "20", "30", "40", "50", "C"),
        # MATH P3
        ("Math", 3, "MCQ", "What is 123 × 4?", "482", "492", "502", "512", "B"),
        ("Math", 3, "MCQ", "What is 500 ÷ 5?", "50", "100", "150", "200", "B"),
        ("Math", 3, "MCQ", "What is the perimeter of a square with side 6cm?", "18cm", "24cm", "30cm", "36cm", "B"),
        ("Math", 3, "MCQ", "What is 3/4 of 100?", "25", "50", "75", "80", "C"),
        ("Math", 3, "MCQ", "What is 7 × 8?", "54", "56", "58", "60", "B"),
        # MATH P4
        ("Math", 4, "MCQ", "What is 1234 + 5678?", "6802", "6902", "6912", "7012", "C"),
        ("Math", 4, "MCQ", "What is 25% of 200?", "25", "50", "75", "100", "B"),
        ("Math", 4, "MCQ", "What is the area of a rectangle 8cm × 5cm?", "26cm²", "36cm²", "40cm²", "45cm²", "C"),
        ("Math", 4, "MCQ", "What is 3.5 + 2.7?", "5.2", "6.2", "6.5", "7.2", "B"),
        ("Math", 4, "MCQ", "What is 144 ÷ 12?", "10", "11", "12", "13", "C"),
        # MATH P5
        ("Math", 5, "MCQ", "What is 15% of 300?", "30", "45", "60", "75", "B"),
        ("Math", 5, "MCQ", "What is the LCM of 4 and 6?", "8", "12", "16", "24", "B"),
        ("Math", 5, "MCQ", "A triangle has angles 60° and 70°. What is the third angle?", "40°", "50°", "60°", "70°", "B"),
        ("Math", 5, "MCQ", "What is 2.5 × 4?", "8", "9", "10", "11", "C"),
        ("Math", 5, "MCQ", "What fraction is equivalent to 0.75?", "1/2", "2/3", "3/4", "4/5", "C"),
        # MATH P6
        ("Math", 6, "MCQ", "What is 20% of 450?", "80", "90", "100", "110", "B"),
        ("Math", 6, "MCQ", "What is the volume of a cube with side 3cm?", "9cm³", "18cm³", "27cm³", "36cm³", "C"),
        ("Math", 6, "MCQ", "Solve: 3x = 27. What is x?", "6", "7", "8", "9", "D"),
        ("Math", 6, "MCQ", "What is the ratio 15:25 in simplest form?", "1:2", "2:3", "3:5", "4:6", "C"),
        ("Math", 6, "MCQ", "What is 0.6 × 0.3?", "0.018", "0.18", "1.8", "18", "B"),
        # SCIENCE P1
        ("Science", 1, "MCQ", "What do plants need to make food?", "Water only", "Sunlight only", "Sunlight and water", "Soil only", "C"),
        ("Science", 1, "MCQ", "Which animal is a mammal?", "Fish", "Snake", "Dog", "Frog", "C"),
        ("Science", 1, "MCQ", "What state of matter is ice?", "Gas", "Liquid", "Solid", "Plasma", "C"),
        ("Science", 1, "MCQ", "How many legs does an insect have?", "4", "6", "8", "10", "B"),
        ("Science", 1, "MCQ", "What colour is a healthy leaf?", "Yellow", "Brown", "Green", "Red", "C"),
        # SCIENCE P2
        ("Science", 2, "MCQ", "Which organ pumps blood around the body?", "Lungs", "Brain", "Heart", "Liver", "C"),
        ("Science", 2, "MCQ", "What do we call animals that eat only plants?", "Carnivores", "Herbivores", "Omnivores", "Predators", "B"),
        ("Science", 2, "MCQ", "Which planet is closest to the Sun?", "Earth", "Venus", "Mars", "Mercury", "D"),
        ("Science", 2, "MCQ", "What gas do humans breathe in?", "Carbon dioxide", "Nitrogen", "Oxygen", "Hydrogen", "C"),
        ("Science", 2, "MCQ", "Where does a tadpole grow into a frog?", "Land", "Water", "Tree", "Underground", "B"),
        # SCIENCE P3
        ("Science", 3, "MCQ", "What is the process of water turning into vapour called?", "Condensation", "Evaporation", "Precipitation", "Melting", "B"),
        ("Science", 3, "MCQ", "Which force pulls objects toward Earth?", "Friction", "Magnetism", "Gravity", "Tension", "C"),
        ("Science", 3, "MCQ", "What do we call a material that does not let electricity flow?", "Conductor", "Semiconductor", "Insulator", "Resistor", "C"),
        ("Science", 3, "MCQ", "What type of rock is formed from cooled lava?", "Sedimentary", "Metamorphic", "Igneous", "Limestone", "C"),
        ("Science", 3, "MCQ", "Which part of the plant absorbs water from the soil?", "Leaf", "Stem", "Flower", "Root", "D"),
        # SCIENCE P4
        ("Science", 4, "MCQ", "What is the unit of measuring force?", "Kilogram", "Newton", "Metre", "Watt", "B"),
        ("Science", 4, "MCQ", "Which gas is produced during photosynthesis?", "Carbon dioxide", "Nitrogen", "Oxygen", "Water vapour", "C"),
        ("Science", 4, "MCQ", "What causes day and night?", "Earth revolving around Sun", "Moon's orbit", "Earth rotating on its axis", "Sun moving", "C"),
        ("Science", 4, "MCQ", "What is the function of the lungs?", "Digest food", "Pump blood", "Exchange gases", "Filter blood", "C"),
        ("Science", 4, "MCQ", "Which material is the best conductor of electricity?", "Plastic", "Wood", "Rubber", "Copper", "D"),
        # SCIENCE P5
        ("Science", 5, "MCQ", "What is the food chain that starts with grass?", "Grass → Lion → Deer", "Grass → Deer → Lion", "Deer → Grass → Lion", "Lion → Deer → Grass", "B"),
        ("Science", 5, "MCQ", "What is the chemical symbol for water?", "CO2", "H2O", "O2", "NaCl", "B"),
        ("Science", 5, "MCQ", "Which layer of the Earth is the outermost?", "Core", "Mantle", "Crust", "Magma", "C"),
        ("Science", 5, "MCQ", "What type of lens makes objects look bigger?", "Concave", "Flat", "Convex", "Prism", "C"),
        ("Science", 5, "MCQ", "What is the role of decomposers in an ecosystem?", "Produce food", "Hunt prey", "Break down dead matter", "Absorb sunlight", "C"),
        # SCIENCE P6
        ("Science", 6, "MCQ", "What is the SI unit of energy?", "Watt", "Joule", "Newton", "Pascal", "B"),
        ("Science", 6, "MCQ", "What is the process by which plants make food?", "Respiration", "Digestion", "Photosynthesis", "Transpiration", "C"),
        ("Science", 6, "MCQ", "Which blood cells help fight infection?", "Red blood cells", "Platelets", "White blood cells", "Plasma", "C"),
        ("Science", 6, "MCQ", "What is the speed of light?", "3×10⁶ m/s", "3×10⁷ m/s", "3×10⁸ m/s", "3×10⁹ m/s", "C"),
        ("Science", 6, "MCQ", "What gas makes up most of Earth's atmosphere?", "Oxygen", "Carbon dioxide", "Argon", "Nitrogen", "D"),
        # ENGLISH P1
        ("English", 1, "MCQ", "Which word is a noun?", "Run", "Happy", "Apple", "Quickly", "C"),
        ("English", 1, "MCQ", "What is the plural of 'cat'?", "Cates", "Cats", "Caties", "Catses", "B"),
        ("English", 1, "MCQ", "Which sentence is correct?", "She run fast.", "She runs fast.", "She running fast.", "She runned fast.", "B"),
        ("English", 1, "MCQ", "What does 'big' mean?", "Small", "Fast", "Large", "Slow", "C"),
        ("English", 1, "MCQ", "Which word rhymes with 'cat'?", "Dog", "Bat", "Cup", "Sun", "B"),
        # ENGLISH P2
        ("English", 2, "MCQ", "Which word is a verb?", "Beautiful", "Quickly", "Jump", "Blue", "C"),
        ("English", 2, "MCQ", "What is the past tense of 'eat'?", "Eated", "Eaten", "Ate", "Aten", "C"),
        ("English", 2, "MCQ", "Which is the correct spelling?", "Freind", "Friend", "Frend", "Freiend", "B"),
        ("English", 2, "MCQ", "What does 'ancient' mean?", "Modern", "New", "Very old", "Bright", "C"),
        ("English", 2, "MCQ", "Which punctuation ends a question?", ".", "!", "?", ",", "C"),
        # ENGLISH P3
        ("English", 3, "MCQ", "What is a synonym for 'happy'?", "Sad", "Angry", "Joyful", "Tired", "C"),
        ("English", 3, "MCQ", "What is an antonym for 'brave'?", "Bold", "Fearless", "Cowardly", "Strong", "C"),
        ("English", 3, "MCQ", "Which word is an adjective?", "Run", "Slowly", "Beautiful", "Jump", "C"),
        ("English", 3, "MCQ", "What does the prefix 'un-' mean?", "Again", "Before", "Not", "After", "C"),
        ("English", 3, "MCQ", "Which sentence uses correct punctuation?", "The dog ran fast", "The dog ran fast.", "the dog ran fast.", "The dog ran fast!", "B"),
        # ENGLISH P4
        ("English", 4, "MCQ", "What is a metaphor?", "A comparison using 'like' or 'as'", "A direct comparison without 'like' or 'as'", "A type of rhyme", "A repeated sound", "B"),
        ("English", 4, "MCQ", "Which word is an adverb?", "Quickly", "Quick", "Quicker", "Quicken", "A"),
        ("English", 4, "MCQ", "What is the plural of 'child'?", "Childs", "Childrens", "Children", "Childes", "C"),
        ("English", 4, "MCQ", "Choose the correct word: 'She is __ than her brother.'", "tall", "taller", "tallest", "more tall", "B"),
        ("English", 4, "MCQ", "What does 'reluctant' mean?", "Excited", "Unwilling", "Confused", "Happy", "B"),
        # ENGLISH P5
        ("English", 5, "MCQ", "What is a simile?", "A word that sounds like what it means", "A comparison using 'like' or 'as'", "A repeated consonant sound", "A type of punctuation", "B"),
        ("English", 5, "MCQ", "Which is the correct passive voice of 'The cat chased the mouse'?", "The mouse is chasing the cat.", "The mouse was chased by the cat.", "The cat was chased by the mouse.", "The mouse chased the cat.", "B"),
        ("English", 5, "MCQ", "What is the meaning of 'benevolent'?", "Cruel", "Selfish", "Kind and generous", "Brave", "C"),
        ("English", 5, "MCQ", "Which word is a conjunction?", "Quickly", "Beautiful", "Although", "Purple", "C"),
        ("English", 5, "MCQ", "What literary device is used in: 'The wind whispered through the trees'?", "Simile", "Metaphor", "Personification", "Alliteration", "C"),
        # ENGLISH P6
        ("English", 6, "MCQ", "What is alliteration?", "Repetition of vowel sounds", "Repetition of consonant sounds at the start of words", "A comparison using 'like'", "Words that rhyme", "B"),
        ("English", 6, "MCQ", "Which sentence is in the subjunctive mood?", "If I was rich, I would travel.", "If I were rich, I would travel.", "When I am rich, I travel.", "I am rich.", "B"),
        ("English", 6, "MCQ", "What does 'ambiguous' mean?", "Clear and obvious", "Open to more than one interpretation", "Completely wrong", "Extremely important", "B"),
        ("English", 6, "MCQ", "Which punctuation is used for a list within a sentence?", "Comma", "Colon", "Semicolon", "Dash", "C"),
        ("English", 6, "MCQ", "What is the tone of a piece of writing?", "The topic of the writing", "The attitude or feeling conveyed by the writing", "The plot of the story", "The length of the text", "B"),
        # CHINESE P1
        ("Chinese", 1, "MCQ", "What does '你好' mean?", "Goodbye", "Thank you", "Hello", "Sorry", "C"),
        ("Chinese", 1, "MCQ", "How do you say 'cat' in Chinese?", "狗 (Gǒu)", "猫 (Māo)", "鱼 (Yú)", "鸟 (Niǎo)", "B"),
        ("Chinese", 1, "MCQ", "What does '大' mean?", "Small", "Big", "Fast", "Slow", "B"),
        ("Chinese", 1, "MCQ", "How do you write the number 3 in Chinese?", "一", "二", "三", "四", "C"),
        ("Chinese", 1, "MCQ", "What does '谢谢' mean?", "Sorry", "Please", "Thank you", "Hello", "C"),
        # CHINESE P2
        ("Chinese", 2, "MCQ", "What does '学校' mean?", "Home", "School", "Park", "Hospital", "B"),
        ("Chinese", 2, "MCQ", "How do you say 'mother' in Chinese?", "爸爸", "哥哥", "妈妈", "姐姐", "C"),
        ("Chinese", 2, "MCQ", "What does '今天' mean?", "Yesterday", "Tomorrow", "Today", "Next week", "C"),
        ("Chinese", 2, "MCQ", "What does '书' mean?", "Pen", "Bag", "Table", "Book", "D"),
        ("Chinese", 2, "MCQ", "How do you say 'eat' in Chinese?", "喝 (Hē)", "跑 (Pǎo)", "吃 (Chī)", "看 (Kàn)", "C"),
        # CHINESE P3
        ("Chinese", 3, "MCQ", "What does '朋友' mean?", "Family", "Teacher", "Friend", "Enemy", "C"),
        ("Chinese", 3, "MCQ", "What is the meaning of '快乐'?", "Sad", "Angry", "Tired", "Happy", "D"),
        ("Chinese", 3, "MCQ", "What does '天气' mean?", "Time", "Weather", "Season", "Temperature", "B"),
        ("Chinese", 3, "MCQ", "How do you say 'beautiful' in Chinese?", "丑 (Chǒu)", "美丽 (Měilì)", "高 (Gāo)", "胖 (Pàng)", "B"),
        ("Chinese", 3, "MCQ", "What does '一起' mean?", "Alone", "Together", "Apart", "Later", "B"),
        # CHINESE P4
        ("Chinese", 4, "MCQ", "What does '认真' mean?", "Lazy", "Playful", "Serious/diligent", "Confused", "C"),
        ("Chinese", 4, "MCQ", "What is the meaning of '环境'?", "Weather", "Environment", "Society", "Culture", "B"),
        ("Chinese", 4, "MCQ", "What does '节日' mean?", "School day", "Festival/holiday", "Weekend", "Birthday", "B"),
        ("Chinese", 4, "MCQ", "How do you say 'science' in Chinese?", "数学 (Shùxué)", "语文 (Yǔwén)", "科学 (Kēxué)", "音乐 (Yīnyuè)", "C"),
        ("Chinese", 4, "MCQ", "What does '保护' mean?", "Destroy", "Protect", "Ignore", "Discover", "B"),
        # CHINESE P5
        ("Chinese", 5, "MCQ", "What does '成语' refer to?", "Chinese songs", "Chinese idioms", "Chinese poems", "Chinese proverbs", "B"),
        ("Chinese", 5, "MCQ", "What does the chengyu '一石二鸟' mean?", "One bird in hand", "Kill two birds with one stone", "A bird in the sky", "Two stones one bird", "B"),
        ("Chinese", 5, "MCQ", "What does '感恩' mean?", "Feeling proud", "Feeling sad", "Feeling grateful", "Feeling angry", "C"),
        ("Chinese", 5, "MCQ", "What does '坚持' mean?", "Give up", "Persevere", "Complain", "Rest", "B"),
        ("Chinese", 5, "MCQ", "What is '比喻' in English?", "Alliteration", "Metaphor/simile", "Rhyme", "Repetition", "B"),
        # CHINESE P6
        ("Chinese", 6, "MCQ", "What does the chengyu '半途而废' mean?", "Work very hard", "Give up halfway", "Succeed in the end", "Start over again", "B"),
        ("Chinese", 6, "MCQ", "What does '责任' mean?", "Freedom", "Responsibility", "Achievement", "Courage", "B"),
        ("Chinese", 6, "MCQ", "What is '议论文' in English?", "Narrative essay", "Descriptive essay", "Argumentative essay", "Expository essay", "C"),
        ("Chinese", 6, "MCQ", "What does '珍惜' mean?", "Waste", "Cherish/treasure", "Ignore", "Lose", "B"),
        ("Chinese", 6, "MCQ", "What does the chengyu '亡羊补牢' mean?", "Too late to do anything", "Better late than never", "Act immediately", "Never make mistakes", "B"),
        # ART P1
        ("Art", 1, "MCQ", "What are the three primary colours?", "Green, Orange, Purple", "Red, Yellow, Blue", "Black, White, Grey", "Pink, Brown, Gold", "B"),
        ("Art", 1, "MCQ", "What do you use to draw a straight line?", "Eraser", "Ruler", "Brush", "Sponge", "B"),
        ("Art", 1, "MCQ", "What shape has no corners?", "Square", "Triangle", "Circle", "Rectangle", "C"),
        ("Art", 1, "MCQ", "What colour do you get when you mix red and blue?", "Green", "Orange", "Purple", "Brown", "C"),
        ("Art", 1, "MCQ", "What tool do you use to paint?", "Pencil", "Scissors", "Brush", "Ruler", "C"),
        # ART P2
        ("Art", 2, "MCQ", "What do you call a drawing of a person's face?", "Landscape", "Portrait", "Still life", "Abstract", "B"),
        ("Art", 2, "MCQ", "What colour do red and yellow make?", "Purple", "Green", "Orange", "Brown", "C"),
        ("Art", 2, "MCQ", "What is a 'warm colour'?", "Blue", "Green", "Purple", "Red", "D"),
        ("Art", 2, "MCQ", "What do you call art made from cut and pasted pieces?", "Sculpture", "Collage", "Mosaic", "Sketch", "B"),
        ("Art", 2, "MCQ", "Which of these is a cool colour?", "Yellow", "Orange", "Blue", "Red", "C"),
        # ART P3
        ("Art", 3, "MCQ", "What is a 'still life' painting?", "A painting of moving things", "A painting of non-living or arranged objects", "A painting of people", "A painting of nature outdoors", "B"),
        ("Art", 3, "MCQ", "What does 'texture' mean in art?", "The colour of the artwork", "The size of the artwork", "How a surface feels or looks like it feels", "The shape in the artwork", "C"),
        ("Art", 3, "MCQ", "Which artist painted the Mona Lisa?", "Vincent van Gogh", "Pablo Picasso", "Leonardo da Vinci", "Michelangelo", "C"),
        ("Art", 3, "MCQ", "What are secondary colours?", "Red, Blue, Yellow", "Orange, Green, Purple", "Black, White, Grey", "Brown, Pink, Gold", "B"),
        ("Art", 3, "MCQ", "What is a 'landscape' in art?", "A painting of a person", "A painting of objects on a table", "A painting of outdoor scenery", "A painting of the sea only", "C"),
        # ART P4
        ("Art", 4, "MCQ", "What does 'perspective' mean in art?", "The use of colour", "Creating a sense of depth and distance", "The texture of paint", "The type of brush used", "B"),
        ("Art", 4, "MCQ", "Which artist is famous for 'Starry Night'?", "Claude Monet", "Pablo Picasso", "Vincent van Gogh", "Salvador Dali", "C"),
        ("Art", 4, "MCQ", "What is 'shading' in drawing?", "Using only one colour", "Adding dark and light to show depth", "Drawing outlines only", "Painting with water", "B"),
        ("Art", 4, "MCQ", "What type of art is made from clay?", "Painting", "Photography", "Sculpture/Pottery", "Collage", "C"),
        ("Art", 4, "MCQ", "What does 'symmetry' mean in art?", "One side is bigger than the other", "Both sides look the same when folded", "Random arrangement", "Using many colours", "B"),
        # ART P5
        ("Art", 5, "MCQ", "What is 'abstract art'?", "Art that looks exactly like real life", "Art that uses shapes and colours to express ideas, not realistic images", "Art made only from photos", "Art drawn only in pencil", "B"),
        ("Art", 5, "MCQ", "What is the 'colour wheel'?", "A tool showing how colours relate to each other", "A paint brush", "A type of sculpture", "A drawing technique", "A"),
        ("Art", 5, "MCQ", "What is 'complementary colours'?", "Colours next to each other on the wheel", "Colours opposite each other on the colour wheel", "All warm colours", "All cool colours", "B"),
        ("Art", 5, "MCQ", "Which art movement is Pablo Picasso associated with?", "Impressionism", "Surrealism", "Cubism", "Realism", "C"),
        ("Art", 5, "MCQ", "What is 'printmaking'?", "Taking photos", "Creating images by pressing inked surfaces onto paper", "Drawing with pencils", "Sculpting with clay", "B"),
        # ART P6
        ("Art", 6, "MCQ", "What is 'chiaroscuro'?", "A type of sculpture", "The use of strong contrasts of light and dark in art", "A painting style using dots", "A type of watercolour technique", "B"),
        ("Art", 6, "MCQ", "Which artist is known for creating large soup can paintings?", "Andy Warhol", "Jackson Pollock", "Georgia O'Keeffe", "Frida Kahlo", "A"),
        ("Art", 6, "MCQ", "What does 'impressionism' focus on?", "Exact realistic detail", "Capturing light and movement with loose brushstrokes", "Abstract shapes only", "Dark and dramatic scenes", "B"),
        ("Art", 6, "MCQ", "What is 'negative space' in art?", "The main subject of the artwork", "The space around and between the subjects", "Dark colours in the painting", "The background colour", "B"),
        ("Art", 6, "MCQ", "What technique uses small dots of colour to create an image?", "Impasto", "Pointillism", "Fresco", "Chiaroscuro", "B"),
        # MATH P1 extra
        ("Math", 1, "MCQ", "What is 5 + 6?", "10", "11", "12", "13", "B"),
        ("Math", 1, "MCQ", "What is 9 - 4?", "3", "4", "5", "6", "C"),
        ("Math", 1, "MCQ", "How many sides does a square have?", "3", "4", "5", "6", "B"),
        ("Math", 1, "MCQ", "What is 3 × 3?", "6", "7", "8", "9", "D"),
        ("Math", 1, "MCQ", "What comes after 19?", "18", "20", "21", "22", "B"),
        ("Math", 1, "MCQ", "What is 8 + 7?", "13", "14", "15", "16", "C"),
        ("Math", 1, "MCQ", "What is 12 - 5?", "5", "6", "7", "8", "C"),
        ("Math", 1, "MCQ", "How many days are in a week?", "5", "6", "7", "8", "C"),
        ("Math", 1, "MCQ", "What is 4 × 2?", "6", "7", "8", "9", "C"),
        ("Math", 1, "MCQ", "What is 20 ÷ 4?", "4", "5", "6", "7", "B"),
        ("Math", 1, "MCQ", "What is 6 + 9?", "14", "15", "16", "17", "B"),
        ("Math", 1, "MCQ", "What is half of 10?", "3", "4", "5", "6", "C"),
        ("Math", 1, "MCQ", "How many months are in a year?", "10", "11", "12", "13", "C"),
        ("Math", 1, "MCQ", "What is 7 - 3?", "3", "4", "5", "6", "B"),
        ("Math", 1, "MCQ", "What is 2 + 2 + 2?", "4", "5", "6", "7", "C"),
        # MATH P2 extra
        ("Math", 2, "MCQ", "What is 34 + 29?", "53", "63", "73", "83", "B"),
        ("Math", 2, "MCQ", "What is 80 - 37?", "33", "43", "53", "63", "B"),
        ("Math", 2, "MCQ", "What is 9 × 4?", "32", "34", "36", "38", "C"),
        ("Math", 2, "MCQ", "What is 72 ÷ 9?", "7", "8", "9", "10", "B"),
        ("Math", 2, "MCQ", "What is a quarter of 40?", "5", "8", "10", "20", "C"),
        ("Math", 2, "MCQ", "What is 15 × 3?", "35", "40", "45", "50", "C"),
        ("Math", 2, "MCQ", "What is 200 - 75?", "105", "115", "125", "135", "C"),
        ("Math", 2, "MCQ", "What is 7 × 6?", "36", "40", "42", "48", "C"),
        ("Math", 2, "MCQ", "What is 48 ÷ 6?", "6", "7", "8", "9", "C"),
        ("Math", 2, "MCQ", "How many cm in 1 metre?", "10", "100", "1000", "10000", "B"),
        ("Math", 2, "MCQ", "What is 55 + 46?", "91", "101", "111", "121", "B"),
        ("Math", 2, "MCQ", "What is 8 × 8?", "56", "60", "64", "72", "C"),
        ("Math", 2, "MCQ", "What is 99 - 54?", "35", "45", "55", "65", "B"),
        ("Math", 2, "MCQ", "What is double 35?", "60", "65", "70", "75", "C"),
        ("Math", 2, "MCQ", "What is 63 ÷ 7?", "7", "8", "9", "10", "C"),
        # MATH P3 extra
        ("Math", 3, "MCQ", "What is 256 + 389?", "535", "545", "635", "645", "D"),
        ("Math", 3, "MCQ", "What is 700 - 243?", "347", "357", "457", "467", "D"),
        ("Math", 3, "MCQ", "What is 12 × 12?", "132", "140", "144", "148", "C"),
        ("Math", 3, "MCQ", "What is 1/2 + 1/4?", "1/4", "2/4", "3/4", "4/4", "C"),
        ("Math", 3, "MCQ", "What is the area of a square with side 5cm?", "20cm²", "25cm²", "30cm²", "35cm²", "B"),
        ("Math", 3, "MCQ", "What is 0.5 + 0.3?", "0.7", "0.8", "0.9", "1.0", "B"),
        ("Math", 3, "MCQ", "What is 9 × 9?", "72", "79", "81", "89", "C"),
        ("Math", 3, "MCQ", "What is 600 ÷ 6?", "10", "100", "1000", "60", "B"),
        ("Math", 3, "MCQ", "What is 2/3 of 90?", "30", "45", "60", "75", "C"),
        ("Math", 3, "MCQ", "What is the perimeter of a rectangle 8cm × 3cm?", "11cm", "22cm", "24cm", "32cm", "B"),
        ("Math", 3, "MCQ", "What is 11 × 11?", "111", "121", "131", "141", "B"),
        ("Math", 3, "MCQ", "What is 450 ÷ 9?", "40", "45", "50", "55", "C"),
        ("Math", 3, "MCQ", "Which fraction is bigger: 1/3 or 1/4?", "1/4", "1/3", "They are equal", "Cannot tell", "B"),
        ("Math", 3, "MCQ", "What is 325 × 3?", "875", "945", "975", "1025", "C"),
        ("Math", 3, "MCQ", "What is 1.5 + 2.5?", "3.0", "4.0", "5.0", "6.0", "B"),
        # MATH P4 extra
        ("Math", 4, "MCQ", "What is 50% of 180?", "80", "90", "100", "110", "B"),
        ("Math", 4, "MCQ", "What is 3456 - 1289?", "2067", "2167", "2267", "2367", "B"),
        ("Math", 4, "MCQ", "What is the area of a triangle with base 10cm and height 6cm?", "16cm²", "30cm²", "60cm²", "120cm²", "B"),
        ("Math", 4, "MCQ", "What is 2.4 × 3?", "6.2", "7.0", "7.2", "8.0", "C"),
        ("Math", 4, "MCQ", "What is 75% expressed as a fraction?", "1/2", "2/3", "3/4", "4/5", "C"),
        ("Math", 4, "MCQ", "What is 1000 ÷ 25?", "30", "35", "40", "45", "C"),
        ("Math", 4, "MCQ", "What is 4.8 - 1.9?", "2.7", "2.8", "2.9", "3.0", "C"),
        ("Math", 4, "MCQ", "What is 17 × 8?", "126", "132", "136", "142", "C"),
        ("Math", 4, "MCQ", "What is 10% of 350?", "30", "35", "40", "45", "B"),
        ("Math", 4, "MCQ", "What is the perimeter of a regular pentagon with side 7cm?", "28cm", "35cm", "42cm", "49cm", "B"),
        ("Math", 4, "MCQ", "What is 5/8 as a decimal?", "0.5", "0.6", "0.625", "0.75", "C"),
        ("Math", 4, "MCQ", "What is 234 × 5?", "1060", "1120", "1170", "1230", "C"),
        ("Math", 4, "MCQ", "What is 9.6 ÷ 4?", "2.0", "2.4", "2.8", "3.2", "B"),
        ("Math", 4, "MCQ", "What is 3/5 + 1/5?", "2/5", "3/5", "4/5", "5/5", "C"),
        ("Math", 4, "MCQ", "Which is the smallest: 0.3, 1/4, 0.28?", "0.3", "1/4", "0.28", "They are equal", "C"),
        # MATH P5 extra
        ("Math", 5, "MCQ", "What is 40% of 250?", "80", "90", "100", "110", "C"),
        ("Math", 5, "MCQ", "What is the HCF of 12 and 18?", "3", "4", "6", "9", "C"),
        ("Math", 5, "MCQ", "What is the area of a circle with radius 7cm? (use π = 22/7)", "144cm²", "154cm²", "164cm²", "174cm²", "B"),
        ("Math", 5, "MCQ", "What is 3.6 × 1.5?", "4.8", "5.0", "5.4", "5.8", "C"),
        ("Math", 5, "MCQ", "A bag has 3 red, 2 blue and 5 green balls. What is the probability of picking red?", "1/5", "3/10", "1/3", "2/5", "B"),
        ("Math", 5, "MCQ", "What is 25% of 480?", "100", "110", "120", "130", "C"),
        ("Math", 5, "MCQ", "What is 1 2/3 + 2 1/3?", "3 1/3", "3 2/3", "4", "4 1/3", "C"),
        ("Math", 5, "MCQ", "What is the ratio of 12 to 20 in simplest form?", "2:3", "3:4", "3:5", "4:5", "C"),
        ("Math", 5, "MCQ", "What is 7² (7 squared)?", "14", "42", "49", "56", "C"),
        ("Math", 5, "MCQ", "If x + 8 = 15, what is x?", "5", "6", "7", "8", "C"),
        ("Math", 5, "MCQ", "What is 0.4 × 0.2?", "0.006", "0.08", "0.8", "8", "B"),
        ("Math", 5, "MCQ", "A rectangle has area 48cm² and length 8cm. What is its width?", "4cm", "6cm", "8cm", "10cm", "B"),
        ("Math", 5, "MCQ", "What is 3/4 ÷ 3?", "1/4", "1/3", "3/4", "9/4", "A"),
        ("Math", 5, "MCQ", "What is 12.5% as a fraction?", "1/4", "1/6", "1/8", "1/10", "C"),
        ("Math", 5, "MCQ", "The speed of a car is 60 km/h. How far does it travel in 2.5 hours?", "120km", "140km", "150km", "160km", "C"),
        # MATH P6 extra
        ("Math", 6, "MCQ", "What is 15% of 600?", "75", "80", "90", "100", "C"),
        ("Math", 6, "MCQ", "A cylinder has radius 7cm and height 10cm. What is its volume? (π = 22/7)", "1450cm³", "1520cm³", "1540cm³", "1600cm³", "C"),
        ("Math", 6, "MCQ", "Solve: 4x - 5 = 19. What is x?", "4", "5", "6", "7", "C"),
        ("Math", 6, "MCQ", "What is 3:4:5 as percentages (sum = 100%)?", "20%, 30%, 50%", "25%, 33%, 42%", "25%, 33.3%, 41.7%", "30%, 40%, 30%", "C"),
        ("Math", 6, "MCQ", "What is the average of 12, 18, 24, 30?", "18", "20", "21", "22", "C"),
        ("Math", 6, "MCQ", "A shopkeeper buys an item for $80 and sells it for $100. What is the profit percentage?", "15%", "20%", "25%", "30%", "C"),
        ("Math", 6, "MCQ", "What is √144?", "10", "11", "12", "14", "C"),
        ("Math", 6, "MCQ", "If 2x + 3y = 12 and x = 3, what is y?", "1", "2", "3", "4", "B"),
        ("Math", 6, "MCQ", "What is the surface area of a cube with side 4cm?", "64cm²", "80cm²", "96cm²", "112cm²", "C"),
        ("Math", 6, "MCQ", "Express 0.125 as a fraction in simplest form.", "1/4", "1/6", "1/8", "1/10", "C"),
        ("Math", 6, "MCQ", "A train travels 240km in 3 hours. What is its speed?", "60 km/h", "70 km/h", "80 km/h", "90 km/h", "C"),
        ("Math", 6, "MCQ", "What is 2³ × 3²?", "54", "60", "72", "84", "C"),
        ("Math", 6, "MCQ", "What is 35% of 1200?", "380", "400", "420", "440", "C"),
        ("Math", 6, "MCQ", "Simplify: 5/6 - 1/3", "1/2", "1/3", "2/6", "3/6", "A"),
        ("Math", 6, "MCQ", "A circle has circumference 44cm. What is its radius? (π = 22/7)", "5cm", "6cm", "7cm", "8cm", "C"),
        # SCIENCE P1 extra
        ("Science", 1, "MCQ", "What do animals need to survive?", "Only water", "Only food", "Food, water and air", "Only sunlight", "C"),
        ("Science", 1, "MCQ", "Which of these is a fruit?", "Carrot", "Potato", "Apple", "Onion", "C"),
        ("Science", 1, "MCQ", "What do we use our eyes for?", "Hearing", "Tasting", "Seeing", "Smelling", "C"),
        ("Science", 1, "MCQ", "What is the sky like on a sunny day?", "Dark and cloudy", "Grey and rainy", "Bright and blue", "Orange and windy", "C"),
        ("Science", 1, "MCQ", "Which animal lays eggs?", "Dog", "Cat", "Hen", "Rabbit", "C"),
        ("Science", 1, "MCQ", "What season has the most rain?", "Summer", "Autumn", "Winter", "All seasons can have rain", "D"),
        ("Science", 1, "MCQ", "What do we call baby cats?", "Puppies", "Kittens", "Chicks", "Calves", "B"),
        ("Science", 1, "MCQ", "Which body part helps us smell?", "Eyes", "Ears", "Nose", "Tongue", "C"),
        ("Science", 1, "MCQ", "What is water when it is very cold?", "Steam", "Ice", "Mist", "Cloud", "B"),
        ("Science", 1, "MCQ", "How many legs does a spider have?", "4", "6", "8", "10", "C"),
        ("Science", 1, "MCQ", "Which of these is a living thing?", "Rock", "Water", "Tree", "Sand", "C"),
        ("Science", 1, "MCQ", "What part of a plant is underground?", "Flower", "Leaf", "Stem", "Root", "D"),
        ("Science", 1, "MCQ", "What do caterpillars turn into?", "Beetles", "Bees", "Butterflies", "Dragonflies", "C"),
        ("Science", 1, "MCQ", "Which sense do we use to hear music?", "Sight", "Hearing", "Touch", "Smell", "B"),
        ("Science", 1, "MCQ", "What colour is the Sun?", "White/yellow", "Blue", "Red", "Green", "A"),
        # SCIENCE P2 extra
        ("Science", 2, "MCQ", "What do plants produce that humans breathe in?", "Carbon dioxide", "Nitrogen", "Oxygen", "Hydrogen", "C"),
        ("Science", 2, "MCQ", "What type of animal is a whale?", "Fish", "Reptile", "Mammal", "Amphibian", "C"),
        ("Science", 2, "MCQ", "Which magnet pole attracts the opposite pole?", "North attracts North", "South attracts South", "Opposite poles attract", "Same poles attract", "C"),
        ("Science", 2, "MCQ", "What is the outer layer of the Earth called?", "Core", "Mantle", "Crust", "Shell", "C"),
        ("Science", 2, "MCQ", "What happens to water when heated to 100°C?", "It freezes", "It boils", "It melts", "It condenses", "B"),
        ("Science", 2, "MCQ", "Which planet has rings?", "Earth", "Mars", "Jupiter", "Saturn", "D"),
        ("Science", 2, "MCQ", "What is a baby frog called?", "Cub", "Tadpole", "Larva", "Froglet", "B"),
        ("Science", 2, "MCQ", "What is the hard outer covering of insects called?", "Shell", "Scale", "Exoskeleton", "Skin", "C"),
        ("Science", 2, "MCQ", "What do we call animals that are active at night?", "Diurnal", "Nocturnal", "Migratory", "Hibernating", "B"),
        ("Science", 2, "MCQ", "Which part of the eye controls the amount of light entering?", "Lens", "Retina", "Pupil", "Cornea", "C"),
        ("Science", 2, "MCQ", "What is the process of a caterpillar becoming a butterfly?", "Reproduction", "Germination", "Metamorphosis", "Evolution", "C"),
        ("Science", 2, "MCQ", "What force acts between two magnets?", "Gravity", "Friction", "Magnetic force", "Air resistance", "C"),
        ("Science", 2, "MCQ", "What do we call the path of the Earth around the Sun?", "Rotation", "Revolution", "Orbit", "Axis", "C"),
        ("Science", 2, "MCQ", "Which state of matter has a fixed shape?", "Gas", "Liquid", "Solid", "Plasma", "C"),
        ("Science", 2, "MCQ", "What gas do plants take in during photosynthesis?", "Oxygen", "Nitrogen", "Carbon dioxide", "Helium", "C"),
        # SCIENCE P3 extra
        ("Science", 3, "MCQ", "What is the powerhouse of the cell?", "Nucleus", "Mitochondria", "Cell wall", "Ribosome", "B"),
        ("Science", 3, "MCQ", "What is the water cycle process when water vapour cools and forms clouds?", "Evaporation", "Precipitation", "Condensation", "Infiltration", "C"),
        ("Science", 3, "MCQ", "Which type of rock is marble?", "Sedimentary", "Igneous", "Metamorphic", "Volcanic", "C"),
        ("Science", 3, "MCQ", "What is the unit of electrical current?", "Volt", "Watt", "Ampere", "Ohm", "C"),
        ("Science", 3, "MCQ", "What do we call the changing shape of the moon we see?", "Eclipses", "Phases of the moon", "Tides", "Orbits", "B"),
        ("Science", 3, "MCQ", "What is the process where plants lose water through their leaves?", "Evaporation", "Transpiration", "Condensation", "Absorption", "B"),
        ("Science", 3, "MCQ", "Which force opposes motion between two surfaces?", "Gravity", "Magnetism", "Friction", "Tension", "C"),
        ("Science", 3, "MCQ", "What is a food web?", "A single food chain", "Multiple food chains linked together", "What spiders eat", "A chain of predators", "B"),
        ("Science", 3, "MCQ", "What is the main gas in Earth's atmosphere?", "Oxygen", "Carbon dioxide", "Nitrogen", "Argon", "C"),
        ("Science", 3, "MCQ", "Which sense organ detects sound?", "Eye", "Nose", "Ear", "Skin", "C"),
        ("Science", 3, "MCQ", "What is the chemical symbol for oxygen?", "O", "O2", "Ox", "On", "A"),
        ("Science", 3, "MCQ", "What type of lens is used in a magnifying glass?", "Concave", "Flat", "Convex", "Prism", "C"),
        ("Science", 3, "MCQ", "Which planet is known as the Red Planet?", "Venus", "Mars", "Jupiter", "Saturn", "B"),
        ("Science", 3, "MCQ", "What is the function of the root hairs in a plant?", "Make food", "Absorb water and minerals", "Carry water upward", "Make seeds", "B"),
        ("Science", 3, "MCQ", "What is the unit of measuring temperature?", "Newton", "Pascal", "Degree Celsius", "Joule", "C"),
        # SCIENCE P4 extra
        ("Science", 4, "MCQ", "What is the process by which rocks are broken down?", "Erosion", "Weathering", "Sedimentation", "Compression", "B"),
        ("Science", 4, "MCQ", "What is the function of chlorophyll?", "Absorb water", "Absorb sunlight for photosynthesis", "Carry nutrients", "Store food", "B"),
        ("Science", 4, "MCQ", "Which organ filters blood in the human body?", "Liver", "Heart", "Kidneys", "Lungs", "C"),
        ("Science", 4, "MCQ", "What is the angle of incidence equal to?", "Angle of reflection", "Angle of refraction", "90 degrees", "45 degrees", "A"),
        ("Science", 4, "MCQ", "What is an ecosystem?", "A type of rock", "All living and non-living things in an area", "A food chain", "A type of climate", "B"),
        ("Science", 4, "MCQ", "What is the role of the small intestine?", "Produce bile", "Absorb nutrients", "Store food", "Filter blood", "B"),
        ("Science", 4, "MCQ", "What type of energy does the Sun produce?", "Kinetic energy only", "Chemical energy only", "Light and heat energy", "Electrical energy", "C"),
        ("Science", 4, "MCQ", "What is a conductor?", "A material that blocks electricity", "A material that allows electricity to flow", "A type of magnet", "A type of circuit", "B"),
        ("Science", 4, "MCQ", "What causes tides on Earth?", "Wind", "The Sun's heat", "The Moon's gravitational pull", "Earth's rotation", "C"),
        ("Science", 4, "MCQ", "What is the function of red blood cells?", "Fight infection", "Carry oxygen", "Clot blood", "Digest food", "B"),
        ("Science", 4, "MCQ", "What is potential energy?", "Energy of motion", "Stored energy due to position", "Energy from food", "Sound energy", "B"),
        ("Science", 4, "MCQ", "Which gas is used in photosynthesis?", "Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen", "C"),
        ("Science", 4, "MCQ", "What is the function of the skeleton?", "Produce blood only", "Support the body and protect organs", "Digest food", "Pump blood", "B"),
        ("Science", 4, "MCQ", "What happens during condensation?", "Liquid turns to gas", "Gas turns to liquid", "Solid turns to liquid", "Liquid turns to solid", "B"),
        ("Science", 4, "MCQ", "What is the source of energy for most food chains?", "Water", "Soil", "The Sun", "Air", "C"),
        # SCIENCE P5 extra
        ("Science", 5, "MCQ", "What is the formula for speed?", "Speed = Distance × Time", "Speed = Distance ÷ Time", "Speed = Time ÷ Distance", "Speed = Distance + Time", "B"),
        ("Science", 5, "MCQ", "What is the pH of pure water?", "5", "6", "7", "8", "C"),
        ("Science", 5, "MCQ", "What is osmosis?", "Movement of solutes through a membrane", "Movement of water through a semi-permeable membrane", "Evaporation of water", "Absorption of light", "B"),
        ("Science", 5, "MCQ", "Which organ produces insulin?", "Liver", "Kidney", "Pancreas", "Stomach", "C"),
        ("Science", 5, "MCQ", "What is the difference between mass and weight?", "They are the same", "Mass is the amount of matter; weight is the force of gravity on mass", "Weight is the amount of matter; mass is force", "Mass is measured in Newtons", "B"),
        ("Science", 5, "MCQ", "What is refraction?", "Reflection of light", "Bending of light when it passes through different media", "Absorption of light", "Emission of light", "B"),
        ("Science", 5, "MCQ", "What is the function of the stomata in leaves?", "Absorb water", "Allow gas exchange", "Produce glucose", "Absorb sunlight", "B"),
        ("Science", 5, "MCQ", "What is the name of the process that converts glucose to energy in cells?", "Photosynthesis", "Transpiration", "Cellular respiration", "Fermentation", "C"),
        ("Science", 5, "MCQ", "What is the difference between a producer and a consumer?", "Producers eat animals; consumers eat plants", "Producers make their own food; consumers eat other organisms", "They are the same", "Producers are animals; consumers are plants", "B"),
        ("Science", 5, "MCQ", "What is the unit of electrical resistance?", "Volt", "Ampere", "Watt", "Ohm", "D"),
        ("Science", 5, "MCQ", "What is a renewable energy source?", "Coal", "Oil", "Natural gas", "Solar energy", "D"),
        ("Science", 5, "MCQ", "What is the function of the nervous system?", "Pump blood", "Digest food", "Transmit signals between body parts and brain", "Filter waste", "C"),
        ("Science", 5, "MCQ", "What is biodiversity?", "A type of energy", "The variety of living organisms in an area", "A food chain", "A weather pattern", "B"),
        ("Science", 5, "MCQ", "Which gas causes the greenhouse effect?", "Oxygen", "Nitrogen", "Carbon dioxide", "Helium", "C"),
        ("Science", 5, "MCQ", "What is the function of the liver?", "Pump blood", "Filter blood and produce bile", "Absorb nutrients", "Produce hormones", "B"),
        # SCIENCE P6 extra
        ("Science", 6, "MCQ", "What is Newton's First Law?", "F = ma", "Objects in motion stay in motion unless acted on by force", "Every action has an equal reaction", "Energy cannot be created or destroyed", "B"),
        ("Science", 6, "MCQ", "What is the formula for pressure?", "Pressure = Force × Area", "Pressure = Force ÷ Area", "Pressure = Area ÷ Force", "Pressure = Mass × Volume", "B"),
        ("Science", 6, "MCQ", "What is DNA?", "A type of protein", "The molecule that carries genetic information", "A type of enzyme", "A cell membrane", "B"),
        ("Science", 6, "MCQ", "What is the difference between mitosis and meiosis?", "They are the same", "Mitosis produces 2 identical cells; meiosis produces 4 sex cells", "Mitosis produces sex cells; meiosis produces body cells", "Mitosis only occurs in plants", "B"),
        ("Science", 6, "MCQ", "What is the ozone layer?", "A layer of water vapour", "A layer of oxygen", "A layer of ozone gas that protects Earth from UV radiation", "A type of cloud", "C"),
        ("Science", 6, "MCQ", "What is kinetic energy?", "Stored energy", "Energy of motion", "Chemical energy", "Electrical energy", "B"),
        ("Science", 6, "MCQ", "What is the role of enzymes?", "Store energy", "Carry oxygen", "Speed up chemical reactions", "Protect cells", "C"),
        ("Science", 6, "MCQ", "What is the difference between a physical and chemical change?", "They are the same", "Physical change is reversible; chemical change forms new substances", "Chemical change is reversible; physical is not", "Physical changes form new substances", "B"),
        ("Science", 6, "MCQ", "What is the law of conservation of energy?", "Energy can be created", "Energy can be destroyed", "Energy cannot be created or destroyed, only transformed", "Energy always decreases", "C"),
        ("Science", 6, "MCQ", "What is the function of the cerebrum?", "Control breathing", "Control heart rate", "Thinking, memory and voluntary movement", "Balance and coordination", "C"),
        ("Science", 6, "MCQ", "What is a catalyst?", "A substance that slows reactions", "A substance that speeds up reactions without being consumed", "A type of acid", "A type of base", "B"),
        ("Science", 6, "MCQ", "What is the difference between series and parallel circuits?", "They are the same", "Series has one path; parallel has multiple paths", "Parallel has one path; series has multiple", "Series is safer than parallel", "B"),
        ("Science", 6, "MCQ", "What is the greenhouse effect?", "Growing plants in greenhouses", "Trapping of heat by atmospheric gases", "Cooling of Earth's surface", "Reflection of sunlight", "B"),
        ("Science", 6, "MCQ", "What is the difference between speed and velocity?", "They are the same", "Speed has direction; velocity does not", "Velocity includes direction; speed does not", "Speed is measured in km; velocity in m", "C"),
        ("Science", 6, "MCQ", "What is the function of mitochondria?", "Store DNA", "Produce proteins", "Produce energy (ATP)", "Control cell division", "C"),
        # ENGLISH P1 extra
        ("English", 1, "MCQ", "Which word is a colour?", "Run", "Blue", "Fast", "Jump", "B"),
        ("English", 1, "MCQ", "What is the opposite of 'hot'?", "Warm", "Cool", "Cold", "Icy", "C"),
        ("English", 1, "MCQ", "Which letter comes after D in the alphabet?", "C", "E", "F", "G", "B"),
        ("English", 1, "MCQ", "What is the plural of 'dog'?", "Dogies", "Doges", "Dogs", "Dogen", "C"),
        ("English", 1, "MCQ", "Which of these is an animal?", "Chair", "Table", "Horse", "Book", "C"),
        ("English", 1, "MCQ", "What does 'small' mean?", "Big", "Tall", "Little", "Fast", "C"),
        ("English", 1, "MCQ", "Which word rhymes with 'sun'?", "Moon", "Star", "Run", "Sky", "C"),
        ("English", 1, "MCQ", "What is the first letter of 'elephant'?", "A", "D", "E", "F", "C"),
        ("English", 1, "MCQ", "Which sentence has a capital letter at the start?", "the dog ran.", "The dog ran.", "the Dog ran.", "THE dog ran.", "B"),
        ("English", 1, "MCQ", "What does 'happy' mean?", "Sad", "Angry", "Scared", "Joyful", "D"),
        ("English", 1, "MCQ", "Which word is a number?", "Apple", "Seven", "Quick", "Green", "B"),
        ("English", 1, "MCQ", "What comes at the end of a telling sentence?", "?", "!", ".", ",", "C"),
        ("English", 1, "MCQ", "Which word names a place?", "Jump", "School", "Quickly", "Red", "B"),
        ("English", 1, "MCQ", "What is the plural of 'book'?", "Bookes", "Bookies", "Books", "Booksie", "C"),
        ("English", 1, "MCQ", "Which word is an action word?", "Happy", "Chair", "Dance", "Blue", "C"),
        # ENGLISH P2 extra
        ("English", 2, "MCQ", "What is the past tense of 'run'?", "Runned", "Runs", "Ran", "Running", "C"),
        ("English", 2, "MCQ", "Which word is a proper noun?", "city", "country", "Singapore", "school", "C"),
        ("English", 2, "MCQ", "What does 'enormous' mean?", "Tiny", "Average", "Very large", "Colourful", "C"),
        ("English", 2, "MCQ", "Which sentence is a question?", "The cat sat.", "Where is the cat.", "Where is the cat?", "The cat is here!", "C"),
        ("English", 2, "MCQ", "What is the opposite of 'noisy'?", "Loud", "Quiet", "Busy", "Happy", "B"),
        ("English", 2, "MCQ", "Which word correctly completes: 'She ___ to school every day.'", "go", "gone", "going", "goes", "D"),
        ("English", 2, "MCQ", "What does 'exhausted' mean?", "Excited", "Very tired", "Very happy", "Confused", "B"),
        ("English", 2, "MCQ", "Which word is an adjective?", "Swim", "Beautiful", "Quickly", "Under", "B"),
        ("English", 2, "MCQ", "What is the plural of 'leaf'?", "Leafs", "Leaves", "Leafes", "Leaes", "B"),
        ("English", 2, "MCQ", "Which sentence uses 'there' correctly?", "Their going home.", "They're going home.", "There going home.", "There are going home.", "B"),
        ("English", 2, "MCQ", "What does 'swift' mean?", "Slow", "Clumsy", "Fast", "Quiet", "C"),
        ("English", 2, "MCQ", "Which is a compound word?", "Running", "Beautiful", "Sunshine", "Quickly", "C"),
        ("English", 2, "MCQ", "What is an exclamation mark used for?", "To end a question", "To show strong feeling", "To list items", "To separate clauses", "B"),
        ("English", 2, "MCQ", "What does 'frequently' mean?", "Never", "Sometimes", "Rarely", "Often", "D"),
        ("English", 2, "MCQ", "Which word correctly completes: 'He has ___ his homework.'", "did", "done", "do", "doing", "B"),
        # ENGLISH P3 extra
        ("English", 3, "MCQ", "What is alliteration?", "Words that rhyme", "Repetition of the same starting sound", "A type of punctuation", "A word that sounds like its meaning", "B"),
        ("English", 3, "MCQ", "What is onomatopoeia?", "A comparison using like/as", "A word that sounds like what it describes", "Exaggeration for effect", "Giving human traits to objects", "B"),
        ("English", 3, "MCQ", "What does 'persuade' mean?", "To confuse someone", "To force someone", "To convince someone to do or think something", "To argue with someone", "C"),
        ("English", 3, "MCQ", "Which word is a preposition?", "Run", "Happy", "Under", "Sing", "C"),
        ("English", 3, "MCQ", "What is the purpose of a paragraph?", "To end a story", "To group related sentences about one idea", "To ask a question", "To list items", "B"),
        ("English", 3, "MCQ", "What does 'curious' mean?", "Bored", "Eager to know or learn", "Frightened", "Angry", "B"),
        ("English", 3, "MCQ", "Which sentence is in the future tense?", "She played outside.", "She plays outside.", "She will play outside.", "She is playing outside.", "C"),
        ("English", 3, "MCQ", "What is a compound sentence?", "One short sentence", "Two simple sentences joined by a conjunction", "A question sentence", "A sentence with many adjectives", "B"),
        ("English", 3, "MCQ", "What does 'unfortunately' mean?", "Luckily", "Sadly, because of bad luck", "Surprisingly", "Happily", "B"),
        ("English", 3, "MCQ", "Which word is a pronoun?", "Dog", "Run", "She", "Happy", "C"),
        ("English", 3, "MCQ", "What does 'magnificent' mean?", "Ordinary", "Terrible", "Impressively beautiful", "Very small", "C"),
        ("English", 3, "MCQ", "Which correctly uses an apostrophe for possession?", "The dogs bone", "The dog's bone", "The dogs' bone's", "The dogs bone's", "B"),
        ("English", 3, "MCQ", "What is a topic sentence?", "The last sentence in a paragraph", "The sentence that introduces the main idea of a paragraph", "A question in a paragraph", "A sentence with many adjectives", "B"),
        ("English", 3, "MCQ", "What does 'hesitate' mean?", "Move quickly", "Pause before doing something", "Shout loudly", "Disagree", "B"),
        ("English", 3, "MCQ", "Which word is a collective noun?", "Dog", "Swim", "Flock", "Happy", "C"),
        # ENGLISH P4 extra
        ("English", 4, "MCQ", "What is personification?", "A comparison using like/as", "Giving human qualities to non-human things", "Exaggeration for effect", "Words that sound like what they describe", "B"),
        ("English", 4, "MCQ", "What is hyperbole?", "A comparison using like/as", "Giving human qualities to objects", "Deliberate exaggeration for emphasis", "Words that sound like what they describe", "C"),
        ("English", 4, "MCQ", "Which sentence uses the correct form of 'lie/lay'?", "She lied the book on the table.", "She lay the book on the table.", "She laid the book on the table.", "She lain the book on the table.", "C"),
        ("English", 4, "MCQ", "What is the function of a semicolon?", "End a sentence", "Separate items in a list", "Link related independent clauses", "Show possession", "C"),
        ("English", 4, "MCQ", "What does 'controversial' mean?", "Very popular", "Causing disagreement or debate", "Completely clear", "Very boring", "B"),
        ("English", 4, "MCQ", "Which is an example of a complex sentence?", "She ran fast.", "She ran and she jumped.", "Although she was tired, she ran fast.", "She ran fast, she jumped.", "C"),
        ("English", 4, "MCQ", "What is the purpose of a conclusion in an essay?", "To introduce new ideas", "To list facts", "To summarise and wrap up the main points", "To ask questions", "C"),
        ("English", 4, "MCQ", "What does 'vivid' mean?", "Dull and boring", "Producing clear and strong mental images", "Very quiet", "Very slow", "B"),
        ("English", 4, "MCQ", "Which word correctly fills the blank: 'Neither the students nor the teacher ___ ready.'", "were", "was", "are", "have been", "B"),
        ("English", 4, "MCQ", "What is a rhetorical question?", "A question that needs an answer", "A question asked for effect, not needing an answer", "A question with many words", "A question in a story", "B"),
        ("English", 4, "MCQ", "What does 'elaborate' mean?", "Make simpler", "Make shorter", "Add more detail", "Remove detail", "C"),
        ("English", 4, "MCQ", "Which is an example of direct speech?", "She said that she was tired.", "She said she would come.", "\"I am tired,\" she said.", "She mentioned her tiredness.", "C"),
        ("English", 4, "MCQ", "What is the effect of short sentences in writing?", "Makes writing flow slowly", "Creates drama, urgency or emphasis", "Makes writing boring", "Shows detailed description", "B"),
        ("English", 4, "MCQ", "What does 'deduce' mean?", "To guess randomly", "To reach a conclusion through reasoning", "To memorise information", "To copy from another source", "B"),
        ("English", 4, "MCQ", "Which word means 'to make something worse'?", "Improve", "Aggravate", "Soothe", "Repair", "B"),
        # ENGLISH P5 extra
        ("English", 5, "MCQ", "What is the difference between 'affect' and 'effect'?", "They mean the same thing", "Affect is usually a verb; effect is usually a noun", "Effect is a verb; affect is a noun", "Both are adjectives", "B"),
        ("English", 5, "MCQ", "What is a motif in literature?", "The main character", "A recurring element that has symbolic meaning", "The setting of the story", "The climax of the plot", "B"),
        ("English", 5, "MCQ", "What does 'protagonist' mean?", "The villain of the story", "The narrator of the story", "The main character of the story", "The author of the story", "C"),
        ("English", 5, "MCQ", "What is the purpose of a thesis statement?", "To entertain the reader", "To state the main argument of an essay", "To provide background information", "To conclude the essay", "B"),
        ("English", 5, "MCQ", "What is the effect of using first-person narration?", "Creates distance from the story", "Makes the reader feel directly involved", "Makes the story less personal", "Removes the narrator from the story", "B"),
        ("English", 5, "MCQ", "What does 'implicit' mean?", "Clearly stated", "Directly expressed", "Suggested but not directly stated", "Completely hidden", "C"),
        ("English", 5, "MCQ", "What is a paradox in literature?", "A statement that seems contradictory but reveals a truth", "A comparison using like/as", "An exaggeration for effect", "A repeated phrase", "A"),
        ("English", 5, "MCQ", "What is the difference between 'then' and 'than'?", "They are the same", "'Then' relates to time; 'than' is used for comparison", "'Than' relates to time; 'then' is for comparison", "Both are conjunctions", "B"),
        ("English", 5, "MCQ", "What does 'ambivalent' mean?", "Very certain", "Having mixed or contradictory feelings", "Very happy", "Completely opposed", "B"),
        ("English", 5, "MCQ", "What is foreshadowing?", "Describing a past event", "Hinting at future events in the story", "Exaggerating an event", "Describing emotions", "B"),
        ("English", 5, "MCQ", "What is the purpose of using varied sentence structures in writing?", "To confuse the reader", "To make writing more interesting and dynamic", "To make writing simpler", "To use fewer words", "B"),
        ("English", 5, "MCQ", "What does 'infer' mean?", "State directly", "Guess randomly", "Draw a conclusion from evidence", "Copy from text", "C"),
        ("English", 5, "MCQ", "What is the effect of using repetition in writing?", "Makes writing boring", "Emphasises a point or creates rhythm", "Makes writing confusing", "Shortens the writing", "B"),
        ("English", 5, "MCQ", "What does 'bias' mean in writing?", "A balanced viewpoint", "Preference for one side over another", "A factual statement", "A neutral opinion", "B"),
        ("English", 5, "MCQ", "What is a narrative hook?", "The ending of a story", "An exciting opening that grabs the reader's attention", "The main conflict of the story", "A description of the setting", "B"),
        # ENGLISH P6 extra
        ("English", 6, "MCQ", "What is the difference between connotation and denotation?", "They are the same", "Denotation is the literal meaning; connotation is the implied meaning", "Connotation is the literal meaning; denotation is implied", "Both refer to literal meanings", "B"),
        ("English", 6, "MCQ", "What is the effect of using the passive voice?", "Makes writing more personal", "Emphasises the action rather than who did it", "Makes writing more informal", "Shows direct speech", "B"),
        ("English", 6, "MCQ", "What is dramatic irony?", "When characters say the opposite of what they mean", "When the audience knows something characters don't", "When an event is amusing", "When a story has a twist ending", "B"),
        ("English", 6, "MCQ", "What is the purpose of a counter-argument in persuasive writing?", "To weaken your argument", "To acknowledge the opposite view and refute it", "To confuse the reader", "To end the essay", "B"),
        ("English", 6, "MCQ", "What does 'succinct' mean?", "Long and detailed", "Unclear and confusing", "Brief and clear", "Very emotional", "C"),
        ("English", 6, "MCQ", "What is the effect of using rhetorical devices?", "Weakens an argument", "Makes writing dull", "Persuades and engages the reader", "Makes writing harder to understand", "C"),
        ("English", 6, "MCQ", "What is an unreliable narrator?", "A narrator who is always correct", "A narrator whose account cannot be fully trusted", "A narrator who is very detailed", "A third-person narrator", "B"),
        ("English", 6, "MCQ", "What does 'juxtaposition' mean?", "Using one idea alone", "Placing two contrasting ideas side by side for effect", "Repeating an idea", "Exaggerating an idea", "B"),
        ("English", 6, "MCQ", "What is the purpose of a discursive essay?", "To tell a story", "To describe a scene", "To explore different viewpoints on an issue", "To persuade strongly", "C"),
        ("English", 6, "MCQ", "What does 'syntax' refer to?", "Vocabulary choice", "The arrangement of words in a sentence", "The tone of writing", "The length of paragraphs", "B"),
        ("English", 6, "MCQ", "What is epistrophe?", "Repetition at the start of lines", "Repetition at the end of lines", "A comparison using like/as", "A sudden change in mood", "B"),
        ("English", 6, "MCQ", "What does 'evocative' mean?", "Hard to understand", "Bringing feelings or images to mind", "Very formal", "Very short", "B"),
        ("English", 6, "MCQ", "What is the purpose of varied vocabulary in formal writing?", "Makes writing informal", "Shows a wide range of language and avoids repetition", "Makes writing shorter", "Confuses the reader", "B"),
        ("English", 6, "MCQ", "What is a frame narrative?", "A story with no ending", "A story within a story", "A story told backwards", "A story with many characters", "B"),
        ("English", 6, "MCQ", "What does 'credible' mean?", "Unbelievable", "Able to be trusted or believed", "Very exciting", "Very complex", "B"),
        # CHINESE P1 extra
        ("Chinese", 1, "MCQ", "What does '水' mean?", "Fire", "Earth", "Water", "Wind", "C"),
        ("Chinese", 1, "MCQ", "How do you say 'father' in Chinese?", "妈妈", "爸爸", "哥哥", "弟弟", "B"),
        ("Chinese", 1, "MCQ", "What does '小' mean?", "Big", "Tall", "Fast", "Small", "D"),
        ("Chinese", 1, "MCQ", "What is '一 + 一' in Chinese?", "三", "二", "四", "五", "B"),
        ("Chinese", 1, "MCQ", "How do you say 'sun' in Chinese?", "月亮", "星星", "太阳", "天空", "C"),
        ("Chinese", 1, "MCQ", "What does '红色' mean?", "Blue colour", "Green colour", "Yellow colour", "Red colour", "D"),
        ("Chinese", 1, "MCQ", "How do you say 'goodbye' in Chinese?", "你好", "谢谢", "对不起", "再见", "D"),
        ("Chinese", 1, "MCQ", "What does '上' mean?", "Down", "Left", "Right", "Up", "D"),
        ("Chinese", 1, "MCQ", "How do you say 'rice' in Chinese?", "面条", "饺子", "米饭", "面包", "C"),
        ("Chinese", 1, "MCQ", "What does '开心' mean?", "Sad", "Angry", "Scared", "Happy", "D"),
        ("Chinese", 1, "MCQ", "What number is '五'?", "3", "4", "5", "6", "C"),
        ("Chinese", 1, "MCQ", "How do you say 'teacher' in Chinese?", "学生", "老师", "校长", "同学", "B"),
        ("Chinese", 1, "MCQ", "What does '家' mean?", "School", "Park", "Home/family", "Shop", "C"),
        ("Chinese", 1, "MCQ", "How do you say 'brother' (older) in Chinese?", "妹妹", "姐姐", "弟弟", "哥哥", "D"),
        ("Chinese", 1, "MCQ", "What does '好' mean?", "Bad", "Good", "Fast", "Slow", "B"),
        # CHINESE P2 extra
        ("Chinese", 2, "MCQ", "What does '超市' mean?", "School", "Hospital", "Supermarket", "Library", "C"),
        ("Chinese", 2, "MCQ", "How do you say 'Monday' in Chinese?", "星期二", "星期三", "星期一", "星期四", "C"),
        ("Chinese", 2, "MCQ", "What does '快' mean?", "Slow", "Loud", "Fast", "Quiet", "C"),
        ("Chinese", 2, "MCQ", "How do you say 'to drink' in Chinese?", "吃 (Chī)", "跑 (Pǎo)", "喝 (Hē)", "看 (Kàn)", "C"),
        ("Chinese", 2, "MCQ", "What does '颜色' mean?", "Size", "Shape", "Colour", "Number", "C"),
        ("Chinese", 2, "MCQ", "How do you say 'friend' in Chinese?", "同学", "老师", "朋友", "家人", "C"),
        ("Chinese", 2, "MCQ", "What does '下雨' mean?", "Sunny", "Windy", "Cloudy", "Raining", "D"),
        ("Chinese", 2, "MCQ", "How do you say 'to sleep' in Chinese?", "吃饭", "看书", "睡觉", "玩耍", "C"),
        ("Chinese", 2, "MCQ", "What does '高兴' mean?", "Sad", "Angry", "Happy", "Scared", "C"),
        ("Chinese", 2, "MCQ", "How do you say 'apple' in Chinese?", "香蕉", "橙子", "草莓", "苹果", "D"),
        ("Chinese", 2, "MCQ", "What does '图书馆' mean?", "Supermarket", "School", "Library", "Hospital", "C"),
        ("Chinese", 2, "MCQ", "How do you say 'to write' in Chinese?", "读 (Dú)", "写 (Xiě)", "画 (Huà)", "看 (Kàn)", "B"),
        ("Chinese", 2, "MCQ", "What does '弟弟' mean?", "Older brother", "Older sister", "Younger brother", "Younger sister", "C"),
        ("Chinese", 2, "MCQ", "How do you say 'game/play' in Chinese?", "工作", "学习", "游戏", "睡觉", "C"),
        ("Chinese", 2, "MCQ", "What does '生日' mean?", "New Year", "Holiday", "Birthday", "Festival", "C"),
        # CHINESE P3 extra
        ("Chinese", 3, "MCQ", "What does '勤劳' mean?", "Lazy", "Naughty", "Hardworking", "Quiet", "C"),
        ("Chinese", 3, "MCQ", "How do you say 'environment' in Chinese?", "社会", "文化", "环境", "科技", "C"),
        ("Chinese", 3, "MCQ", "What does '希望' mean?", "Fear", "Doubt", "Anger", "Hope", "D"),
        ("Chinese", 3, "MCQ", "How do you say 'to protect' in Chinese?", "破坏", "忽视", "保护", "发现", "C"),
        ("Chinese", 3, "MCQ", "What does '节约' mean?", "Waste", "Save/conserve", "Spend", "Borrow", "B"),
        ("Chinese", 3, "MCQ", "How do you say 'festival' in Chinese?", "生日", "假期", "节日", "周末", "C"),
        ("Chinese", 3, "MCQ", "What does '分享' mean?", "Hide", "Keep", "Share", "Take", "C"),
        ("Chinese", 3, "MCQ", "How do you say 'healthy' in Chinese?", "生病", "疲惫", "健康", "难过", "C"),
        ("Chinese", 3, "MCQ", "What does '努力' mean?", "Give up", "Rest", "Work hard", "Play", "C"),
        ("Chinese", 3, "MCQ", "How do you say 'nature' in Chinese?", "城市", "大自然", "科技", "社会", "B"),
        ("Chinese", 3, "MCQ", "What does '互相帮助' mean?", "Compete with each other", "Ignore each other", "Help each other", "Fight with each other", "C"),
        ("Chinese", 3, "MCQ", "How do you say 'polite' in Chinese?", "粗鲁", "害羞", "有礼貌", "骄傲", "C"),
        ("Chinese", 3, "MCQ", "What does '安全' mean?", "Danger", "Safe", "Quick", "Slow", "B"),
        ("Chinese", 3, "MCQ", "How do you say 'to recycle' in Chinese?", "浪费", "丢弃", "循环再用", "购买", "C"),
        ("Chinese", 3, "MCQ", "What does '有趣' mean?", "Boring", "Difficult", "Interesting", "Easy", "C"),
        # CHINESE P4 extra
        ("Chinese", 4, "MCQ", "What does '合作' mean?", "Competition", "Cooperation", "Argument", "Isolation", "B"),
        ("Chinese", 4, "MCQ", "What does '进步' mean?", "Go backwards", "Stay the same", "Make progress", "Give up", "C"),
        ("Chinese", 4, "MCQ", "How do you say 'technology' in Chinese?", "科学", "数学", "科技", "历史", "C"),
        ("Chinese", 4, "MCQ", "What does '关心' mean?", "Ignore", "Hate", "Care for", "Fear", "C"),
        ("Chinese", 4, "MCQ", "What does '影响' mean?", "Ignore", "Discuss", "Influence/affect", "Discover", "C"),
        ("Chinese", 4, "MCQ", "How do you say 'pollution' in Chinese?", "保护", "自然", "污染", "环境", "C"),
        ("Chinese", 4, "MCQ", "What does '传统' mean?", "Modern", "Traditional", "Foreign", "Future", "B"),
        ("Chinese", 4, "MCQ", "What does '重要' mean?", "Unimportant", "Difficult", "Important", "Easy", "C"),
        ("Chinese", 4, "MCQ", "How do you say 'to volunteer' in Chinese?", "强迫", "拒绝", "自愿", "命令", "C"),
        ("Chinese", 4, "MCQ", "What does '鼓励' mean?", "Discourage", "Encourage", "Ignore", "Punish", "B"),
        ("Chinese", 4, "MCQ", "What does '诚实' mean?", "Dishonest", "Lazy", "Honest", "Brave", "C"),
        ("Chinese", 4, "MCQ", "How do you say 'community' in Chinese?", "家庭", "学校", "社区", "国家", "C"),
        ("Chinese", 4, "MCQ", "What does '解决' mean?", "Create a problem", "Ignore a problem", "Solve a problem", "Worsen a problem", "C"),
        ("Chinese", 4, "MCQ", "What does '挑战' mean?", "Easy task", "Rest", "Challenge", "Reward", "C"),
        ("Chinese", 4, "MCQ", "How do you say 'responsibility' in Chinese?", "自由", "权利", "责任", "兴趣", "C"),
        # CHINESE P5 extra
        ("Chinese", 5, "MCQ", "What does the chengyu '马到成功' mean?", "Work very hard", "Immediate success", "Never give up", "Learn from mistakes", "B"),
        ("Chinese", 5, "MCQ", "What does '议论文' mean?", "Narrative essay", "Descriptive essay", "Argumentative essay", "Personal recount", "C"),
        ("Chinese", 5, "MCQ", "What does '借景抒情' mean as a writing technique?", "Describing characters", "Using scenery to express emotions", "Writing dialogue", "Listing facts", "B"),
        ("Chinese", 5, "MCQ", "What does the chengyu '对牛弹琴' mean?", "Play music for cows", "Wasting effort on someone who can't appreciate it", "A skilled musician", "A patient teacher", "B"),
        ("Chinese", 5, "MCQ", "What does '叙事文' mean?", "Argumentative essay", "Diary entry", "Narrative/story essay", "Letter", "C"),
        ("Chinese", 5, "MCQ", "What does '关爱' mean?", "Ignore", "Care and love", "Dislike", "Fear", "B"),
        ("Chinese", 5, "MCQ", "What does the chengyu '专心致志' mean?", "Give up easily", "Work slowly", "Focus wholeheartedly", "Work carelessly", "C"),
        ("Chinese", 5, "MCQ", "What is the purpose of '拟人' (personification) in Chinese writing?", "Makes writing shorter", "Makes things clearer factually", "Makes non-human things seem relatable and vivid", "Makes writing more formal", "C"),
        ("Chinese", 5, "MCQ", "What does '值得' mean?", "Not worth it", "Worth it", "Too expensive", "Too cheap", "B"),
        ("Chinese", 5, "MCQ", "What does the chengyu '画蛇添足' mean?", "Draw a beautiful snake", "Do something unnecessary that ruins the result", "Add more details to a drawing", "Work very carefully", "B"),
        ("Chinese", 5, "MCQ", "What does '启示' mean?", "Warning", "Lesson/inspiration drawn from an experience", "Punishment", "Reward", "B"),
        ("Chinese", 5, "MCQ", "What does '夸张' mean as a writing device?", "Simile", "Metaphor", "Exaggeration", "Repetition", "C"),
        ("Chinese", 5, "MCQ", "What does the chengyu '亡羊补牢' mean?", "It is always too late", "Better late than never", "Never make mistakes", "Rush into action", "B"),
        ("Chinese", 5, "MCQ", "What does '排比' mean in Chinese writing?", "Using rhyme", "Using parallel structures for emphasis", "Using dialogue", "Using description", "B"),
        ("Chinese", 5, "MCQ", "What does '反问' mean in Chinese writing?", "A factual question", "A rhetorical question", "A confused question", "A greeting", "B"),
        # CHINESE P6 extra
        ("Chinese", 6, "MCQ", "What does the chengyu '功亏一篑' mean?", "Work very hard", "Fail at the last step", "Succeed through teamwork", "Start over again", "B"),
        ("Chinese", 6, "MCQ", "What is the structure of an argumentative essay in Chinese?", "Introduction, body, conclusion", "Opening, problem, solution", "Beginning, middle, end", "Claim, evidence, rebuttal, conclusion", "D"),
        ("Chinese", 6, "MCQ", "What does '承上启下' mean as a paragraph function?", "Introduce new ideas", "Connect previous and next paragraphs as a transition", "Conclude the essay", "Provide examples", "B"),
        ("Chinese", 6, "MCQ", "What does the chengyu '胸有成竹' mean?", "Be nervous and unsure", "Have a plan or idea fully formed before acting", "Work without planning", "Follow others blindly", "B"),
        ("Chinese", 6, "MCQ", "What does '升华主题' mean in Chinese essay writing?", "Introduce the topic", "Provide examples", "Elevate and deepen the theme at the end", "Write the title", "C"),
        ("Chinese", 6, "MCQ", "What does '对比' mean as a writing technique?", "Comparison to show similarities", "Contrast to highlight differences", "Using metaphors", "Using dialogue", "B"),
        ("Chinese", 6, "MCQ", "What does the chengyu '百折不挠' mean?", "Give up after one failure", "Succeed on the first try", "Never give up despite setbacks", "Move forward slowly", "C"),
        ("Chinese", 6, "MCQ", "What does '感悟' mean?", "A factual observation", "A personal insight or realisation", "A plot summary", "A character description", "B"),
        ("Chinese", 6, "MCQ", "What is the function of '开门见山' in Chinese writing?", "End the essay strongly", "Start by immediately stating the main point", "Provide detailed examples", "Write a transition", "B"),
        ("Chinese", 6, "MCQ", "What does the chengyu '弄巧成拙' mean?", "A clever plan succeeds", "Being too clever causes failure", "Hard work leads to success", "Patience is rewarded", "B"),
        ("Chinese", 6, "MCQ", "What does '点题' mean in an essay?", "Write the title", "Refer back to the main theme or title", "Start a new paragraph", "Introduce characters", "B"),
        ("Chinese", 6, "MCQ", "What does '倒叙' mean as a narrative technique?", "Writing in order", "Starting at the end and flashing back", "Using dialogue only", "Describing emotions only", "B"),
        ("Chinese", 6, "MCQ", "What does the chengyu '知己知彼' mean?", "Only know yourself", "Know both yourself and your enemy", "Pretend to know everything", "Learn from teachers", "B"),
        ("Chinese", 6, "MCQ", "What does '正面描写' mean?", "Writing about negative events", "Direct description of a character or scene", "Describing events indirectly", "Writing in first person", "B"),
        ("Chinese", 6, "MCQ", "What does '首尾呼应' mean in essay writing?", "Write a long introduction", "Write a long conclusion", "The ending echoes or refers back to the opening", "Use the same sentence twice", "C"),
        # ART P1 extra
        ("Art", 1, "MCQ", "What colour do you get when you mix yellow and blue?", "Red", "Orange", "Green", "Purple", "C"),
        ("Art", 1, "MCQ", "What tool makes curved lines easily?", "Ruler", "Pencil", "Compass", "Eraser", "C"),
        ("Art", 1, "MCQ", "Which of these is NOT a primary colour?", "Red", "Yellow", "Blue", "Green", "D"),
        ("Art", 1, "MCQ", "What do you call a picture you draw of yourself?", "Landscape", "Abstract", "Self-portrait", "Still life", "C"),
        ("Art", 1, "MCQ", "What colour do you get when you mix red and yellow?", "Purple", "Green", "Orange", "Brown", "C"),
        ("Art", 1, "MCQ", "What is an eraser used for?", "Drawing lines", "Adding colour", "Removing pencil marks", "Cutting paper", "C"),
        ("Art", 1, "MCQ", "Which shape has 4 equal sides?", "Rectangle", "Triangle", "Square", "Circle", "C"),
        ("Art", 1, "MCQ", "What is the colour of the sky on a clear day?", "Green", "Red", "Orange", "Blue", "D"),
        ("Art", 1, "MCQ", "What do you use to mix paint colours?", "Scissors", "Palette", "Brush only", "Ruler", "B"),
        ("Art", 1, "MCQ", "Which colour is made by mixing white and red?", "Orange", "Yellow", "Pink", "Purple", "C"),
        ("Art", 1, "MCQ", "What do we call a drawing using only pencil?", "Painting", "Sketch", "Collage", "Print", "B"),
        ("Art", 1, "MCQ", "Which of these is made by folding paper?", "Painting", "Origami", "Sculpture", "Collage", "B"),
        ("Art", 1, "MCQ", "What does a paintbrush do?", "Cuts paper", "Applies paint or colour", "Draws straight lines", "Erases marks", "B"),
        ("Art", 1, "MCQ", "What is black and white mixed together called?", "Brown", "Beige", "Grey", "Cream", "C"),
        ("Art", 1, "MCQ", "Which of these is a 3D shape?", "Circle", "Square", "Triangle", "Sphere", "D"),
        # ART P2 extra
        ("Art", 2, "MCQ", "What is a 'horizon line' in drawing?", "A very dark line", "The line where the sky meets the ground", "A curved line", "A dotted line", "B"),
        ("Art", 2, "MCQ", "What colour do you get mixing blue and red?", "Orange", "Green", "Purple", "Brown", "C"),
        ("Art", 2, "MCQ", "What does 'foreground' mean in a picture?", "The area in the distance", "The area at the top", "The area at the front/bottom", "The background", "C"),
        ("Art", 2, "MCQ", "What is a mosaic?", "A painting using brushes", "Art made from small pieces of tiles or glass", "A type of sculpture", "A sketch using pencils", "B"),
        ("Art", 2, "MCQ", "What colour is made by mixing all primary colours of light?", "Black", "Grey", "White", "Brown", "C"),
        ("Art", 2, "MCQ", "What is watercolour?", "A type of paint that uses water", "A type of pencil", "A type of crayon", "A type of paper", "A"),
        ("Art", 2, "MCQ", "What is 'background' in a painting?", "Objects at the front", "The area behind the main objects", "The main subject", "The border of the painting", "B"),
        ("Art", 2, "MCQ", "What do we call art made by pressing clay into shapes?", "Painting", "Collage", "Pottery", "Printing", "C"),
        ("Art", 2, "MCQ", "Which colour family does turquoise belong to?", "Warm colours", "Neutral colours", "Cool colours", "Primary colours", "C"),
        ("Art", 2, "MCQ", "What is hatching in drawing?", "Drawing eggs", "Making parallel lines to show shadow", "Drawing animals", "Outlining shapes", "B"),
        ("Art", 2, "MCQ", "What does 'overlap' mean in art?", "One shape is behind another", "One shape covers part of another", "Two shapes are far apart", "Two shapes are the same size", "B"),
        ("Art", 2, "MCQ", "What is a 'border' in art?", "The main subject", "The background", "A frame around the artwork", "A type of brush", "C"),
        ("Art", 2, "MCQ", "What tool is used to cut paper?", "Brush", "Ruler", "Scissors", "Eraser", "C"),
        ("Art", 2, "MCQ", "What is 'mixed media' art?", "Art using only pencil", "Art using only paint", "Art using more than one material", "Art using only photographs", "C"),
        ("Art", 2, "MCQ", "What does 'pattern' mean in art?", "A random arrangement", "A repeated design or motif", "A single image", "A type of colour", "B"),
        # ART P3 extra
        ("Art", 3, "MCQ", "What is the difference between 2D and 3D art?", "2D has depth; 3D is flat", "2D is flat; 3D has depth and volume", "They are the same", "3D is always smaller", "B"),
        ("Art", 3, "MCQ", "What does 'proportion' mean in art?", "The colour used", "The size relationship between parts of an artwork", "The texture of the surface", "The background used", "B"),
        ("Art", 3, "MCQ", "What is 'cross-hatching'?", "Drawing X shapes", "Using criss-crossing lines to create tone and shadow", "Colouring in shapes", "Drawing borders", "B"),
        ("Art", 3, "MCQ", "Who painted 'The Starry Night'?", "Leonardo da Vinci", "Pablo Picasso", "Claude Monet", "Vincent van Gogh", "D"),
        ("Art", 3, "MCQ", "What does 'balance' mean in art?", "All objects are the same colour", "The visual weight is evenly distributed", "Only one side has objects", "All shapes are the same size", "B"),
        ("Art", 3, "MCQ", "What is a 'contour line' in drawing?", "A line showing colour", "A line that defines the edges and shape of an object", "A very thick line", "A dotted line", "B"),
        ("Art", 3, "MCQ", "What does 'value' mean in art?", "How expensive the artwork is", "The lightness or darkness of a colour", "The size of the artwork", "The texture of the artwork", "B"),
        ("Art", 3, "MCQ", "What type of art is made on a wall or ceiling?", "Easel painting", "Watercolour", "Mural", "Collage", "C"),
        ("Art", 3, "MCQ", "What does 'composition' mean in art?", "The colours used", "How elements are arranged in an artwork", "The size of the brushes", "The type of paint used", "B"),
        ("Art", 3, "MCQ", "What is a 'silhouette'?", "A colourful painting", "A dark outline shape of a figure against a lighter background", "A detailed portrait", "A type of sculpture", "B"),
        ("Art", 3, "MCQ", "What are tertiary colours?", "Red, blue, yellow", "Orange, green, purple", "Colours made by mixing a primary and secondary colour", "Black, white and grey", "C"),
        ("Art", 3, "MCQ", "What does 'emphasis' mean in art?", "Making all parts equal", "Making one part stand out as the focus", "Reducing details", "Using only one colour", "B"),
        ("Art", 3, "MCQ", "What is 'perspective' in a drawing?", "The colour of objects", "Creating an illusion of depth and distance on a flat surface", "The size of the paper", "The type of pencil used", "B"),
        ("Art", 3, "MCQ", "What is batik?", "A type of painting", "A fabric art using wax and dye", "A type of sculpture", "A printmaking technique", "B"),
        ("Art", 3, "MCQ", "What does 'unity' mean in art?", "Using many different styles", "When all parts work together to create a whole", "Using only one colour", "All objects being the same shape", "B"),
        # ART P4 extra
        ("Art", 4, "MCQ", "What is the golden ratio used for in art?", "Choosing paint colours", "Creating visually pleasing proportions and compositions", "Measuring the size of brushes", "Mixing colours", "B"),
        ("Art", 4, "MCQ", "What is foreshortening?", "Making objects shorter in real life", "Making a distant object smaller in a drawing", "Drawing an object at an angle to create depth", "Using only short brushstrokes", "C"),
        ("Art", 4, "MCQ", "What does 'rhythm' mean in art?", "Sound in music", "A feeling of movement created by repeating elements", "Using curved lines only", "Painting quickly", "B"),
        ("Art", 4, "MCQ", "What is the rule of thirds in composition?", "Divide the artwork into three colours", "Divide the image into a 3×3 grid and place subjects at intersections", "Use three main objects only", "Paint in three layers", "B"),
        ("Art", 4, "MCQ", "What is 'impasto'?", "A thin layer of paint", "An Italian food", "Thick application of paint that creates texture", "A type of collage", "C"),
        ("Art", 4, "MCQ", "What does 'monochromatic' mean?", "Using many colours", "Using only one colour and its tints and shades", "Using only black and white", "Using complementary colours", "B"),
        ("Art", 4, "MCQ", "What is 'relief sculpture'?", "Sculpture viewed from all sides", "Figures projecting from a flat background", "Sculpture made from found objects", "A type of mobile", "B"),
        ("Art", 4, "MCQ", "What does 'contrast' mean in art?", "All elements are similar", "Strong differences between elements to create interest", "Using only one element", "Using very light colours", "B"),
        ("Art", 4, "MCQ", "What is a 'tint' in colour theory?", "A colour mixed with black", "A colour mixed with white", "A colour mixed with grey", "A primary colour", "B"),
        ("Art", 4, "MCQ", "What does 'movement' mean in art?", "The artwork is physically moving", "A visual path that guides the viewer's eye through the artwork", "Only curved lines are used", "The artist moved while painting", "B"),
        ("Art", 4, "MCQ", "What is screen printing?", "Printing on a computer screen", "Pushing ink through a mesh screen onto a surface", "Printing photographs", "Scanning artwork", "B"),
        ("Art", 4, "MCQ", "What is 'vanishing point' in perspective drawing?", "Where objects disappear", "The point where parallel lines appear to meet on the horizon", "The darkest part of the drawing", "The centre of the artwork", "B"),
        ("Art", 4, "MCQ", "What does a 'shade' of a colour mean?", "Colour mixed with white", "Colour mixed with grey", "Colour mixed with black", "Colour mixed with another hue", "C"),
        ("Art", 4, "MCQ", "What is 'assemblage' in art?", "A type of painting", "Art made by assembling three-dimensional found objects", "A type of drawing technique", "A type of printmaking", "B"),
        ("Art", 4, "MCQ", "What does 'focal point' mean in an artwork?", "The area the viewer's eye is least drawn to", "The main area that attracts the viewer's attention", "The background of the artwork", "The border of the artwork", "B"),
        # ART P5 extra
        ("Art", 5, "MCQ", "What is the Bauhaus?", "A famous painting", "An influential art and design school that combined fine art and crafts", "A type of sculpture", "A painting technique", "B"),
        ("Art", 5, "MCQ", "What is 'gestural drawing'?", "Drawing very slowly and carefully", "Loose, expressive drawing that captures movement and energy", "Drawing with a ruler", "Drawing tiny details", "B"),
        ("Art", 5, "MCQ", "What is a 'diptych'?", "A single artwork", "An artwork in two panels", "An artwork in three panels", "An artwork in four panels", "B"),
        ("Art", 5, "MCQ", "What does 'saturation' mean in colour theory?", "The lightness of a colour", "The darkness of a colour", "The intensity or purity of a colour", "The temperature of a colour", "C"),
        ("Art", 5, "MCQ", "What is 'surrealism'?", "Art that depicts realistic scenes", "Art that explores the unconscious mind and dreamlike imagery", "Art that uses only geometric shapes", "Art that focuses on nature", "B"),
        ("Art", 5, "MCQ", "What is 'encaustic' painting?", "Painting with water-based paint", "Painting with wax mixed with pigment", "Painting on fabric", "Painting on glass", "B"),
        ("Art", 5, "MCQ", "What does 'juxtaposition' mean in art?", "Placing similar objects together", "Placing contrasting elements next to each other for effect", "Using only one element", "Repeating an element", "B"),
        ("Art", 5, "MCQ", "What is 'plein air' painting?", "Painting indoors only", "Painting outdoors directly from nature", "Painting using only blue", "Painting in the dark", "B"),
        ("Art", 5, "MCQ", "What is 'linocut' printing?", "Printing from a photograph", "Carving a design into linoleum and printing from it", "Printing on a computer", "Stamping with rubber stamps", "B"),
        ("Art", 5, "MCQ", "What does 'atmospheric perspective' mean?", "Painting clouds and weather", "Objects in the distance appear lighter and less detailed", "Using dark colours for the sky", "Drawing weather patterns", "B"),
        ("Art", 5, "MCQ", "What is 'typography' in design?", "A type of painting", "The art and style of arranging text", "A type of sculpture", "A printing technique", "B"),
        ("Art", 5, "MCQ", "What is a 'triptych'?", "A single artwork", "An artwork in two panels", "An artwork in three panels", "An artwork in four panels", "C"),
        ("Art", 5, "MCQ", "What does 'hue' mean in colour theory?", "The lightness of a colour", "The darkness of a colour", "The pure colour itself", "The temperature of a colour", "C"),
        ("Art", 5, "MCQ", "What is 'decalcomania'?", "A type of drawing", "A technique of pressing paint between surfaces to create patterns", "A type of sculpture", "A weaving technique", "B"),
        ("Art", 5, "MCQ", "What is 'installation art'?", "Hanging pictures on a wall", "Art that transforms a space using various materials and media", "A type of portrait", "A type of landscape painting", "B"),
        # ART P6 extra
        ("Art", 6, "MCQ", "What is the difference between 'fine art' and 'applied art'?", "They are the same", "Fine art is for aesthetic purposes; applied art has a functional use", "Applied art is more valuable", "Fine art is always more colourful", "B"),
        ("Art", 6, "MCQ", "What is 'colour harmony'?", "Using only one colour", "Pleasing combinations of colours that work well together", "Using as many colours as possible", "Using only dark colours", "B"),
        ("Art", 6, "MCQ", "What is Op Art?", "Art using optical illusions to create movement and depth", "Paintings of nature", "Abstract sculpture", "Pop culture inspired art", "A"),
        ("Art", 6, "MCQ", "What is 'sgraffito'?", "A type of Italian food", "Scratching through a top layer to reveal a different colour beneath", "A type of collage", "A printmaking technique", "B"),
        ("Art", 6, "MCQ", "What is the purpose of a 'mood board'?", "A board for rules", "A collection of images and colours to inspire and plan a design", "A type of artwork in itself", "A way to display finished work", "B"),
        ("Art", 6, "MCQ", "What is 'photorealism'?", "Taking photographs", "Painting or drawing that looks as realistic as a photograph", "Using photos as reference only", "Digital art only", "B"),
        ("Art", 6, "MCQ", "What does 'semiotics' mean in art and design?", "The study of colour", "The study of signs and symbols and their meaning", "The study of brushstrokes", "The study of composition", "B"),
        ("Art", 6, "MCQ", "What is 'vernacular architecture'?", "Famous landmark buildings", "Buildings designed using local materials and traditions", "Modern skyscrapers", "Underground buildings", "B"),
        ("Art", 6, "MCQ", "What is 'kinetic art'?", "Art that makes sounds", "Art that moves or gives the illusion of movement", "Art made from machines", "Art using digital technology only", "B"),
        ("Art", 6, "MCQ", "What does 'bricolage' mean in art?", "A French painting style", "Creating art from available materials not intended for that purpose", "A type of sculpture technique", "A style of abstract painting", "B"),
        ("Art", 6, "MCQ", "What is 'site-specific art'?", "Art made for museums only", "Art created for and responding to a particular location", "Art about famous cities", "Art displayed outdoors only", "B"),
        ("Art", 6, "MCQ", "What is 'ekphrasis'?", "A painting technique", "A written description of a visual artwork", "A type of sculpture", "A colour mixing method", "B"),
        ("Art", 6, "MCQ", "What is the difference between 'symmetrical' and 'asymmetrical' balance?", "They are the same", "Symmetrical is mirror-image balance; asymmetrical uses different elements of equal visual weight", "Asymmetrical is more balanced", "Symmetrical only uses one colour", "B"),
        ("Art", 6, "MCQ", "What is 'context' in art appreciation?", "The size of the artwork", "The circumstances (historical, cultural, personal) in which art is created and viewed", "The materials used", "The technique used", "B"),
        ("Art", 6, "MCQ", "What is 'colour temperature' in art?", "How hot the paint is", "Warm colours (reds/yellows) vs cool colours (blues/greens) and their emotional effect", "The season when the art was made", "How quickly paint dries", "B"),
    ]
    c.executemany(
        "INSERT INTO questions (subject, level, section, question, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?,?,?,?)",
        questions
    )

    # ShortAnswer questions: (subject, level, section, question, None, None, None, None, answer)
    short_answer = [
        # MATH P1 ShortAnswer
        ("Math", 1, "ShortAnswer", "What is 5 + 8?", None, None, None, None, "13"),
        ("Math", 1, "ShortAnswer", "What is 10 - 6?", None, None, None, None, "4"),
        ("Math", 1, "ShortAnswer", "What is 3 × 4?", None, None, None, None, "12"),
        ("Math", 1, "ShortAnswer", "How many sides does a rectangle have?", None, None, None, None, "4"),
        ("Math", 1, "ShortAnswer", "What is 15 ÷ 5?", None, None, None, None, "3"),
        ("Math", 1, "ShortAnswer", "What is 9 + 6?", None, None, None, None, "15"),
        ("Math", 1, "ShortAnswer", "What is 20 - 8?", None, None, None, None, "12"),
        ("Math", 1, "ShortAnswer", "What is 2 × 7?", None, None, None, None, "14"),
        ("Math", 1, "ShortAnswer", "What is 18 ÷ 2?", None, None, None, None, "9"),
        ("Math", 1, "ShortAnswer", "What is half of 16?", None, None, None, None, "8"),
        ("Math", 1, "ShortAnswer", "What is 7 + 7?", None, None, None, None, "14"),
        ("Math", 1, "ShortAnswer", "What is 30 - 13?", None, None, None, None, "17"),
        # MATH P2 ShortAnswer
        ("Math", 2, "ShortAnswer", "What is 48 ÷ 6?", None, None, None, None, "8"),
        ("Math", 2, "ShortAnswer", "What is 9 × 7?", None, None, None, None, "63"),
        ("Math", 2, "ShortAnswer", "What is 125 - 48?", None, None, None, None, "77"),
        ("Math", 2, "ShortAnswer", "What is 36 + 57?", None, None, None, None, "93"),
        ("Math", 2, "ShortAnswer", "What is a quarter of 60?", None, None, None, None, "15"),
        ("Math", 2, "ShortAnswer", "What is 8 × 9?", None, None, None, None, "72"),
        ("Math", 2, "ShortAnswer", "What is 200 - 64?", None, None, None, None, "136"),
        ("Math", 2, "ShortAnswer", "What is 77 + 34?", None, None, None, None, "111"),
        ("Math", 2, "ShortAnswer", "What is 54 ÷ 9?", None, None, None, None, "6"),
        ("Math", 2, "ShortAnswer", "What is double 46?", None, None, None, None, "92"),
        ("Math", 2, "ShortAnswer", "How many cm are in 2 metres?", None, None, None, None, "200"),
        ("Math", 2, "ShortAnswer", "What is 11 × 6?", None, None, None, None, "66"),
        # MATH P3 ShortAnswer
        ("Math", 3, "ShortAnswer", "What is 48 ÷ 6 + 7 × 3?", None, None, None, None, "29"),
        ("Math", 3, "ShortAnswer", "What is the perimeter of a square with side 9 cm?", None, None, None, None, "36"),
        ("Math", 3, "ShortAnswer", "What is 3/4 of 80?", None, None, None, None, "60"),
        ("Math", 3, "ShortAnswer", "What is 456 + 278?", None, None, None, None, "734"),
        ("Math", 3, "ShortAnswer", "What is 1/2 + 1/6?", None, None, None, None, "2/3"),
        ("Math", 3, "ShortAnswer", "What is the area of a square with side 7 cm?", None, None, None, None, "49"),
        ("Math", 3, "ShortAnswer", "What is 900 - 357?", None, None, None, None, "543"),
        ("Math", 3, "ShortAnswer", "What is 13 × 7?", None, None, None, None, "91"),
        ("Math", 3, "ShortAnswer", "What is 2/5 of 100?", None, None, None, None, "40"),
        ("Math", 3, "ShortAnswer", "What is 0.7 + 0.8?", None, None, None, None, "1.5"),
        ("Math", 3, "ShortAnswer", "What is 360 ÷ 4?", None, None, None, None, "90"),
        ("Math", 3, "ShortAnswer", "What is the perimeter of a rectangle 12 cm × 5 cm?", None, None, None, None, "34"),
        # MATH P4 ShortAnswer
        ("Math", 4, "ShortAnswer", "What is 25% of 160?", None, None, None, None, "40"),
        ("Math", 4, "ShortAnswer", "What is the area of a triangle with base 8 cm and height 5 cm?", None, None, None, None, "20"),
        ("Math", 4, "ShortAnswer", "What is 3.8 × 4?", None, None, None, None, "15.2"),
        ("Math", 4, "ShortAnswer", "What is 5/8 of 240?", None, None, None, None, "150"),
        ("Math", 4, "ShortAnswer", "What is 2456 - 1389?", None, None, None, None, "1067"),
        ("Math", 4, "ShortAnswer", "Express 0.6 as a fraction in simplest form.", None, None, None, None, "3/5"),
        ("Math", 4, "ShortAnswer", "What is 75% of 200?", None, None, None, None, "150"),
        ("Math", 4, "ShortAnswer", "What is 18 × 15?", None, None, None, None, "270"),
        ("Math", 4, "ShortAnswer", "What is the area of a rectangle 13 cm × 6 cm?", None, None, None, None, "78"),
        ("Math", 4, "ShortAnswer", "What is 4.5 + 2.7?", None, None, None, None, "7.2"),
        ("Math", 4, "ShortAnswer", "What is 50% of 346?", None, None, None, None, "173"),
        ("Math", 4, "ShortAnswer", "What is 1008 ÷ 7?", None, None, None, None, "144"),
        # MATH P5 ShortAnswer
        ("Math", 5, "ShortAnswer", "What is the LCM of 6 and 8?", None, None, None, None, "24"),
        ("Math", 5, "ShortAnswer", "What is the HCF of 24 and 36?", None, None, None, None, "12"),
        ("Math", 5, "ShortAnswer", "A triangle has angles 45° and 75°. What is the third angle?", None, None, None, None, "60"),
        ("Math", 5, "ShortAnswer", "What is 3.6 × 2.5?", None, None, None, None, "9"),
        ("Math", 5, "ShortAnswer", "Express 3/8 as a decimal.", None, None, None, None, "0.375"),
        ("Math", 5, "ShortAnswer", "What is 30% of 450?", None, None, None, None, "135"),
        ("Math", 5, "ShortAnswer", "What is 5² + 3²?", None, None, None, None, "34"),
        ("Math", 5, "ShortAnswer", "If 2x + 5 = 19, what is x?", None, None, None, None, "7"),
        ("Math", 5, "ShortAnswer", "What is 1 3/4 + 2 1/2?", None, None, None, None, "4 1/4"),
        ("Math", 5, "ShortAnswer", "What is the ratio 18:24 in simplest form?", None, None, None, None, "3:4"),
        ("Math", 5, "ShortAnswer", "What is 0.6 × 0.4?", None, None, None, None, "0.24"),
        ("Math", 5, "ShortAnswer", "A rectangle has area 60 cm² and width 5 cm. What is its length?", None, None, None, None, "12"),
        # MATH P6 ShortAnswer
        ("Math", 6, "ShortAnswer", "What is 12.5% of 400?", None, None, None, None, "50"),
        ("Math", 6, "ShortAnswer", "Solve: 5x - 7 = 23. What is x?", None, None, None, None, "6"),
        ("Math", 6, "ShortAnswer", "What is the volume of a cube with side 5 cm?", None, None, None, None, "125"),
        ("Math", 6, "ShortAnswer", "What is √169?", None, None, None, None, "13"),
        ("Math", 6, "ShortAnswer", "What is the average of 15, 22, 18, 25, 10?", None, None, None, None, "18"),
        ("Math", 6, "ShortAnswer", "Express 0.375 as a fraction in simplest form.", None, None, None, None, "3/8"),
        ("Math", 6, "ShortAnswer", "What is 2⁴ × 3²?", None, None, None, None, "144"),
        ("Math", 6, "ShortAnswer", "If 3x + 2y = 20 and x = 4, what is y?", None, None, None, None, "4"),
        ("Math", 6, "ShortAnswer", "What is the surface area of a cube with side 6 cm?", None, None, None, None, "216"),
        ("Math", 6, "ShortAnswer", "Simplify: 7/8 - 3/4", None, None, None, None, "1/8"),
        ("Math", 6, "ShortAnswer", "What is 40% of 625?", None, None, None, None, "250"),
        ("Math", 6, "ShortAnswer", "A circle has radius 14 cm. What is its circumference? (π = 22/7)", None, None, None, None, "88"),
        # SCIENCE P1-P6 ShortAnswer
        ("Science", 1, "OpenEnded", "How many legs does a butterfly have?", None, None, None, None, "6"),
        ("Science", 1, "OpenEnded", "Name one thing plants need to make food.", None, None, None, None, "sunlight"),
        ("Science", 1, "OpenEnded", "What state of matter is water when it is frozen?", None, None, None, None, "solid"),
        ("Science", 1, "OpenEnded", "How many legs does an insect have?", None, None, None, None, "6"),
        ("Science", 1, "OpenEnded", "What do we call baby dogs?", None, None, None, None, "puppies"),
        ("Science", 1, "OpenEnded", "How many legs does a spider have?", None, None, None, None, "8"),
        ("Science", 1, "OpenEnded", "What colour is a healthy leaf?", None, None, None, None, "green"),
        ("Science", 1, "OpenEnded", "Name the part of a plant that grows underground.", None, None, None, None, "root"),
        ("Science", 1, "OpenEnded", "What do caterpillars turn into?", None, None, None, None, "butterflies"),
        ("Science", 1, "OpenEnded", "Name one liquid.", None, None, None, None, "water"),
        ("Science", 1, "OpenEnded", "How many days are in a week?", None, None, None, None, "7"),
        ("Science", 1, "OpenEnded", "What gas do we breathe in to stay alive?", None, None, None, None, "oxygen"),
        ("Science", 2, "OpenEnded", "Name the gas plants take in during photosynthesis.", None, None, None, None, "carbon dioxide"),
        ("Science", 2, "OpenEnded", "What is the temperature at which water boils?", None, None, None, None, "100"),
        ("Science", 2, "OpenEnded", "Name one animal that is a mammal.", None, None, None, None, "dog"),
        ("Science", 2, "OpenEnded", "What is a baby frog called?", None, None, None, None, "tadpole"),
        ("Science", 2, "OpenEnded", "What do we call animals that eat only plants?", None, None, None, None, "herbivores"),
        ("Science", 2, "OpenEnded", "Which planet is closest to the Sun?", None, None, None, None, "Mercury"),
        ("Science", 2, "OpenEnded", "Name the process of a caterpillar becoming a butterfly.", None, None, None, None, "metamorphosis"),
        ("Science", 2, "OpenEnded", "What do we call animals that are active at night?", None, None, None, None, "nocturnal"),
        ("Science", 2, "OpenEnded", "What force acts between magnets?", None, None, None, None, "magnetic force"),
        ("Science", 2, "OpenEnded", "What state of matter has a definite shape?", None, None, None, None, "solid"),
        ("Science", 2, "OpenEnded", "Name the organ that pumps blood.", None, None, None, None, "heart"),
        ("Science", 2, "OpenEnded", "What gas do humans breathe out?", None, None, None, None, "carbon dioxide"),
        ("Science", 3, "OpenEnded", "Name the process where water turns into water vapour.", None, None, None, None, "evaporation"),
        ("Science", 3, "OpenEnded", "What force pulls objects toward Earth?", None, None, None, None, "gravity"),
        ("Science", 3, "OpenEnded", "What is the unit of electrical current?", None, None, None, None, "ampere"),
        ("Science", 3, "OpenEnded", "Name the gas released by plants during photosynthesis.", None, None, None, None, "oxygen"),
        ("Science", 3, "OpenEnded", "What planet is known as the Red Planet?", None, None, None, None, "Mars"),
        ("Science", 3, "OpenEnded", "What do root hairs absorb from the soil?", None, None, None, None, "water"),
        ("Science", 3, "OpenEnded", "Name the force that opposes motion between surfaces.", None, None, None, None, "friction"),
        ("Science", 3, "OpenEnded", "What is the main gas in Earth's atmosphere?", None, None, None, None, "nitrogen"),
        ("Science", 3, "OpenEnded", "Name the process where water vapour cools and forms clouds.", None, None, None, None, "condensation"),
        ("Science", 3, "OpenEnded", "What type of lens is used in a magnifying glass?", None, None, None, None, "convex"),
        ("Science", 3, "OpenEnded", "What is the unit of measuring temperature?", None, None, None, None, "degree Celsius"),
        ("Science", 3, "OpenEnded", "Name a material that does not conduct electricity.", None, None, None, None, "rubber"),
        ("Science", 4, "OpenEnded", "What is the unit of force?", None, None, None, None, "Newton"),
        ("Science", 4, "OpenEnded", "Name the gas produced during photosynthesis.", None, None, None, None, "oxygen"),
        ("Science", 4, "OpenEnded", "What causes day and night on Earth?", None, None, None, None, "Earth rotating on its axis"),
        ("Science", 4, "OpenEnded", "Name the organ that filters blood in the human body.", None, None, None, None, "kidney"),
        ("Science", 4, "OpenEnded", "What type of energy does the Sun produce?", None, None, None, None, "light and heat energy"),
        ("Science", 4, "OpenEnded", "Name a good conductor of electricity.", None, None, None, None, "copper"),
        ("Science", 4, "OpenEnded", "What causes tides on Earth?", None, None, None, None, "the Moon's gravitational pull"),
        ("Science", 4, "OpenEnded", "What is the function of red blood cells?", None, None, None, None, "carry oxygen"),
        ("Science", 4, "OpenEnded", "What is the source of energy for most food chains?", None, None, None, None, "the Sun"),
        ("Science", 4, "OpenEnded", "Name the process where rocks are broken down.", None, None, None, None, "weathering"),
        ("Science", 4, "OpenEnded", "What is the function of chlorophyll?", None, None, None, None, "absorb sunlight for photosynthesis"),
        ("Science", 4, "OpenEnded", "What happens during condensation?", None, None, None, None, "gas turns to liquid"),
        ("Science", 5, "OpenEnded", "What is the formula for speed?", None, None, None, None, "distance divided by time"),
        ("Science", 5, "OpenEnded", "What is the pH of pure water?", None, None, None, None, "7"),
        ("Science", 5, "OpenEnded", "Name the organ that produces insulin.", None, None, None, None, "pancreas"),
        ("Science", 5, "OpenEnded", "What is the unit of electrical resistance?", None, None, None, None, "ohm"),
        ("Science", 5, "OpenEnded", "Name one renewable energy source.", None, None, None, None, "solar energy"),
        ("Science", 5, "OpenEnded", "What is the chemical symbol for water?", None, None, None, None, "H2O"),
        ("Science", 5, "OpenEnded", "Name the process that converts glucose to energy in cells.", None, None, None, None, "cellular respiration"),
        ("Science", 5, "OpenEnded", "Which gas causes the greenhouse effect?", None, None, None, None, "carbon dioxide"),
        ("Science", 5, "OpenEnded", "What is the outermost layer of the Earth called?", None, None, None, None, "crust"),
        ("Science", 5, "OpenEnded", "Name the type of lens that makes objects look bigger.", None, None, None, None, "convex"),
        ("Science", 5, "OpenEnded", "What is biodiversity?", None, None, None, None, "the variety of living organisms in an area"),
        ("Science", 5, "OpenEnded", "Name the function of stomata in leaves.", None, None, None, None, "allow gas exchange"),
        ("Science", 6, "OpenEnded", "What is the SI unit of energy?", None, None, None, None, "joule"),
        ("Science", 6, "OpenEnded", "Name the molecule that carries genetic information.", None, None, None, None, "DNA"),
        ("Science", 6, "OpenEnded", "What is Newton's Second Law formula?", None, None, None, None, "F = ma"),
        ("Science", 6, "OpenEnded", "Name the layer of gas that protects Earth from UV radiation.", None, None, None, None, "ozone layer"),
        ("Science", 6, "OpenEnded", "What is kinetic energy?", None, None, None, None, "energy of motion"),
        ("Science", 6, "OpenEnded", "What is the formula for pressure?", None, None, None, None, "force divided by area"),
        ("Science", 6, "OpenEnded", "Name the part of the brain responsible for thinking and memory.", None, None, None, None, "cerebrum"),
        ("Science", 6, "OpenEnded", "What is the law of conservation of energy?", None, None, None, None, "energy cannot be created or destroyed"),
        ("Science", 6, "OpenEnded", "Name the function of mitochondria.", None, None, None, None, "produce energy"),
        ("Science", 6, "OpenEnded", "What is the difference between a series and parallel circuit?", None, None, None, None, "series has one path, parallel has multiple paths"),
        ("Science", 6, "OpenEnded", "Name one blood cell type that fights infection.", None, None, None, None, "white blood cells"),
        ("Science", 6, "OpenEnded", "What is the speed of light approximately?", None, None, None, None, "300000000"),
        # ENGLISH ShortAnswer
        ("English", 1, "ShortAnswer", "What is the plural of 'child'?", None, None, None, None, "children"),
        ("English", 1, "ShortAnswer", "What is the plural of 'tooth'?", None, None, None, None, "teeth"),
        ("English", 1, "ShortAnswer", "What is the opposite of 'happy'?", None, None, None, None, "sad"),
        ("English", 1, "ShortAnswer", "What is the plural of 'mouse'?", None, None, None, None, "mice"),
        ("English", 1, "ShortAnswer", "The dog ___ very fast. (run)", None, None, None, None, "runs"),
        ("English", 1, "ShortAnswer", "What is the opposite of 'big'?", None, None, None, None, "small"),
        ("English", 1, "ShortAnswer", "What is the plural of 'fish'?", None, None, None, None, "fish"),
        ("English", 1, "ShortAnswer", "What is the opposite of 'day'?", None, None, None, None, "night"),
        ("English", 1, "ShortAnswer", "She ___ a book yesterday. (read, past tense)", None, None, None, None, "read"),
        ("English", 1, "ShortAnswer", "What is the opposite of 'old'?", None, None, None, None, "new"),
        ("English", 1, "ShortAnswer", "What is the plural of 'foot'?", None, None, None, None, "feet"),
        ("English", 1, "ShortAnswer", "What is the past tense of 'go'?", None, None, None, None, "went"),
        ("English", 2, "ShortAnswer", "The children ___ playing in the park when it started to rain.", None, None, None, None, "were"),
        ("English", 2, "ShortAnswer", "What is the past tense of 'write'?", None, None, None, None, "wrote"),
        ("English", 2, "ShortAnswer", "What is the plural of 'goose'?", None, None, None, None, "geese"),
        ("English", 2, "ShortAnswer", "She is ___ (tall) than her sister. (comparative)", None, None, None, None, "taller"),
        ("English", 2, "ShortAnswer", "What is a synonym for 'big'?", None, None, None, None, "large"),
        ("English", 2, "ShortAnswer", "What is the past tense of 'swim'?", None, None, None, None, "swam"),
        ("English", 2, "ShortAnswer", "What is an antonym for 'loud'?", None, None, None, None, "quiet"),
        ("English", 2, "ShortAnswer", "He has ___ his homework. (do, past participle)", None, None, None, None, "done"),
        ("English", 2, "ShortAnswer", "What is the plural of 'woman'?", None, None, None, None, "women"),
        ("English", 2, "ShortAnswer", "What is a synonym for 'fast'?", None, None, None, None, "quick"),
        ("English", 2, "ShortAnswer", "What is the past tense of 'choose'?", None, None, None, None, "chose"),
        ("English", 2, "ShortAnswer", "What is an antonym for 'brave'?", None, None, None, None, "cowardly"),
        ("English", 3, "ShortAnswer", "Name the literary device in: 'The wind whispered through the trees.'", None, None, None, None, "personification"),
        ("English", 3, "ShortAnswer", "What is a synonym for 'enormous'?", None, None, None, None, "huge"),
        ("English", 3, "ShortAnswer", "Name the literary device that compares using 'like' or 'as'.", None, None, None, None, "simile"),
        ("English", 3, "ShortAnswer", "What is an antonym for 'ancient'?", None, None, None, None, "modern"),
        ("English", 3, "ShortAnswer", "The boy ___ to school every day. (walk, present tense)", None, None, None, None, "walks"),
        ("English", 3, "ShortAnswer", "What is a synonym for 'courageous'?", None, None, None, None, "brave"),
        ("English", 3, "ShortAnswer", "Name the punctuation mark used to show possession.", None, None, None, None, "apostrophe"),
        ("English", 3, "ShortAnswer", "What is an antonym for 'generous'?", None, None, None, None, "selfish"),
        ("English", 3, "ShortAnswer", "What part of speech is the word 'quickly'?", None, None, None, None, "adverb"),
        ("English", 3, "ShortAnswer", "What is the past tense of 'bring'?", None, None, None, None, "brought"),
        ("English", 3, "ShortAnswer", "Name the literary device: repeating the same starting sound.", None, None, None, None, "alliteration"),
        ("English", 3, "ShortAnswer", "What is a synonym for 'angry'?", None, None, None, None, "furious"),
        ("English", 4, "ShortAnswer", "Name the literary device that gives human qualities to objects.", None, None, None, None, "personification"),
        ("English", 4, "ShortAnswer", "What is a synonym for 'reluctant'?", None, None, None, None, "unwilling"),
        ("English", 4, "ShortAnswer", "Name the literary device: deliberate exaggeration for emphasis.", None, None, None, None, "hyperbole"),
        ("English", 4, "ShortAnswer", "What is an antonym for 'transparent'?", None, None, None, None, "opaque"),
        ("English", 4, "ShortAnswer", "Name the tense: 'She had finished her work before dinner.'", None, None, None, None, "past perfect"),
        ("English", 4, "ShortAnswer", "What is a synonym for 'vivid'?", None, None, None, None, "bright"),
        ("English", 4, "ShortAnswer", "Name the punctuation used to link related independent clauses.", None, None, None, None, "semicolon"),
        ("English", 4, "ShortAnswer", "What is an antonym for 'hostile'?", None, None, None, None, "friendly"),
        ("English", 4, "ShortAnswer", "What word class is 'although'?", None, None, None, None, "conjunction"),
        ("English", 4, "ShortAnswer", "What is a synonym for 'elaborate'?", None, None, None, None, "detailed"),
        ("English", 4, "ShortAnswer", "Name the voice: 'The book was written by the author.'", None, None, None, None, "passive"),
        ("English", 4, "ShortAnswer", "What is an antonym for 'timid'?", None, None, None, None, "bold"),
        ("English", 5, "ShortAnswer", "Name the literary device: hinting at future events in a story.", None, None, None, None, "foreshadowing"),
        ("English", 5, "ShortAnswer", "What is the protagonist of a story?", None, None, None, None, "the main character"),
        ("English", 5, "ShortAnswer", "Name the literary device: a statement that seems contradictory but reveals a truth.", None, None, None, None, "paradox"),
        ("English", 5, "ShortAnswer", "What is a synonym for 'ambivalent'?", None, None, None, None, "uncertain"),
        ("English", 5, "ShortAnswer", "What does 'implicit' mean?", None, None, None, None, "suggested but not directly stated"),
        ("English", 5, "ShortAnswer", "Name the narrative perspective that uses 'I'.", None, None, None, None, "first person"),
        ("English", 5, "ShortAnswer", "What is a synonym for 'benevolent'?", None, None, None, None, "kind"),
        ("English", 5, "ShortAnswer", "What is an antonym for 'bias'?", None, None, None, None, "fairness"),
        ("English", 5, "ShortAnswer", "What is the purpose of a thesis statement?", None, None, None, None, "to state the main argument"),
        ("English", 5, "ShortAnswer", "Name the device: repetition at the start of lines for emphasis.", None, None, None, None, "anaphora"),
        ("English", 5, "ShortAnswer", "What does 'infer' mean?", None, None, None, None, "draw a conclusion from evidence"),
        ("English", 5, "ShortAnswer", "What is a synonym for 'succinct'?", None, None, None, None, "concise"),
        ("English", 6, "ShortAnswer", "Name the technique: placing contrasting ideas side by side.", None, None, None, None, "juxtaposition"),
        ("English", 6, "ShortAnswer", "What is dramatic irony?", None, None, None, None, "when the audience knows something characters do not"),
        ("English", 6, "ShortAnswer", "Name the narrative technique: a story within a story.", None, None, None, None, "frame narrative"),
        ("English", 6, "ShortAnswer", "What does 'connotation' mean?", None, None, None, None, "the implied meaning of a word"),
        ("English", 6, "ShortAnswer", "Name the device: repetition at the end of lines.", None, None, None, None, "epistrophe"),
        ("English", 6, "ShortAnswer", "What is an unreliable narrator?", None, None, None, None, "a narrator whose account cannot be fully trusted"),
        ("English", 6, "ShortAnswer", "What does 'syntax' refer to?", None, None, None, None, "the arrangement of words in a sentence"),
        ("English", 6, "ShortAnswer", "Name the mood: 'If I were the president, I would change the law.'", None, None, None, None, "subjunctive"),
        ("English", 6, "ShortAnswer", "What is a synonym for 'evocative'?", None, None, None, None, "expressive"),
        ("English", 6, "ShortAnswer", "What is a discursive essay?", None, None, None, None, "an essay that explores different viewpoints"),
        ("English", 6, "ShortAnswer", "Name the literary device: a written description of a visual artwork.", None, None, None, None, "ekphrasis"),
        ("English", 6, "ShortAnswer", "What is the denotation of a word?", None, None, None, None, "its literal dictionary meaning"),
        # CHINESE ShortAnswer
        ("Chinese", 1, "ShortAnswer", "What does '你好' mean in English?", None, None, None, None, "hello"),
        ("Chinese", 1, "ShortAnswer", "What does '谢谢' mean in English?", None, None, None, None, "thank you"),
        ("Chinese", 1, "ShortAnswer", "What does '再见' mean in English?", None, None, None, None, "goodbye"),
        ("Chinese", 1, "ShortAnswer", "What does '水' mean in English?", None, None, None, None, "water"),
        ("Chinese", 1, "ShortAnswer", "What does '大' mean in English?", None, None, None, None, "big"),
        ("Chinese", 1, "ShortAnswer", "What does '小' mean in English?", None, None, None, None, "small"),
        ("Chinese", 1, "ShortAnswer", "How do you write the number 5 in Chinese characters?", None, None, None, None, "五"),
        ("Chinese", 1, "ShortAnswer", "What does '家' mean in English?", None, None, None, None, "home"),
        ("Chinese", 1, "ShortAnswer", "How do you say 'mother' in Chinese?", None, None, None, None, "妈妈"),
        ("Chinese", 1, "ShortAnswer", "How do you say 'father' in Chinese?", None, None, None, None, "爸爸"),
        ("Chinese", 1, "ShortAnswer", "What does '好' mean in English?", None, None, None, None, "good"),
        ("Chinese", 1, "ShortAnswer", "What does '开心' mean in English?", None, None, None, None, "happy"),
        ("Chinese", 2, "ShortAnswer", "What does '学校' mean in English?", None, None, None, None, "school"),
        ("Chinese", 2, "ShortAnswer", "What does '今天' mean in English?", None, None, None, None, "today"),
        ("Chinese", 2, "ShortAnswer", "What does '书' mean in English?", None, None, None, None, "book"),
        ("Chinese", 2, "ShortAnswer", "What does '颜色' mean in English?", None, None, None, None, "colour"),
        ("Chinese", 2, "ShortAnswer", "What does '下雨' mean in English?", None, None, None, None, "raining"),
        ("Chinese", 2, "ShortAnswer", "What does '生日' mean in English?", None, None, None, None, "birthday"),
        ("Chinese", 2, "ShortAnswer", "What does '高兴' mean in English?", None, None, None, None, "happy"),
        ("Chinese", 2, "ShortAnswer", "What does '图书馆' mean in English?", None, None, None, None, "library"),
        ("Chinese", 2, "ShortAnswer", "What does '弟弟' mean in English?", None, None, None, None, "younger brother"),
        ("Chinese", 2, "ShortAnswer", "What does '超市' mean in English?", None, None, None, None, "supermarket"),
        ("Chinese", 2, "ShortAnswer", "What does '快' mean in English?", None, None, None, None, "fast"),
        ("Chinese", 2, "ShortAnswer", "How do you say Monday in Chinese?", None, None, None, None, "星期一"),
        ("Chinese", 3, "ShortAnswer", "What does '朋友' mean in English?", None, None, None, None, "friend"),
        ("Chinese", 3, "ShortAnswer", "What does '天气' mean in English?", None, None, None, None, "weather"),
        ("Chinese", 3, "ShortAnswer", "What does '分享' mean in English?", None, None, None, None, "share"),
        ("Chinese", 3, "ShortAnswer", "What does '节约' mean in English?", None, None, None, None, "save"),
        ("Chinese", 3, "ShortAnswer", "What does '努力' mean in English?", None, None, None, None, "work hard"),
        ("Chinese", 3, "ShortAnswer", "What does '安全' mean in English?", None, None, None, None, "safe"),
        ("Chinese", 3, "ShortAnswer", "What does '有趣' mean in English?", None, None, None, None, "interesting"),
        ("Chinese", 3, "ShortAnswer", "What does '健康' mean in English?", None, None, None, None, "healthy"),
        ("Chinese", 3, "ShortAnswer", "What does '希望' mean in English?", None, None, None, None, "hope"),
        ("Chinese", 3, "ShortAnswer", "What does '互相帮助' mean in English?", None, None, None, None, "help each other"),
        ("Chinese", 3, "ShortAnswer", "What does '保护' mean in English?", None, None, None, None, "protect"),
        ("Chinese", 3, "ShortAnswer", "What does '勤劳' mean in English?", None, None, None, None, "hardworking"),
        ("Chinese", 4, "ShortAnswer", "What does '责任' mean in English?", None, None, None, None, "responsibility"),
        ("Chinese", 4, "ShortAnswer", "What does '合作' mean in English?", None, None, None, None, "cooperation"),
        ("Chinese", 4, "ShortAnswer", "What does '进步' mean in English?", None, None, None, None, "progress"),
        ("Chinese", 4, "ShortAnswer", "What does '污染' mean in English?", None, None, None, None, "pollution"),
        ("Chinese", 4, "ShortAnswer", "What does '传统' mean in English?", None, None, None, None, "traditional"),
        ("Chinese", 4, "ShortAnswer", "What does '诚实' mean in English?", None, None, None, None, "honest"),
        ("Chinese", 4, "ShortAnswer", "What does '鼓励' mean in English?", None, None, None, None, "encourage"),
        ("Chinese", 4, "ShortAnswer", "What does '影响' mean in English?", None, None, None, None, "influence"),
        ("Chinese", 4, "ShortAnswer", "What does '解决' mean in English?", None, None, None, None, "solve"),
        ("Chinese", 4, "ShortAnswer", "What does '挑战' mean in English?", None, None, None, None, "challenge"),
        ("Chinese", 4, "ShortAnswer", "What does '关心' mean in English?", None, None, None, None, "care for"),
        ("Chinese", 4, "ShortAnswer", "What does '重要' mean in English?", None, None, None, None, "important"),
        ("Chinese", 5, "ShortAnswer", "What does the chengyu '一石二鸟' mean in English?", None, None, None, None, "kill two birds with one stone"),
        ("Chinese", 5, "ShortAnswer", "What does '坚持' mean in English?", None, None, None, None, "persevere"),
        ("Chinese", 5, "ShortAnswer", "What does '感恩' mean in English?", None, None, None, None, "grateful"),
        ("Chinese", 5, "ShortAnswer", "What does the chengyu '专心致志' mean in English?", None, None, None, None, "focus wholeheartedly"),
        ("Chinese", 5, "ShortAnswer", "What does '值得' mean in English?", None, None, None, None, "worth it"),
        ("Chinese", 5, "ShortAnswer", "What is '比喻' in English?", None, None, None, None, "metaphor"),
        ("Chinese", 5, "ShortAnswer", "What does '启示' mean in English?", None, None, None, None, "inspiration"),
        ("Chinese", 5, "ShortAnswer", "What does the chengyu '亡羊补牢' mean in English?", None, None, None, None, "better late than never"),
        ("Chinese", 5, "ShortAnswer", "What does '夸张' mean as a writing device?", None, None, None, None, "exaggeration"),
        ("Chinese", 5, "ShortAnswer", "What does '排比' mean in Chinese writing?", None, None, None, None, "parallel structures"),
        ("Chinese", 5, "ShortAnswer", "What does '反问' mean in Chinese writing?", None, None, None, None, "rhetorical question"),
        ("Chinese", 5, "ShortAnswer", "What does the chengyu '画蛇添足' mean in English?", None, None, None, None, "do something unnecessary"),
        ("Chinese", 6, "ShortAnswer", "What does '承上启下' mean as a paragraph function?", None, None, None, None, "connect previous and next paragraphs"),
        ("Chinese", 6, "ShortAnswer", "What does '感悟' mean in English?", None, None, None, None, "personal insight"),
        ("Chinese", 6, "ShortAnswer", "What does '对比' mean as a writing technique?", None, None, None, None, "contrast"),
        ("Chinese", 6, "ShortAnswer", "What does the chengyu '百折不挠' mean in English?", None, None, None, None, "never give up despite setbacks"),
        ("Chinese", 6, "ShortAnswer", "What does '倒叙' mean as a narrative technique?", None, None, None, None, "starting at the end and flashing back"),
        ("Chinese", 6, "ShortAnswer", "What does '点题' mean in an essay?", None, None, None, None, "refer back to the main theme"),
        ("Chinese", 6, "ShortAnswer", "What does '升华主题' mean in Chinese essay writing?", None, None, None, None, "elevate and deepen the theme"),
        ("Chinese", 6, "ShortAnswer", "What does the chengyu '功亏一篑' mean in English?", None, None, None, None, "fail at the last step"),
        ("Chinese", 6, "ShortAnswer", "What does '首尾呼应' mean in essay writing?", None, None, None, None, "the ending echoes the opening"),
        ("Chinese", 6, "ShortAnswer", "What does '正面描写' mean?", None, None, None, None, "direct description"),
        ("Chinese", 6, "ShortAnswer", "What does the chengyu '胸有成竹' mean in English?", None, None, None, None, "have a plan fully formed before acting"),
        ("Chinese", 6, "ShortAnswer", "What does '开门见山' mean in Chinese writing?", None, None, None, None, "immediately state the main point"),
        # ART ShortAnswer
        ("Art", 1, "ShortAnswer", "Name the three primary colours.", None, None, None, None, "red, yellow, blue"),
        ("Art", 1, "ShortAnswer", "What colour do red and blue make?", None, None, None, None, "purple"),
        ("Art", 1, "ShortAnswer", "What colour do yellow and blue make?", None, None, None, None, "green"),
        ("Art", 1, "ShortAnswer", "What colour do red and yellow make?", None, None, None, None, "orange"),
        ("Art", 1, "ShortAnswer", "Name a tool used to apply paint.", None, None, None, None, "paintbrush"),
        ("Art", 1, "ShortAnswer", "What do you call a drawing of yourself?", None, None, None, None, "self-portrait"),
        ("Art", 1, "ShortAnswer", "What is black and white mixed together?", None, None, None, None, "grey"),
        ("Art", 1, "ShortAnswer", "Name one cool colour.", None, None, None, None, "blue"),
        ("Art", 1, "ShortAnswer", "Name one warm colour.", None, None, None, None, "red"),
        ("Art", 1, "ShortAnswer", "What shape has no corners?", None, None, None, None, "circle"),
        ("Art", 1, "ShortAnswer", "What do we call art made from cut and pasted pieces?", None, None, None, None, "collage"),
        ("Art", 1, "ShortAnswer", "What colour do you get mixing white and red?", None, None, None, None, "pink"),
        ("Art", 2, "ShortAnswer", "Name the three secondary colours.", None, None, None, None, "orange, green, purple"),
        ("Art", 2, "ShortAnswer", "What does 'portrait' mean in art?", None, None, None, None, "a picture of a person"),
        ("Art", 2, "ShortAnswer", "Name the type of art made from small pieces of tiles or glass.", None, None, None, None, "mosaic"),
        ("Art", 2, "ShortAnswer", "What does 'foreground' mean in a picture?", None, None, None, None, "the area at the front"),
        ("Art", 2, "ShortAnswer", "Name the technique of making parallel lines to show shadow.", None, None, None, None, "hatching"),
        ("Art", 2, "ShortAnswer", "What do we call art made from clay?", None, None, None, None, "pottery"),
        ("Art", 2, "ShortAnswer", "What is 'mixed media' art?", None, None, None, None, "art using more than one material"),
        ("Art", 2, "ShortAnswer", "Name the element in art that describes how a surface looks or feels.", None, None, None, None, "texture"),
        ("Art", 2, "ShortAnswer", "What does 'pattern' mean in art?", None, None, None, None, "a repeated design"),
        ("Art", 2, "ShortAnswer", "Name the cool colour made by mixing blue and red.", None, None, None, None, "purple"),
        ("Art", 2, "ShortAnswer", "What does 'overlap' mean in art?", None, None, None, None, "one shape covers part of another"),
        ("Art", 2, "ShortAnswer", "What is a 'horizon line' in drawing?", None, None, None, None, "where the sky meets the ground"),
        ("Art", 3, "ShortAnswer", "Who painted the Mona Lisa?", None, None, None, None, "Leonardo da Vinci"),
        ("Art", 3, "ShortAnswer", "Who painted Starry Night?", None, None, None, None, "Vincent van Gogh"),
        ("Art", 3, "ShortAnswer", "What does 'value' mean in art?", None, None, None, None, "the lightness or darkness of a colour"),
        ("Art", 3, "ShortAnswer", "What does 'composition' mean in art?", None, None, None, None, "how elements are arranged in an artwork"),
        ("Art", 3, "ShortAnswer", "Name the colours made by mixing a primary and secondary colour.", None, None, None, None, "tertiary colours"),
        ("Art", 3, "ShortAnswer", "What is a 'silhouette'?", None, None, None, None, "a dark outline shape against a lighter background"),
        ("Art", 3, "ShortAnswer", "What does 'proportion' mean in art?", None, None, None, None, "the size relationship between parts of an artwork"),
        ("Art", 3, "ShortAnswer", "Name the technique of using criss-crossing lines for tone.", None, None, None, None, "cross-hatching"),
        ("Art", 3, "ShortAnswer", "What is batik?", None, None, None, None, "fabric art using wax and dye"),
        ("Art", 3, "ShortAnswer", "What is a 'mural'?", None, None, None, None, "art painted on a wall"),
        ("Art", 3, "ShortAnswer", "What does 'emphasis' mean in art?", None, None, None, None, "making one part stand out as the focus"),
        ("Art", 3, "ShortAnswer", "What does 'balance' mean in art?", None, None, None, None, "visual weight is evenly distributed"),
        ("Art", 4, "ShortAnswer", "Name the artist famous for Starry Night.", None, None, None, None, "Vincent van Gogh"),
        ("Art", 4, "ShortAnswer", "What does 'perspective' mean in art?", None, None, None, None, "creating a sense of depth and distance"),
        ("Art", 4, "ShortAnswer", "What is a 'vanishing point'?", None, None, None, None, "the point where parallel lines appear to meet on the horizon"),
        ("Art", 4, "ShortAnswer", "What is a 'tint'?", None, None, None, None, "a colour mixed with white"),
        ("Art", 4, "ShortAnswer", "What is a 'shade'?", None, None, None, None, "a colour mixed with black"),
        ("Art", 4, "ShortAnswer", "Name the art movement Pablo Picasso is associated with.", None, None, None, None, "Cubism"),
        ("Art", 4, "ShortAnswer", "What does 'monochromatic' mean?", None, None, None, None, "using one colour and its tints and shades"),
        ("Art", 4, "ShortAnswer", "What does 'focal point' mean in an artwork?", None, None, None, None, "the main area that attracts the viewer's attention"),
        ("Art", 4, "ShortAnswer", "What is 'impasto'?", None, None, None, None, "thick application of paint"),
        ("Art", 4, "ShortAnswer", "What is 'screen printing'?", None, None, None, None, "pushing ink through a mesh screen"),
        ("Art", 4, "ShortAnswer", "What does 'contrast' mean in art?", None, None, None, None, "strong differences between elements"),
        ("Art", 4, "ShortAnswer", "What is 'symmetry' in art?", None, None, None, None, "both sides look the same when folded"),
        ("Art", 5, "ShortAnswer", "What does 'abstract art' mean?", None, None, None, None, "art that uses shapes and colours to express ideas, not realistic images"),
        ("Art", 5, "ShortAnswer", "What are 'complementary colours'?", None, None, None, None, "colours opposite each other on the colour wheel"),
        ("Art", 5, "ShortAnswer", "What is 'printmaking'?", None, None, None, None, "creating images by pressing inked surfaces onto paper"),
        ("Art", 5, "ShortAnswer", "What does 'saturation' mean in colour theory?", None, None, None, None, "the intensity or purity of a colour"),
        ("Art", 5, "ShortAnswer", "What is 'surrealism'?", None, None, None, None, "art that explores the unconscious mind and dreamlike imagery"),
        ("Art", 5, "ShortAnswer", "What does 'atmospheric perspective' mean?", None, None, None, None, "objects in the distance appear lighter and less detailed"),
        ("Art", 5, "ShortAnswer", "What is a 'triptych'?", None, None, None, None, "an artwork in three panels"),
        ("Art", 5, "ShortAnswer", "What does 'hue' mean in colour theory?", None, None, None, None, "the pure colour itself"),
        ("Art", 5, "ShortAnswer", "What is 'plein air' painting?", None, None, None, None, "painting outdoors directly from nature"),
        ("Art", 5, "ShortAnswer", "What is 'linocut' printing?", None, None, None, None, "carving a design into linoleum and printing from it"),
        ("Art", 5, "ShortAnswer", "What is 'typography' in design?", None, None, None, None, "the art and style of arranging text"),
        ("Art", 5, "ShortAnswer", "What is 'installation art'?", None, None, None, None, "art that transforms a space using various materials"),
        ("Art", 6, "ShortAnswer", "What is 'chiaroscuro'?", None, None, None, None, "the use of strong contrasts of light and dark in art"),
        ("Art", 6, "ShortAnswer", "Name the artist known for soup can paintings.", None, None, None, None, "Andy Warhol"),
        ("Art", 6, "ShortAnswer", "What is 'impressionism'?", None, None, None, None, "capturing light and movement with loose brushstrokes"),
        ("Art", 6, "ShortAnswer", "What is 'negative space' in art?", None, None, None, None, "the space around and between the subjects"),
        ("Art", 6, "ShortAnswer", "Name the technique using small dots of colour to create an image.", None, None, None, None, "pointillism"),
        ("Art", 6, "ShortAnswer", "What is 'colour harmony'?", None, None, None, None, "pleasing combinations of colours that work well together"),
        ("Art", 6, "ShortAnswer", "What is 'photorealism'?", None, None, None, None, "painting or drawing that looks as realistic as a photograph"),
        ("Art", 6, "ShortAnswer", "What is 'kinetic art'?", None, None, None, None, "art that moves or gives the illusion of movement"),
        ("Art", 6, "ShortAnswer", "What is 'sgraffito'?", None, None, None, None, "scratching through a top layer to reveal a different colour beneath"),
        ("Art", 6, "ShortAnswer", "What does 'semiotics' mean in art and design?", None, None, None, None, "the study of signs and symbols and their meaning"),
        ("Art", 6, "ShortAnswer", "What is 'site-specific art'?", None, None, None, None, "art created for and responding to a particular location"),
        ("Art", 6, "ShortAnswer", "What is 'colour temperature' in art?", None, None, None, None, "warm vs cool colours and their emotional effect"),
    ]
    c.executemany(
        "INSERT INTO questions (subject, level, section, question, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?,?,?,?)",
        short_answer
    )

    # ProblemSum questions: (subject, level, section, question, None, None, None, None, answer)
    problem_sums = [
        # MATH P1 ProblemSum
        ("Math", 1, "ProblemSum", "Ali has 5 apples. He buys 8 more. How many apples does he have now?", None, None, None, None, "13"),
        ("Math", 1, "ProblemSum", "There are 12 birds on a tree. 4 fly away. How many birds are left?", None, None, None, None, "8"),
        ("Math", 1, "ProblemSum", "Mary has 3 bags. Each bag has 4 sweets. How many sweets does she have in total?", None, None, None, None, "12"),
        ("Math", 1, "ProblemSum", "Tom has 20 stickers. He gives 7 to his friend. How many stickers does Tom have left?", None, None, None, None, "13"),
        ("Math", 1, "ProblemSum", "There are 6 boxes. Each box holds 3 books. How many books are there altogether?", None, None, None, None, "18"),
        ("Math", 1, "ProblemSum", "Lily has 15 marbles. She wins 6 more. How many marbles does she have?", None, None, None, None, "21"),
        ("Math", 1, "ProblemSum", "Sam has 24 crayons. He shares them equally into 4 boxes. How many crayons are in each box?", None, None, None, None, "6"),
        ("Math", 1, "ProblemSum", "A bag has 10 red balls and 8 blue balls. How many balls are there altogether?", None, None, None, None, "18"),
        ("Math", 1, "ProblemSum", "There are 30 pupils in a class. 12 are boys. How many are girls?", None, None, None, None, "18"),
        ("Math", 1, "ProblemSum", "Ben has 5 packs of biscuits. Each pack has 6 biscuits. How many biscuits does he have?", None, None, None, None, "30"),
        ("Math", 1, "ProblemSum", "There are 16 flowers. They are put into vases of 4. How many vases are there?", None, None, None, None, "4"),
        ("Math", 1, "ProblemSum", "A shop sells 9 pens in the morning and 11 pens in the afternoon. How many pens are sold in total?", None, None, None, None, "20"),
        # MATH P2 ProblemSum
        ("Math", 2, "ProblemSum", "Mrs Tan bought 3 boxes of cookies. Each box had 24 cookies. She ate 15 cookies. How many cookies did she have left?", None, None, None, None, "57"),
        ("Math", 2, "ProblemSum", "A shop had 150 oranges. They sold 87 and received 60 more. How many oranges does the shop have now?", None, None, None, None, "123"),
        ("Math", 2, "ProblemSum", "John has $45. He spends $18 on a book and $12 on a pen. How much money does he have left?", None, None, None, None, "15"),
        ("Math", 2, "ProblemSum", "A farmer has 9 rows of plants. Each row has 12 plants. How many plants does the farmer have?", None, None, None, None, "108"),
        ("Math", 2, "ProblemSum", "There are 56 chairs to be arranged into rows of 7. How many rows are there?", None, None, None, None, "8"),
        ("Math", 2, "ProblemSum", "Aisha saved $35 in January and $48 in February. How much did she save altogether?", None, None, None, None, "83"),
        ("Math", 2, "ProblemSum", "A box has 120 eggs. 34 eggs are broken. How many eggs are not broken?", None, None, None, None, "86"),
        ("Math", 2, "ProblemSum", "There are 8 teams. Each team has 11 players. How many players are there altogether?", None, None, None, None, "88"),
        ("Math", 2, "ProblemSum", "A book has 200 pages. Raju reads 75 pages. How many pages are left to read?", None, None, None, None, "125"),
        ("Math", 2, "ProblemSum", "There are 96 students going on a trip. Each bus holds 32 students. How many buses are needed?", None, None, None, None, "3"),
        ("Math", 2, "ProblemSum", "Ming had 68 stamps. He gave 29 to his sister. How many stamps does he have left?", None, None, None, None, "39"),
        ("Math", 2, "ProblemSum", "A toy costs $15. Wei buys 6 of the same toy. How much does he spend?", None, None, None, None, "90"),
        # MATH P3 ProblemSum
        ("Math", 3, "ProblemSum", "A bookshop sold 345 books on Saturday and 289 books on Sunday. How many books were sold over the weekend?", None, None, None, None, "634"),
        ("Math", 3, "ProblemSum", "Siti has $500. She buys a dress for $185 and a bag for $126. How much money does she have left?", None, None, None, None, "189"),
        ("Math", 3, "ProblemSum", "A ribbon is 360 cm long. It is cut into 8 equal pieces. How long is each piece?", None, None, None, None, "45"),
        ("Math", 3, "ProblemSum", "A rectangular garden is 15 m long and 8 m wide. What is its perimeter?", None, None, None, None, "46"),
        ("Math", 3, "ProblemSum", "A school has 560 pupils. 3/4 of them are girls. How many girls are there?", None, None, None, None, "420"),
        ("Math", 3, "ProblemSum", "There are 48 chocolates in a box. 3 friends share them equally. How many chocolates does each friend get?", None, None, None, None, "16"),
        ("Math", 3, "ProblemSum", "A bag of rice weighs 5 kg. A shopkeeper has 24 such bags. What is the total weight?", None, None, None, None, "120"),
        ("Math", 3, "ProblemSum", "A square has a perimeter of 52 cm. What is the length of each side?", None, None, None, None, "13"),
        ("Math", 3, "ProblemSum", "There are 720 students in a school. 2/5 of them wear glasses. How many students wear glasses?", None, None, None, None, "288"),
        ("Math", 3, "ProblemSum", "A shop sells T-shirts for $12 each. If 35 T-shirts are sold, how much money does the shop collect?", None, None, None, None, "420"),
        ("Math", 3, "ProblemSum", "A water tank has 900 litres. 375 litres are used. How many litres are left?", None, None, None, None, "525"),
        ("Math", 3, "ProblemSum", "A rectangular playground is 25 m by 18 m. What is its area?", None, None, None, None, "450"),
        # MATH P4 ProblemSum
        ("Math", 4, "ProblemSum", "A shop sold 480 items in 4 days. The same number were sold each day. How many items were sold per day?", None, None, None, None, "120"),
        ("Math", 4, "ProblemSum", "Tom saves $1250 a month. How much does he save in 8 months?", None, None, None, None, "10000"),
        ("Math", 4, "ProblemSum", "A jacket costs $96. A 25% discount is given. What is the discounted price?", None, None, None, None, "72"),
        ("Math", 4, "ProblemSum", "A rectangle has a length of 14 cm and width of 9 cm. What is its area?", None, None, None, None, "126"),
        ("Math", 4, "ProblemSum", "There are 840 pupils in a school. 35% are in the lower primary. How many pupils are in the lower primary?", None, None, None, None, "294"),
        ("Math", 4, "ProblemSum", "Ali has 3/5 of a pizza. He eats 1/5. What fraction of the pizza is left?", None, None, None, None, "2/5"),
        ("Math", 4, "ProblemSum", "A car travels 120 km in 2 hours. What is its speed?", None, None, None, None, "60"),
        ("Math", 4, "ProblemSum", "A bucket holds 18 litres. How many buckets are needed to fill a tank of 252 litres?", None, None, None, None, "14"),
        ("Math", 4, "ProblemSum", "The ratio of boys to girls in a class is 3:5. There are 24 boys. How many girls are there?", None, None, None, None, "40"),
        ("Math", 4, "ProblemSum", "Sarah bought 4 pens at $2.50 each and 3 notebooks at $3.80 each. How much did she spend altogether?", None, None, None, None, "21.40"),
        ("Math", 4, "ProblemSum", "A cloth is 7.5 m long. It is cut into pieces of 0.5 m each. How many pieces are there?", None, None, None, None, "15"),
        ("Math", 4, "ProblemSum", "A triangle has a base of 16 cm and a height of 9 cm. What is its area?", None, None, None, None, "72"),
        # MATH P5 ProblemSum
        ("Math", 5, "ProblemSum", "A train travels at 80 km/h. How far does it travel in 3.5 hours?", None, None, None, None, "280"),
        ("Math", 5, "ProblemSum", "The ratio of adults to children at a party is 2:3. There are 18 adults. How many people are at the party altogether?", None, None, None, None, "45"),
        ("Math", 5, "ProblemSum", "A shopkeeper bought 200 kg of rice at $1.50 per kg and sold it at $2.10 per kg. What was the total profit?", None, None, None, None, "120"),
        ("Math", 5, "ProblemSum", "25% of a number is 75. What is the number?", None, None, None, None, "300"),
        ("Math", 5, "ProblemSum", "A cylinder has a radius of 7 cm and height of 10 cm. What is its volume? (π = 22/7)", None, None, None, None, "1540"),
        ("Math", 5, "ProblemSum", "A rectangle has perimeter 54 cm. Its length is 16 cm. What is its area?", None, None, None, None, "176"),
        ("Math", 5, "ProblemSum", "The average score of 5 students is 82. The total score of 4 of them is 320. What is the fifth student's score?", None, None, None, None, "90"),
        ("Math", 5, "ProblemSum", "A car uses 8 litres of petrol per 100 km. How many litres are needed to travel 375 km?", None, None, None, None, "30"),
        ("Math", 5, "ProblemSum", "There are 120 red and blue balls in a bag. 40% are red. How many blue balls are there?", None, None, None, None, "72"),
        ("Math", 5, "ProblemSum", "A vendor bought 150 items at $4 each and sold them at $7 each. Find his total profit.", None, None, None, None, "450"),
        ("Math", 5, "ProblemSum", "If 3 workers can complete a job in 12 days, how many days will 6 workers take?", None, None, None, None, "6"),
        ("Math", 5, "ProblemSum", "A circle has a circumference of 88 cm. What is its radius? (π = 22/7)", None, None, None, None, "14"),
        # MATH P6 ProblemSum
        ("Math", 6, "ProblemSum", "Peter spent 40% of his money and gave 25% of the remainder to charity. He had $270 left. How much did he start with?", None, None, None, None, "600"),
        ("Math", 6, "ProblemSum", "A shopkeeper sold a bag for $144 making a 20% profit. What was the cost price?", None, None, None, None, "120"),
        ("Math", 6, "ProblemSum", "The ratio of Amy's savings to Ben's savings is 5:3. Amy has $250 more than Ben. How much does Amy have?", None, None, None, None, "625"),
        ("Math", 6, "ProblemSum", "A tap fills a tank at 12 litres per minute. Another empties it at 8 litres per minute. How long to fill a 120-litre tank?", None, None, None, None, "30"),
        ("Math", 6, "ProblemSum", "A train 400 m long passes a pole in 20 seconds. What is its speed in m/s?", None, None, None, None, "20"),
        ("Math", 6, "ProblemSum", "After giving away 1/3 of his marbles, Ahmad had 48 left. How many did he start with?", None, None, None, None, "72"),
        ("Math", 6, "ProblemSum", "Three numbers are in the ratio 2:3:5. Their sum is 400. What is the largest number?", None, None, None, None, "200"),
        ("Math", 6, "ProblemSum", "A square has a perimeter of 64 cm. What is its area?", None, None, None, None, "256"),
        ("Math", 6, "ProblemSum", "A shopkeeper buys 80 items for $600 and sells each for $9. How much profit does he make?", None, None, None, None, "120"),
        ("Math", 6, "ProblemSum", "The average of 6 numbers is 15. When one number is removed the average becomes 13. What number was removed?", None, None, None, None, "25"),
        ("Math", 6, "ProblemSum", "A rectangular tank 50 cm by 40 cm by 30 cm is 3/4 full. How many litres of water does it contain?", None, None, None, None, "45"),
        ("Math", 6, "ProblemSum", "Jane is 3 times as old as her brother. In 5 years she will be twice his age. How old is Jane now?", None, None, None, None, "15"),
        # SCIENCE ProblemSum (experiment/reasoning type)
        ("Science", 3, "ProblemSum", "A plant is placed in a dark room for 3 days. It is then moved to sunlight. What gas will it start producing during the day?", None, None, None, None, "oxygen"),
        ("Science", 3, "ProblemSum", "A circuit has a bulb and a switch. The switch is open. Does the bulb light up? Answer yes or no.", None, None, None, None, "no"),
        ("Science", 3, "ProblemSum", "A magnet attracts a paper clip. The paper clip is then brought near another paper clip. Does the second clip get attracted? Yes or no.", None, None, None, None, "yes"),
        ("Science", 4, "ProblemSum", "A ball is dropped from rest. After 3 seconds it hits the ground. What type of energy does it have just before hitting the ground?", None, None, None, None, "kinetic energy"),
        ("Science", 4, "ProblemSum", "A solution has pH 3. Is it an acid, base or neutral?", None, None, None, None, "acid"),
        ("Science", 4, "ProblemSum", "Water is heated from 20°C to 100°C. By how many degrees Celsius does it increase?", None, None, None, None, "80"),
        ("Science", 5, "ProblemSum", "A car travels 240 km in 3 hours. What is its speed in km/h?", None, None, None, None, "80"),
        ("Science", 5, "ProblemSum", "A plant produces 12 units of glucose in 1 hour of sunlight. How many units does it produce in 4 hours?", None, None, None, None, "48"),
        ("Science", 5, "ProblemSum", "A spring stretches 5 cm for every 10 N of force. How much does it stretch for 30 N?", None, None, None, None, "15"),
        ("Science", 6, "ProblemSum", "A force of 40 N acts on an area of 8 m². What is the pressure?", None, None, None, None, "5"),
        ("Science", 6, "ProblemSum", "An object has a mass of 5 kg and acceleration of 3 m/s². What is the force acting on it?", None, None, None, None, "15"),
        ("Science", 6, "ProblemSum", "A lamp converts 200 J of electrical energy. 80 J is given out as light. How many joules are wasted as heat?", None, None, None, None, "120"),
        # ENGLISH ProblemSum (comprehension/cloze type)
        ("English", 3, "ProblemSum", "Fill in the blank: The dog ran ___ the fence and into the garden. (preposition showing movement over)", None, None, None, None, "over"),
        ("English", 3, "ProblemSum", "Fill in the blank: Neither the teacher nor the students ___ ready for the test. (was/were)", None, None, None, None, "were"),
        ("English", 4, "ProblemSum", "Rewrite in passive voice: 'The chef cooked the meal.' The meal ___ by the chef.", None, None, None, None, "was cooked"),
        ("English", 4, "ProblemSum", "Fill in the blank: If I ___ you, I would study harder. (was/were)", None, None, None, None, "were"),
        ("English", 4, "ProblemSum", "Fill in the blank: She has ___ her homework before dinner. (did/done)", None, None, None, None, "done"),
        ("English", 5, "ProblemSum", "Identify the literary device: 'Life is a journey.' (simile/metaphor/personification)", None, None, None, None, "metaphor"),
        ("English", 5, "ProblemSum", "Fill in the blank: The results, ___ well as the process, matter enormously. (as/so/too)", None, None, None, None, "as"),
        ("English", 5, "ProblemSum", "Identify the device: 'The thunder roared and the lightning danced.' (alliteration/personification/simile)", None, None, None, None, "personification"),
        ("English", 6, "ProblemSum", "Fill in the blank: The new policy will affect ___ of the workers. (all/many/most) — only one word.", None, None, None, None, "all"),
        ("English", 6, "ProblemSum", "Identify the tone: 'It was the best of times, it was the worst of times.' (ironic/paradoxical/sarcastic)", None, None, None, None, "paradoxical"),
        ("English", 6, "ProblemSum", "Fill in the blank with the correct form: By next year, she ___ completed the course. (will have/would have)", None, None, None, None, "will have"),
        ("English", 6, "ProblemSum", "Identify the mood: 'I wish I were a bird and could fly away.' (indicative/subjunctive/imperative)", None, None, None, None, "subjunctive"),
        # CHINESE ProblemSum
        ("Chinese", 3, "ProblemSum", "小明有25颗糖果，他给了朋友8颗。他还剩下多少颗糖果？(How many sweets does Xiao Ming have left?)", None, None, None, None, "17"),
        ("Chinese", 3, "ProblemSum", "一本书有120页，小华每天看15页。几天后他才能看完？(How many days to finish the book?)", None, None, None, None, "8"),
        ("Chinese", 4, "ProblemSum", "一个班有40名学生，其中60%是女生。男生有多少人？(How many boys are there?)", None, None, None, None, "16"),
        ("Chinese", 4, "ProblemSum", "小红有$50，她花了$18买文具。她还剩多少钱？(How much money is left?)", None, None, None, None, "32"),
        ("Chinese", 5, "ProblemSum", "一家商店把一件衣服的价格从$80涨到$100。涨幅是百分之几？(What is the percentage increase?)", None, None, None, None, "25"),
        ("Chinese", 5, "ProblemSum", "小华的数学成绩是85分，小明的成绩是92分。两人的平均分是多少？(What is the average score?)", None, None, None, None, "88.5"),
        ("Chinese", 6, "ProblemSum", "甲的钱是乙的3倍。两人共有$240。甲有多少钱？(How much money does A have?)", None, None, None, None, "180"),
        ("Chinese", 6, "ProblemSum", "一辆车以60公里每小时的速度行驶了2.5小时。它行驶了多少公里？(How many km did it travel?)", None, None, None, None, "150"),
        # ART ProblemSum
        ("Art", 3, "ProblemSum", "An artist uses a primary colour mixed with the secondary colour opposite it on the colour wheel. What type of combination is this?", None, None, None, None, "complementary"),
        ("Art", 4, "ProblemSum", "A painting uses red, yellow and orange. What colour temperature does this palette represent?", None, None, None, None, "warm"),
        ("Art", 4, "ProblemSum", "An artist divides their canvas into a 3x3 grid and places the subject at an intersection. What rule are they using?", None, None, None, None, "rule of thirds"),
        ("Art", 5, "ProblemSum", "A painting shows objects in the distance as smaller and lighter with less detail. What technique is this?", None, None, None, None, "atmospheric perspective"),
        ("Art", 5, "ProblemSum", "An artwork is created by pushing ink through a mesh screen onto fabric. What technique is this?", None, None, None, None, "screen printing"),
        ("Art", 6, "ProblemSum", "An artist places a bright red apple next to a dull grey background. What principle makes the apple stand out?", None, None, None, None, "contrast"),
        ("Art", 6, "ProblemSum", "A sculptor carves a design into linoleum and prints from it. What is this technique called?", None, None, None, None, "linocut"),
    ]
    c.executemany(
        "INSERT INTO questions (subject, level, section, question, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?,?,?,?)",
        problem_sums
    )

def _seed_badges(c):
    c.execute("SELECT COUNT(*) FROM badges")
    if c.fetchone()[0] > 0:
        return
    badges = [
        ("Quiz Starter", "Complete your first quiz", "🌟", 0),
        ("Math Whiz", "Score 100% in a Math quiz", "🔢", 0),
        ("Science Star", "Score 100% in a Science quiz", "🔬", 0),
        ("English Expert", "Score 100% in an English quiz", "📚", 0),
        ("Chinese Champion", "Score 100% in a Chinese quiz", "🀄", 0),
        ("Art Ace", "Score 100% in an Art quiz", "🎨", 0),
        ("Streak Master", "Get 5 correct answers in a row", "🔥", 0),
        ("Token Collector", "Earn 100 tokens", "💰", 0),
        ("Cool Avatar", "Unlock a special avatar", "🦊", 50),
        ("Super Avatar", "Unlock the legendary avatar", "🦄", 100),
    ]
    c.executemany("INSERT INTO badges (name, description, icon, token_cost) VALUES (?,?,?,?)", badges)

MINI_GAMES = [
    {"slug": "memory", "name": "Memory Flip", "description": "Match pairs of cards!", "icon": "🃏", "cost": 30},
    {"slug": "scramble", "name": "Word Scramble", "description": "Unscramble the word!", "icon": "🔤", "cost": 20},
    {"slug": "balloon", "name": "Balloon Pop", "description": "Pop the right balloons!", "icon": "🎈", "cost": 25},
    {"slug": "quickmath", "name": "Quick Math", "description": "Solve as many as you can in 30s!", "icon": "➗", "cost": 20},
    {"slug": "simon", "name": "Memory Beats", "description": "Repeat the glowing sequence!", "icon": "🎵", "cost": 35},
    {"slug": "whack", "name": "Mole Whack", "description": "Bonk the moles, dodge the bombs!", "icon": "🐹", "cost": 30},
    {"slug": "oddone", "name": "Odd One Out", "description": "Spot the one that's different!", "icon": "🔍", "cost": 25},
]

AVATARS = [
    {"id": "star", "icon": "⭐", "name": "Star", "cost": 0},
    {"id": "rocket", "icon": "🚀", "name": "Rocket", "cost": 30},
    {"id": "fox", "icon": "🦊", "name": "Fox", "cost": 50},
    {"id": "dragon", "icon": "🐉", "name": "Dragon", "cost": 80},
    {"id": "unicorn", "icon": "🦄", "name": "Unicorn", "cost": 100},
    {"id": "cat", "icon": "🐱", "name": "Kitty", "cost": 20},
    {"id": "panda", "icon": "🐼", "name": "Panda", "cost": 40},
    {"id": "penguin", "icon": "🐧", "name": "Penguin", "cost": 40},
    {"id": "frog", "icon": "🐸", "name": "Froggy", "cost": 30},
    {"id": "owl", "icon": "🦉", "name": "Owl", "cost": 60},
    {"id": "robot", "icon": "🤖", "name": "Robot", "cost": 70},
    {"id": "ghost", "icon": "👻", "name": "Ghost", "cost": 60},
    {"id": "alien", "icon": "👽", "name": "Alien", "cost": 90},
    {"id": "ninja", "icon": "🥷", "name": "Ninja", "cost": 110},
    {"id": "dino", "icon": "🦖", "name": "Dino", "cost": 120},
    {"id": "crown", "icon": "👑", "name": "Royal", "cost": 150},
    {"id": "wizard", "icon": "🧙", "name": "Wizard", "cost": 150},
]

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_pw(password)))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"ok": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already taken"}), 400
    finally:
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                        (data["username"], hash_pw(data["password"]))).fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "Wrong username or password"}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"ok": True})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("dashboard.html", user=user, games=MINI_GAMES, avatars=AVATARS)

@app.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    conn = get_db()
    user = conn.execute("SELECT id, username, tokens, avatar FROM users WHERE id=?", (session["user_id"],)).fetchone()
    badges = conn.execute("""
        SELECT b.* FROM badges b
        JOIN user_badges ub ON b.id = ub.badge_id
        WHERE ub.user_id = ?
    """, (session["user_id"],)).fetchall()
    unlocked = conn.execute("SELECT game_slug FROM unlocked_games WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()
    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "tokens": user["tokens"],
        "avatar": user["avatar"],
        "badges": [dict(b) for b in badges],
        "unlocked_games": [u["game_slug"] for u in unlocked],
    })

@app.route("/api/sections")
def get_sections():
    subject = request.args.get("subject")
    SUBJECT_SECTIONS = {
        "Math": ["MCQ", "ShortAnswer", "ProblemSum"],
        "Science": ["MCQ", "OpenEnded"],
        "English": ["MCQ", "ShortAnswer"],
        "Chinese": ["MCQ", "ShortAnswer"],
        "Art": ["MCQ", "ShortAnswer"],
    }
    sections = SUBJECT_SECTIONS.get(subject, ["MCQ"])
    return jsonify({"sections": sections})

@app.route("/api/questions")
def get_questions():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    subject = request.args.get("subject")
    level = request.args.get("level", type=int)
    section = request.args.get("section", "MCQ")
    conn = get_db()

    # Get user last seen question IDs
    user_row = conn.execute("SELECT last_seen_q_ids FROM users WHERE id=?", (session["user_id"],)).fetchone()
    last_seen = json.loads(user_row["last_seen_q_ids"]) if user_row and user_row["last_seen_q_ids"] else []

    all_qs = conn.execute(
        "SELECT * FROM questions WHERE subject=? AND level=? AND section=?", (subject, level, section)
    ).fetchall()
    all_qs = [dict(q) for q in all_qs]

    # Exclude recently seen questions
    fresh_qs = [q for q in all_qs if q["id"] not in last_seen]
    pool = fresh_qs if len(fresh_qs) >= 5 else all_qs
    random.shuffle(pool)
    selected = pool[:5]

    # Update last_seen_q_ids (keep last 45)
    new_seen = last_seen + [q["id"] for q in selected]
    new_seen = new_seen[-45:]
    conn.execute("UPDATE users SET last_seen_q_ids=? WHERE id=?", (json.dumps(new_seen), session["user_id"]))
    conn.commit()
    conn.close()

    # Build response
    result = []
    for q in selected:
        qd = dict(q)
        if section == "MCQ":
            options = [
                {"key": "A", "text": q["option_a"]},
                {"key": "B", "text": q["option_b"]},
                {"key": "C", "text": q["option_c"]},
                {"key": "D", "text": q["option_d"]},
            ]
            random.shuffle(options)
            qd["options"] = options
            qd["answer_text"] = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}[q["answer"]]
        else:
            qd["options"] = []
            qd["answer_text"] = q["answer"]
        result.append(qd)
    return jsonify(result)

def _normalise(text):
    """Strip whitespace, lowercase, remove currency/unit suffixes for comparison."""
    t = str(text).strip().lower()
    # remove leading $ or trailing units like cm, m, kg, km/h etc
    t = re.sub(r'^\$', '', t)
    t = re.sub(r'\s*(cm[^a-z]?|cm$|m$|kg$|km/h|litres?|degrees?|%)', '', t)
    t = t.strip()
    return t

@app.route("/api/submit_quiz", methods=["POST"])
def submit_quiz():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.json
    subject = data["subject"]
    level = data["level"]
    section = data.get("section", "MCQ")
    answers = data["answers"]  # {question_id: selected_text}
    conn = get_db()
    score = 0
    total = len(answers)
    for qid, selected in answers.items():
        q = conn.execute("SELECT answer, section, option_a, option_b, option_c, option_d FROM questions WHERE id=?", (int(qid),)).fetchone()
        if q:
            sec = q["section"]
            if sec == "MCQ":
                correct_text = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}[q["answer"]]
                if correct_text == selected:
                    score += 1
            else:
                # ShortAnswer / ProblemSum: normalised comparison
                if _normalise(q["answer"]) == _normalise(selected):
                    score += 1

    # Token calculation: 10 per correct + streak bonus
    streak = data.get("streak", 0)
    streak_bonus = 5 if streak >= 5 else 0
    tokens_earned = score * 10 + streak_bonus

    conn.execute("UPDATE users SET tokens = tokens + ? WHERE id=?", (tokens_earned, session["user_id"]))

    conn.execute("INSERT INTO quiz_sessions (user_id, subject, level, score, total, tokens_earned) VALUES (?,?,?,?,?,?)",
                 (session["user_id"], subject, level, score, total, tokens_earned))

    # Check badges
    new_badges = []
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

    def award_badge(name):
        b = conn.execute("SELECT id FROM badges WHERE name=?", (name,)).fetchone()
        if b:
            try:
                conn.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (?,?)", (session["user_id"], b["id"]))
                new_badges.append(name)
            except sqlite3.IntegrityError:
                pass

    # Quiz Starter
    sessions_count = conn.execute("SELECT COUNT(*) FROM quiz_sessions WHERE user_id=?", (session["user_id"],)).fetchone()[0]
    if sessions_count == 1:
        award_badge("Quiz Starter")

    # Perfect score badges
    if score == total and total > 0:
        subject_badge = {"Math": "Math Whiz", "Science": "Science Star", "English": "English Expert",
                         "Chinese": "Chinese Champion", "Art": "Art Ace"}.get(subject)
        if subject_badge:
            award_badge(subject_badge)

    if streak >= 5:
        award_badge("Streak Master")

    if user["tokens"] + tokens_earned >= 100:
        award_badge("Token Collector")

    conn.commit()
    conn.close()
    return jsonify({"score": score, "total": total, "tokens_earned": tokens_earned, "new_badges": new_badges})

@app.route("/api/leaderboard")
def leaderboard():
    conn = get_db()
    rows = conn.execute("SELECT username, tokens, avatar FROM users ORDER BY tokens DESC LIMIT 20").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/shop/unlock_game", methods=["POST"])
def unlock_game():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    slug = request.json.get("slug")
    game = next((g for g in MINI_GAMES if g["slug"] == slug), None)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    conn = get_db()
    user = conn.execute("SELECT tokens FROM users WHERE id=?", (session["user_id"],)).fetchone()
    already = conn.execute("SELECT 1 FROM unlocked_games WHERE user_id=? AND game_slug=?",
                           (session["user_id"], slug)).fetchone()
    if already:
        return jsonify({"error": "Already unlocked"}), 400
    if user["tokens"] < game["cost"]:
        return jsonify({"error": "Not enough tokens"}), 400
    conn.execute("UPDATE users SET tokens = tokens - ? WHERE id=?", (game["cost"], session["user_id"]))
    conn.execute("INSERT INTO unlocked_games (user_id, game_slug) VALUES (?,?)", (session["user_id"], slug))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/shop/unlock_avatar", methods=["POST"])
def unlock_avatar():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    avatar_id = request.json.get("avatar_id")
    avatar = next((a for a in AVATARS if a["id"] == avatar_id), None)
    if not avatar:
        return jsonify({"error": "Avatar not found"}), 404
    conn = get_db()
    user = conn.execute("SELECT tokens, avatar FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if avatar["cost"] > 0 and user["tokens"] < avatar["cost"]:
        return jsonify({"error": "Not enough tokens"}), 400
    conn.execute("UPDATE users SET tokens = tokens - ?, avatar = ? WHERE id=?",
                 (avatar["cost"], avatar_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/games/list")
def games_list():
    return jsonify(MINI_GAMES)

@app.route("/play/<game_slug>")
def play_game(game_slug):
    if "user_id" not in session:
        return redirect(url_for("index"))
    conn = get_db()
    unlocked = conn.execute("SELECT 1 FROM unlocked_games WHERE user_id=? AND game_slug=?",
                            (session["user_id"], game_slug)).fetchone()
    conn.close()
    if not unlocked:
        return redirect(url_for("dashboard"))
    game = next((g for g in MINI_GAMES if g["slug"] == game_slug), None)
    if not game:
        return redirect(url_for("dashboard"))
    return render_template(f"games/{game_slug}.html", game=game)

# Initialise the database on import so it also runs under gunicorn/WSGI.
# init_db() is idempotent (CREATE TABLE IF NOT EXISTS + seed-only-if-empty).
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
