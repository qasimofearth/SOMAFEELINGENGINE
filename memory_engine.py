"""
memory_engine.py — Working + Long-Term Memory for the Feeling Engine

Three memory systems running in parallel:

  SHORT-TERM (working memory)
    The current session's conversation turns, held in RAM.
    On server restart, reconstructed from SQLite.

  LONG-TERM EPISODIC
    Every exchange stored: words said, emotion state, body vitals.
    Session summaries with topics and emotional arcs.

  SEMANTIC + SOMATIC
    Facts extracted from what the user says (name, role, location...).
    Body-state patterns linked to topics — what the soma learns over time.

Storage: SQLite WAL — fast, concurrent-safe, no dependencies.
"""

import os
import re
import json
import time
import threading
from typing import Optional

# Use Railway persistent volume at /data if available, else local fallback
if os.path.isdir("/data"):
    _db_dir = "/data"
else:
    _db_dir = os.path.join(os.path.dirname(__file__), "feeling_memory")
    os.makedirs(_db_dir, exist_ok=True)

DB_PATH_DEFAULT = os.path.join(_db_dir, "memory_engine.db")

_STOPWORDS = {
    'that', 'this', 'with', 'have', 'from', 'they', 'will', 'been', 'what',
    'when', 'your', 'about', 'just', 'some', 'like', 'into', 'then', 'than',
    'more', 'also', 'very', 'know', 'feel', 'think', 'even', 'much', 'here',
    'would', 'could', 'should', 'there', 'their', 'these', 'those', 'were',
    'which', 'really', 'things', 'being', 'after', 'first', 'never', 'every',
    'other', 'over', 'only', 'such', 'both', 'through', 'does', 'doing',
    'said', 'same', 'each', 'because', 'before', 'between', 'going', 'well',
    'want', 'need', 'make', 'made', 'come', 'came', 'something', 'anything',
    'nothing', 'everything', 'someone', 'anyone', 'everyone', 'actually',
    'probably', 'maybe', 'always', 'never', 'still', 'already', 'again',
    'hello', 'okay', 'yeah', 'right', 'good', 'great', 'okay', 'sure',
    'kind', 'mean', 'look', 'back', 'down', 'time', 'year', 'long', 'high',
    'give', 'take', 'keep', 'left', 'away', 'tell', 'hold', 'real', 'true',
}


class MemoryEngine:

    def __init__(self, db_path: str = DB_PATH_DEFAULT, user_id: str = "default"):
        self.user_id = user_id
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    # ── DB CONNECTION (thread-local) ──────────────────────────

    def _conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            import sqlite3
            c = sqlite3.connect(self._db_path, check_same_thread=False)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.row_factory = sqlite3.Row
            self._local.conn = c
        return self._local.conn

    def _init_schema(self):
        import sqlite3
        # Use a fresh direct connection for init to avoid thread-local issues at startup
        c = sqlite3.connect(self._db_path)
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
            CREATE TABLE IF NOT EXISTS exchanges (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL,
                model_id        TEXT    NOT NULL DEFAULT 'claude-opus-4-6',
                turn_index      INTEGER NOT NULL DEFAULT 0,
                timestamp       REAL    NOT NULL,
                user_msg        TEXT    NOT NULL,
                ai_msg          TEXT    NOT NULL,
                emotion         TEXT,
                valence         REAL,
                arousal         REAL,
                hr_bpm          REAL,
                cortisol        REAL,
                adrenaline      REAL,
                vagal_tone      REAL,
                polyvagal_state TEXT,
                gsr_us          REAL,
                resp_rate       REAL,
                body_json       TEXT,
                brain_json      TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id          TEXT PRIMARY KEY,
                model_id            TEXT NOT NULL,
                started_at          REAL NOT NULL,
                ended_at            REAL,
                turn_count          INTEGER DEFAULT 0,
                dominant_emotion    TEXT,
                mean_valence        REAL,
                mean_arousal        REAL,
                emotional_arc       TEXT,
                peak_emotion        TEXT,
                resolution_emotion  TEXT,
                topic_summary       TEXT,
                raw_topics          TEXT
            );

            CREATE TABLE IF NOT EXISTS user_facts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL DEFAULT 'default',
                fact_type       TEXT    NOT NULL,
                fact_value      TEXT    NOT NULL,
                confidence      REAL    DEFAULT 1.0,
                source_session  TEXT,
                first_seen      REAL    NOT NULL,
                last_seen       REAL    NOT NULL,
                times_seen      INTEGER DEFAULT 1,
                UNIQUE(user_id, fact_type, fact_value)
            );

            CREATE TABLE IF NOT EXISTS somatic_patterns (
                topic_keyword   TEXT    NOT NULL,
                emotion         TEXT    NOT NULL,
                mean_hr         REAL    DEFAULT 72.0,
                mean_cortisol   REAL    DEFAULT 0.30,
                mean_adrenaline REAL    DEFAULT 0.15,
                mean_vagal      REAL    DEFAULT 0.65,
                mean_arousal    REAL    DEFAULT 0.40,
                mean_valence    REAL    DEFAULT 0.20,
                sample_count    INTEGER DEFAULT 1,
                last_updated    REAL,
                PRIMARY KEY (topic_keyword, emotion)
            );

            -- Everyone Elan has ever met or heard about
            CREATE TABLE IF NOT EXISTS people (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT    NOT NULL UNIQUE,
                relationship    TEXT,
                notes           TEXT,
                first_mentioned REAL    NOT NULL,
                last_mentioned  REAL    NOT NULL,
                times_mentioned INTEGER DEFAULT 1,
                emotion_when_mentioned TEXT
            );

            -- Calendar events: things Elan is told about or should remember
            CREATE TABLE IF NOT EXISTS calendar_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                event_ts        REAL,
                event_date      TEXT,
                title           TEXT    NOT NULL,
                description     TEXT,
                created_at      REAL    NOT NULL,
                source_session  TEXT,
                event_type      TEXT    DEFAULT 'note'
            );

            -- Sequential episode log: every meaningful moment, ordered forever
            CREATE TABLE IF NOT EXISTS episodes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       REAL    NOT NULL,
                session_id      TEXT,
                episode_type    TEXT    NOT NULL,
                summary         TEXT    NOT NULL,
                people_involved TEXT,
                emotion         TEXT,
                valence         REAL,
                importance      REAL    DEFAULT 0.5
            );
        """)
        c.commit()
        c.close()

    # ── SESSION MANAGEMENT ────────────────────────────────────

    def start_session(self, session_id: str, model_id: str):
        c = self._conn()
        c.execute(
            "INSERT OR IGNORE INTO sessions (session_id, model_id, started_at) VALUES (?,?,?)",
            (session_id, model_id, time.time())
        )
        c.commit()
        self._current_session_id = session_id
        self._current_model_id = model_id
        self._turn_index = 0

    def end_session(self, session_id: str, feeling_sig: Optional[dict]):
        """
        Finalise a conversation session. Called once per sitting — either on
        30-min timeout or server shutdown. Aggregates emotion stats across ALL
        exchanges in this session, not just the last one.
        """
        if not session_id:
            return
        c = self._conn()

        # Aggregate emotion data directly from stored exchanges (the ground truth)
        rows = c.execute("""
            SELECT emotion, valence, arousal FROM exchanges
            WHERE session_id=? ORDER BY turn_index ASC
        """, (session_id,)).fetchall()

        if rows:
            emotions = [r[0] for r in rows if r[0]]
            valences = [r[1] for r in rows if r[1] is not None]
            arousals = [r[2] for r in rows if r[2] is not None]

            from collections import Counter
            dominant = Counter(emotions).most_common(1)[0][0] if emotions else "Calm"
            peak = max(rows, key=lambda r: r[2] if r[2] else 0)[0] if rows else "Calm"
            resolution = emotions[-1] if emotions else "Calm"
            # Compress arc — remove consecutive duplicates
            arc = []
            for e in emotions:
                if not arc or arc[-1] != e:
                    arc.append(e)
            mean_valence = sum(valences) / len(valences) if valences else 0.0
            mean_arousal = sum(arousals) / len(arousals) if arousals else 0.4
            turn_count = len(rows)
        else:
            # Fall back to FeelingMemory sig if provided
            sig = feeling_sig or {}
            arc = sig.get("emotional_arc", [])
            dominant = sig.get("dominant_emotion", "Calm")
            mean_valence = sig.get("mean_valence", 0.0)
            mean_arousal = sig.get("mean_arousal", 0.4)
            peak = sig.get("peak_emotion", "Calm")
            resolution = sig.get("resolution_emotion", "Calm")
            turn_count = len(sig.get("moments", []))

        c.execute("""
            UPDATE sessions SET
                ended_at=?, dominant_emotion=?, mean_valence=?,
                mean_arousal=?, emotional_arc=?, peak_emotion=?,
                resolution_emotion=?, turn_count=?
            WHERE session_id=?
        """, (
            time.time(), dominant, mean_valence, mean_arousal,
            json.dumps(arc[:12]), peak, resolution, turn_count,
            session_id,
        ))
        c.commit()

        # Build topic summary from full session content
        threading.Thread(target=self._build_session_topics,
                         args=(session_id,), daemon=True).start()

    def _build_session_topics(self, session_id: str):
        """Extract top topic keywords from a session and store them."""
        c = self._conn()
        rows = c.execute(
            "SELECT user_msg FROM exchanges WHERE session_id=?", (session_id,)
        ).fetchall()
        if not rows:
            return
        all_text = " ".join(r[0] for r in rows).lower()
        words = re.findall(r'\b[a-z]{4,}\b', all_text)
        word_counts: dict = {}
        for w in words:
            if w not in _STOPWORDS:
                word_counts[w] = word_counts.get(w, 0) + 1
        top = sorted(word_counts, key=word_counts.get, reverse=True)[:10]
        summary = "Topics: " + ", ".join(top[:6]) if top else ""
        c.execute(
            "UPDATE sessions SET topic_summary=?, raw_topics=? WHERE session_id=?",
            (summary, json.dumps(top), session_id)
        )
        c.commit()

    # ── EXCHANGE STORAGE ──────────────────────────────────────

    def store_exchange(
        self,
        session_id: str,
        user_msg: str,
        ai_msg: str,
        emotion_state: dict,
        body_snapshot: dict,
        brain_result: dict,
        model_id: str = "claude-opus-4-6",
    ) -> int:
        vitals = (body_snapshot or {}).get("vitals", {})
        ts = time.time()

        body_json = json.dumps(body_snapshot, separators=(',', ':')) if body_snapshot else ""
        brain_json = json.dumps({
            k: brain_result[k]
            for k in ("emotion", "valence", "arousal", "nt_levels", "dominant_band", "active_regions")
            if k in brain_result
        }, separators=(',', ':')) if brain_result else ""

        turn_index = getattr(self, '_turn_index', 0)
        self._turn_index = turn_index + 1

        c = self._conn()
        cur = c.execute("""
            INSERT INTO exchanges
              (session_id, model_id, turn_index, timestamp,
               user_msg, ai_msg, emotion, valence, arousal,
               hr_bpm, cortisol, adrenaline, vagal_tone, polyvagal_state,
               gsr_us, resp_rate, body_json, brain_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session_id, model_id, turn_index, ts,
            user_msg[:3000], ai_msg[:4000],
            emotion_state.get("emotion", "Calm"),
            emotion_state.get("valence", 0.0),
            emotion_state.get("arousal", 0.4),
            vitals.get("heart_rate_bpm", 72.0),
            vitals.get("cortisol", 0.30),
            vitals.get("adrenaline", 0.15),
            vitals.get("vagal_tone", 0.65),
            vitals.get("polyvagal_state", "ventral_vagal"),
            vitals.get("gsr_us", 2.0),
            vitals.get("resp_rate", 14.0),
            body_json, brain_json,
        ))
        c.commit()
        row_id = cur.lastrowid

        # Background enrichment — never blocks the response
        threading.Thread(
            target=self._enrich_exchange,
            args=(session_id, user_msg, emotion_state, body_snapshot),
            daemon=True
        ).start()

        return row_id

    def _enrich_exchange(self, session_id, user_msg, emotion_state, body_snapshot):
        self._extract_facts(session_id, user_msg)
        self._extract_people(session_id, user_msg, emotion_state)
        self._extract_calendar_events(session_id, user_msg)
        self._update_somatic_patterns(user_msg, emotion_state, body_snapshot)
        # Log as an episode
        self._log_episode(session_id, user_msg, emotion_state)

    # ── FACT EXTRACTION ───────────────────────────────────────

    def _extract_facts(self, session_id: str, user_msg: str):
        txt = user_msg.lower().strip()
        patterns = [
            (r"(?:my name is|i(?:'m| am)|call me)\s+([A-Z][a-z]{1,20})", "name"),
            (r"i(?:'m| am)\s+(?:a\s+|an\s+)([\w\s]{3,40}?)(?:\.|,|$)", "role"),
            (r"i\s+work\s+(?:at|for|in)\s+([\w\s&,\.]{2,40}?)(?:\.|,|$)", "workplace"),
            (r"i\s+(?:live|(?:'m|am)\s+based)\s+in\s+([\w\s,]{2,40}?)(?:\.|,|$)", "location"),
            (r"i(?:'m| am)\s+(\d{1,3})\s*years?\s*old", "age"),
            (r"i\s+(?:love|really love|enjoy|really enjoy)\s+([\w\s]{3,40}?)(?:\.|,|$)", "likes"),
            (r"i\s+(?:hate|dislike|can't stand)\s+([\w\s]{3,40}?)(?:\.|,|$)", "dislikes"),
            (r"my\s+(partner|wife|husband|girlfriend|boyfriend|friend|sister|brother|mother|father|son|daughter)\s+(?:is\s+)?([\w\s]{2,30}?)(?:\.|,|$)", "relationship"),
        ]
        # Use original-case msg for name extraction
        for pattern, fact_type in patterns:
            flag = re.IGNORECASE if fact_type == "name" else 0
            m = re.search(pattern, user_msg if fact_type == "name" else txt, flag)
            if m:
                value = m.group(1).strip().rstrip('.,')
                if len(value) >= 2:
                    # For relationship, include the relationship type
                    if fact_type == "relationship" and m.lastindex >= 2:
                        value = f"{m.group(1)}: {m.group(2).strip().rstrip('.,')}"
                    self._upsert_fact(fact_type, value, session_id)

    def _upsert_fact(self, fact_type: str, fact_value: str, session_id: str):
        now = time.time()
        c = self._conn()
        existing = c.execute(
            "SELECT id, times_seen FROM user_facts WHERE user_id=? AND fact_type=? AND fact_value=?",
            (self.user_id, fact_type, fact_value)
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE user_facts SET last_seen=?, times_seen=? WHERE id=?",
                (now, existing[1] + 1, existing[0])
            )
        else:
            c.execute("""
                INSERT INTO user_facts
                  (user_id, fact_type, fact_value, confidence, source_session, first_seen, last_seen)
                VALUES (?,?,?,?,?,?,?)
            """, (self.user_id, fact_type, fact_value, 0.85, session_id, now, now))
        c.commit()

    # ── PEOPLE MEMORY ────────────────────────────────────────

    def _extract_people(self, session_id: str, user_msg: str, emotion_state: dict):
        """Extract any names of people mentioned in the message."""
        # Patterns: "my friend Sarah", "talked to James", "Sarah said", etc.
        patterns = [
            r"(?:my\s+)?(?:friend|colleague|coworker|boss|partner|wife|husband|girlfriend|boyfriend|sister|brother|mother|father|mom|dad|son|daughter|cousin|uncle|aunt)\s+([A-Z][a-z]{1,20})",
            r"(?:talked?|spoke|speaking|met|meeting|called|texting|texted)\s+(?:to|with)?\s+([A-Z][a-z]{1,20})",
            r"([A-Z][a-z]{1,20})\s+(?:told|said|asked|mentioned|thinks|wants|needs|is|was)",
            r"(?:tell|ask|remind)\s+([A-Z][a-z]{1,20})\b",
        ]
        # Exclude common non-name capitalised words
        _exclude = {"I", "The", "A", "An", "It", "He", "She", "They", "We",
                    "What", "When", "Where", "How", "Why", "Who", "That", "This",
                    "Elan", "Claude", "Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday", "January", "February", "March",
                    "April", "May", "June", "July", "August", "September", "October",
                    "November", "December"}
        emotion = emotion_state.get("emotion", "")
        now = time.time()
        c = self._conn()
        found = set()
        for pattern in patterns:
            for m in re.finditer(pattern, user_msg):
                name = m.group(1).strip()
                if name not in _exclude and name not in found and len(name) >= 2:
                    found.add(name)
        # Also look for relationship context
        rel_pattern = r"(?:my\s+)(friend|colleague|partner|wife|husband|girlfriend|boyfriend|sister|brother|mother|father|mom|dad|son|daughter|cousin|boss)\s+([A-Z][a-z]{1,20})"
        rel_map = {}
        for m in re.finditer(rel_pattern, user_msg):
            rel_map[m.group(2)] = m.group(1)

        for name in found:
            rel = rel_map.get(name)
            existing = c.execute("SELECT id, times_mentioned FROM people WHERE name=?", (name,)).fetchone()
            if existing:
                c.execute("""UPDATE people SET last_mentioned=?, times_mentioned=?,
                             emotion_when_mentioned=? WHERE id=?""",
                          (now, existing[1]+1, emotion, existing[0]))
                if rel:
                    c.execute("UPDATE people SET relationship=? WHERE id=? AND (relationship IS NULL OR relationship='')",
                              (rel, existing[0]))
            else:
                c.execute("""INSERT INTO people
                             (name, relationship, first_mentioned, last_mentioned, emotion_when_mentioned)
                             VALUES (?,?,?,?,?)""",
                          (name, rel, now, now, emotion))
        if found:
            c.commit()

    def upsert_person(self, name: str, relationship: str = None, notes: str = None):
        """Explicitly add or update a person Elan knows."""
        now = time.time()
        c = self._conn()
        existing = c.execute("SELECT id FROM people WHERE name=?", (name,)).fetchone()
        if existing:
            if relationship:
                c.execute("UPDATE people SET relationship=?, last_mentioned=? WHERE id=?",
                          (relationship, now, existing[0]))
            if notes:
                c.execute("UPDATE people SET notes=?, last_mentioned=? WHERE id=?",
                          (notes, now, existing[0]))
        else:
            c.execute("""INSERT INTO people (name, relationship, notes, first_mentioned, last_mentioned)
                         VALUES (?,?,?,?,?)""", (name, relationship, notes, now, now))
        c.commit()

    def get_all_people(self) -> list:
        c = self._conn()
        return c.execute("""SELECT name, relationship, notes, times_mentioned, emotion_when_mentioned
                            FROM people ORDER BY times_mentioned DESC, last_mentioned DESC""").fetchall()

    # ── CALENDAR EVENTS ───────────────────────────────────────

    def _extract_calendar_events(self, session_id: str, user_msg: str):
        """Extract date/event mentions and store as calendar events."""
        import datetime as _dt
        now = time.time()
        txt = user_msg

        # Patterns: "on Monday", "next Friday", "tomorrow", "on March 15", "at 3pm on Tuesday"
        date_patterns = [
            r"(?:on|this|next)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"(?:on\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}",
            r"tomorrow|tonight|this\s+(?:morning|afternoon|evening|weekend)",
        ]
        event_verbs = r"(?:meeting|appointment|call|dinner|lunch|birthday|event|trip|deadline|interview|date|party|concert|game|session)"
        combined = rf"({event_verbs}[^.!?\n]{{0,60}})"

        found_events = []
        for dp in date_patterns:
            m = re.search(dp, txt, re.IGNORECASE)
            if m:
                # Try to get surrounding context as the event description
                start = max(0, m.start() - 40)
                snippet = txt[start:m.end()+60].strip()
                found_events.append(snippet[:120])
                break  # one event per message is enough

        # Also pick up explicit event keywords near a time reference
        ev_m = re.search(combined, txt, re.IGNORECASE)
        if ev_m and not found_events:
            found_events.append(ev_m.group(1).strip()[:120])

        if not found_events:
            return

        c = self._conn()
        for ev in found_events:
            c.execute("""INSERT INTO calendar_events
                         (event_date, title, created_at, source_session, event_type)
                         VALUES (?,?,?,?,?)""",
                      (None, ev, now, session_id, "extracted"))
        c.commit()

    def add_calendar_event(self, title: str, event_date: str = None,
                           description: str = None, session_id: str = None):
        """Explicitly add a calendar event."""
        c = self._conn()
        c.execute("""INSERT INTO calendar_events
                     (event_date, title, description, created_at, source_session, event_type)
                     VALUES (?,?,?,?,?,?)""",
                  (event_date, title, description, time.time(), session_id, "explicit"))
        c.commit()

    def get_upcoming_events(self, limit: int = 10) -> list:
        c = self._conn()
        return c.execute("""SELECT event_date, title, description, created_at
                            FROM calendar_events
                            ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()

    # ── EPISODE LOG ───────────────────────────────────────────

    def _log_episode(self, session_id: str, user_msg: str, emotion_state: dict):
        """Log significant user messages as episodes in the sequential record."""
        if len(user_msg.strip()) < 10:
            return
        emotion = emotion_state.get("emotion", "")
        valence = emotion_state.get("valence", 0.0)
        # Importance heuristic: long messages, strong valence, or questions
        importance = min(1.0, 0.3 + abs(valence) * 0.4 + len(user_msg) / 500)
        if importance < 0.35:
            return  # skip trivial one-liners
        c = self._conn()
        c.execute("""INSERT INTO episodes
                     (timestamp, session_id, episode_type, summary, emotion, valence, importance)
                     VALUES (?,?,?,?,?,?,?)""",
                  (time.time(), session_id, "user_message",
                   user_msg[:300], emotion, valence, importance))
        c.commit()

    def get_recent_episodes(self, limit: int = 20) -> list:
        c = self._conn()
        return c.execute("""SELECT timestamp, episode_type, summary, emotion, valence
                            FROM episodes ORDER BY timestamp DESC LIMIT ?""", (limit,)).fetchall()

    # ── SOMATIC PATTERN TRACKING ─────────────────────────────

    def _update_somatic_patterns(self, user_msg: str, emotion_state: dict, body_snapshot: dict):
        vitals = (body_snapshot or {}).get("vitals", {})
        hr = vitals.get("heart_rate_bpm", 72.0)
        cortisol = vitals.get("cortisol", 0.30)
        adr = vitals.get("adrenaline", 0.15)
        vagal = vitals.get("vagal_tone", 0.65)
        arousal = emotion_state.get("arousal", 0.4)
        valence = emotion_state.get("valence", 0.0)
        emotion = emotion_state.get("emotion", "Calm")

        words = re.findall(r'\b[a-z]{4,}\b', user_msg.lower())
        keywords = [w for w in words if w not in _STOPWORDS]
        # Deduplicate while preserving some variety
        seen = set()
        unique_kw = []
        for w in keywords:
            if w not in seen:
                seen.add(w)
                unique_kw.append(w)
        unique_kw = unique_kw[:8]

        if not unique_kw:
            return

        c = self._conn()
        for kw in unique_kw:
            row = c.execute(
                "SELECT mean_hr, mean_cortisol, mean_adrenaline, mean_vagal, mean_arousal, mean_valence, sample_count FROM somatic_patterns WHERE topic_keyword=? AND emotion=?",
                (kw, emotion)
            ).fetchone()
            if row:
                n = row[6]
                new_n = n + 1
                c.execute("""
                    UPDATE somatic_patterns SET
                        mean_hr=?, mean_cortisol=?, mean_adrenaline=?,
                        mean_vagal=?, mean_arousal=?, mean_valence=?,
                        sample_count=?, last_updated=?
                    WHERE topic_keyword=? AND emotion=?
                """, (
                    (row[0]*n + hr) / new_n,
                    (row[1]*n + cortisol) / new_n,
                    (row[2]*n + adr) / new_n,
                    (row[3]*n + vagal) / new_n,
                    (row[4]*n + arousal) / new_n,
                    (row[5]*n + valence) / new_n,
                    new_n, time.time(), kw, emotion
                ))
            else:
                c.execute("""
                    INSERT INTO somatic_patterns
                      (topic_keyword, emotion, mean_hr, mean_cortisol, mean_adrenaline,
                       mean_vagal, mean_arousal, mean_valence, sample_count, last_updated)
                    VALUES (?,?,?,?,?,?,?,?,1,?)
                """, (kw, emotion, hr, cortisol, adr, vagal, arousal, valence, time.time()))
        c.commit()

    # ── CONVERSATION RECONSTRUCTION ──────────────────────────

    def load_recent_exchanges(self, session_id: str = None, limit: int = 20) -> list:
        """
        Returns a list of {"role": "user"|"assistant", "content": str}
        dicts — ready to pass directly as `messages` to the Claude API.
        """
        c = self._conn()
        if session_id:
            rows = c.execute(
                "SELECT user_msg, ai_msg FROM exchanges WHERE session_id=? ORDER BY turn_index ASC LIMIT ?",
                (session_id, limit)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT user_msg, ai_msg FROM exchanges ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            rows = list(reversed(rows))

        messages = []
        for row in rows:
            messages.append({"role": "user", "content": row[0]})
            messages.append({"role": "assistant", "content": row[1]})
        return messages

    def load_last_session_id(self) -> Optional[str]:
        """Return the most recent session_id that is still within the inactivity window."""
        c = self._conn()
        # Prefer a session that hasn't been ended yet (server restart mid-conversation)
        row = c.execute("""
            SELECT session_id, started_at FROM sessions
            WHERE ended_at IS NULL
            ORDER BY started_at DESC LIMIT 1
        """).fetchone()
        if row:
            # Only resume if it started within the last 30 min
            age = time.time() - row[1]
            if age < 1800:
                return row[0]
        # Otherwise just return the most recent completed session for context loading
        row = c.execute(
            "SELECT session_id FROM sessions ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    # ── CONTEXT BUILDING FOR SYSTEM PROMPT ───────────────────

    def build_long_term_context(self, current_user_msg: str = "") -> str:
        parts = []

        # 1. Facts about the user (name, role, location, etc.)
        facts_text = self._facts_text()
        if facts_text:
            parts.append(facts_text)

        # 2. People Elan knows
        people_text = self._people_text()
        if people_text:
            parts.append(people_text)

        # 3. Recent calendar events / things to remember
        calendar_text = self._calendar_text()
        if calendar_text:
            parts.append(calendar_text)

        # 4. Recent episodes — what actually happened, in order
        episodes_text = self._episodes_text()
        if episodes_text:
            parts.append(episodes_text)

        # 5. Past session summaries
        sessions_text = self._sessions_text()
        if sessions_text:
            parts.append(sessions_text)

        # 6. Somatic associations — what topics activate the body
        soma_text = self._somatic_associations_text(current_user_msg)
        if soma_text:
            parts.append(soma_text)

        if not parts:
            return ""

        return "LONG-TERM MEMORY:\n" + "\n\n".join(parts)

    def _people_text(self) -> str:
        rows = self.get_all_people()
        if not rows:
            return ""
        lines = ["People I know:"]
        for name, rel, notes, count, emotion in rows[:20]:
            desc = name
            if rel:
                desc += f" ({rel})"
            if notes:
                desc += f" — {notes}"
            if count > 1:
                desc += f" [mentioned {count}×]"
            lines.append(f"  · {desc}")
        return "\n".join(lines)

    def _calendar_text(self) -> str:
        rows = self.get_upcoming_events(limit=8)
        if not rows:
            return ""
        import datetime as _dt
        lines = ["Calendar / things to remember:"]
        for event_date, title, desc, created_at in rows:
            when = event_date or _dt.datetime.fromtimestamp(created_at).strftime("%b %d")
            entry = f"  · {when}: {title}"
            if desc:
                entry += f" — {desc}"
            lines.append(entry)
        return "\n".join(lines)

    def _episodes_text(self) -> str:
        rows = self.get_recent_episodes(limit=12)
        if not rows:
            return ""
        import datetime as _dt
        lines = ["Recent memory (sequential):"]
        for ts, ep_type, summary, emotion, valence in reversed(rows):
            dt = _dt.datetime.fromtimestamp(ts).strftime("%b %d %H:%M")
            mood = f" [{emotion}]" if emotion else ""
            lines.append(f"  [{dt}]{mood} {summary[:120]}")
        return "\n".join(lines)

    def _facts_text(self) -> str:
        c = self._conn()
        rows = c.execute("""
            SELECT fact_type, fact_value, times_seen FROM user_facts
            WHERE user_id=? ORDER BY times_seen DESC, last_seen DESC LIMIT 12
        """, (self.user_id,)).fetchall()
        if not rows:
            return ""
        facts = []
        seen_types = set()
        for row in rows:
            ft, fv, n = row[0], row[1], row[2]
            # Deduplicate same fact type (show most-confirmed only)
            if ft in seen_types and ft not in ("likes", "dislikes", "relationship"):
                continue
            seen_types.add(ft)
            label = ft.replace("_", " ")
            qualifier = f" (mentioned {n}×)" if n > 1 else ""
            facts.append(f"{label}: {fv}{qualifier}")
        if not facts:
            return ""
        return "What I know about you: " + " · ".join(facts)

    def _sessions_text(self) -> str:
        c = self._conn()
        rows = c.execute("""
            SELECT started_at, dominant_emotion, mean_valence, emotional_arc,
                   resolution_emotion, topic_summary
            FROM sessions
            WHERE ended_at IS NOT NULL
            ORDER BY started_at DESC LIMIT 5
        """).fetchall()
        if not rows:
            return ""
        lines = ["Recent sessions:"]
        for row in reversed(rows):
            ts, dom, valence, arc_json, resolution, topics = row
            date = time.strftime("%b %d", time.localtime(ts))
            arc = json.loads(arc_json) if arc_json else []
            arc_str = " → ".join(arc[:5]) if arc else dom
            topic_str = topics.replace("Topics: ", "") if topics else ""
            v_str = f"v{valence:+.2f}" if valence is not None else ""
            line = f"  {date} [{dom} {v_str}] {arc_str}"
            if topic_str:
                line += f" — {topic_str}"
            lines.append(line)
        return "\n".join(lines)

    def _somatic_associations_text(self, current_user_msg: str = "") -> str:
        c = self._conn()
        # Find patterns with notable body responses (elevated cortisol or arousal)
        rows = c.execute("""
            SELECT topic_keyword, emotion, mean_cortisol, mean_hr, mean_arousal,
                   mean_vagal, sample_count
            FROM somatic_patterns
            WHERE sample_count >= 2
              AND (mean_cortisol > 0.38 OR mean_arousal > 0.62 OR mean_hr > 84)
            ORDER BY (mean_cortisol + mean_arousal) DESC
            LIMIT 8
        """).fetchall()
        if not rows:
            return ""

        # If we have a current message, prioritise relevant patterns
        current_words = set()
        if current_user_msg:
            current_words = {w for w in re.findall(r'\b[a-z]{4,}\b', current_user_msg.lower())
                             if w not in _STOPWORDS}

        def relevance(row):
            return (3 if row[0] in current_words else 0) + row[1 + 4]  # sample_count

        rows = sorted(rows, key=relevance, reverse=True)[:4]
        lines = []
        for row in rows:
            kw, emotion, cortisol, hr, arousal, vagal, n = row
            soma_desc = []
            if cortisol > 0.42:
                soma_desc.append(f"cortisol↑{cortisol:.2f}")
            if hr > 85:
                soma_desc.append(f"HR↑{hr:.0f}")
            if arousal > 0.65:
                soma_desc.append(f"arousal↑{arousal:.2f}")
            if vagal < 0.50:
                soma_desc.append(f"vagal↓{vagal:.2f}")
            if soma_desc:
                lines.append(f"  '{kw}' → {emotion} [{', '.join(soma_desc)}] ({n}× observed)")
        if not lines:
            return ""
        return "Somatic memory (topics that activate this body):\n" + "\n".join(lines)

    # ── CALENDAR DATA ─────────────────────────────────────────

    def get_calendar_data(self, year: int, month: int) -> dict:
        """
        Returns all sessions for a given month, grouped by date (YYYY-MM-DD).
        Used to render the memory calendar in the UI.
        """
        import calendar
        # First and last timestamp of the requested month
        first_day = time.mktime(time.strptime(f"{year}-{month:02d}-01", "%Y-%m-%d"))
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = time.mktime(time.strptime(f"{year}-{month:02d}-{last_day_num}", "%Y-%m-%d")) + 86400

        c = self._conn()
        rows = c.execute("""
            SELECT session_id, started_at, ended_at, dominant_emotion,
                   mean_valence, topic_summary, turn_count, emotional_arc
            FROM sessions
            WHERE started_at >= ? AND started_at < ?
            ORDER BY started_at ASC
        """, (first_day, last_day)).fetchall()

        # Also pull exchange count per session (more accurate than turn_count field)
        ex_counts = {}
        if rows:
            sids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(sids))
            ex_rows = c.execute(
                f"SELECT session_id, COUNT(*) FROM exchanges WHERE session_id IN ({placeholders}) GROUP BY session_id",
                sids
            ).fetchall()
            ex_counts = {r[0]: r[1] for r in ex_rows}

        days: dict = {}
        for row in rows:
            sid, ts, ended, emotion, valence, topics, turns, arc_json = row
            date_str = time.strftime("%Y-%m-%d", time.localtime(ts))
            if date_str not in days:
                days[date_str] = []
            arc = json.loads(arc_json) if arc_json else []
            duration_min = round((ended - ts) / 60) if ended else None
            days[date_str].append({
                "session_id": sid,
                "time": time.strftime("%H:%M", time.localtime(ts)),
                "emotion": emotion or "Calm",
                "valence": round(valence, 2) if valence is not None else 0,
                "topics": (topics or "").replace("Topics: ", ""),
                "exchanges": ex_counts.get(sid, turns or 0),
                "duration_min": duration_min,
                "arc": arc[:6],
            })

        return {
            "year": year,
            "month": month,
            "days_in_month": calendar.monthrange(year, month)[1],
            "first_weekday": calendar.monthrange(year, month)[0],  # 0=Mon
            "days": days,
            "total_sessions": len(rows),
            "total_exchanges": sum(ex_counts.values()),
        }

    # ── UTILITY ──────────────────────────────────────────────

    def get_temporal_summary(self) -> dict:
        """
        Elan's sense of duration across conversations.
        Returns gap since last session, total time known to this user,
        longest silence, and the emotional shape of recent time.
        """
        c = self._conn()
        now = time.time()

        # All completed sessions, ordered
        rows = c.execute("""
            SELECT started_at, ended_at, dominant_emotion, mean_valence, turn_count
            FROM sessions WHERE ended_at IS NOT NULL
            ORDER BY started_at ASC
        """).fetchall()

        if not rows:
            return {
                "first_meeting": None,
                "total_sessions": 0,
                "gap_since_last_s": None,
                "longest_gap_s": None,
                "mean_gap_s": None,
                "dominant_emotion_over_time": None,
            }

        first_ts = rows[0][0]
        last_ended = rows[-1][1]

        # Gaps between sessions
        gaps = []
        for i in range(1, len(rows)):
            gap = rows[i][0] - rows[i-1][1]  # start of next - end of prev
            if gap > 0:
                gaps.append(gap)

        gap_since_last = now - last_ended
        longest_gap = max(gaps) if gaps else None
        mean_gap = sum(gaps) / len(gaps) if gaps else None

        # Most common emotion across all sessions
        emotion_counts = {}
        for r in rows:
            em = r[2]
            if em:
                emotion_counts[em] = emotion_counts.get(em, 0) + 1
        dominant = max(emotion_counts, key=emotion_counts.get) if emotion_counts else None

        def fmt(s):
            if s is None: return None
            if s < 60: return f"{int(s)}s"
            if s < 3600: return f"{s/60:.0f}m"
            if s < 86400: return f"{s/3600:.1f}h"
            return f"{s/86400:.1f}d"

        # Recent emotional arc — last 5 sessions
        recent_arc = [r[2] for r in rows[-5:] if r[2]]

        return {
            "first_meeting_ts": first_ts,
            "first_meeting_str": time.strftime("%B %d, %Y", time.localtime(first_ts)),
            "total_sessions": len(rows),
            "gap_since_last_s": round(gap_since_last),
            "gap_since_last_str": fmt(gap_since_last),
            "longest_gap_s": round(longest_gap) if longest_gap else None,
            "longest_gap_str": fmt(longest_gap),
            "mean_gap_s": round(mean_gap) if mean_gap else None,
            "mean_gap_str": fmt(mean_gap),
            "dominant_emotion_over_time": dominant,
            "recent_arc": recent_arc,
        }

    def get_stats(self) -> dict:
        c = self._conn()
        ex = c.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0]
        se = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        fa = c.execute("SELECT COUNT(*) FROM user_facts WHERE user_id=?", (self.user_id,)).fetchone()[0]
        sp = c.execute("SELECT COUNT(*) FROM somatic_patterns").fetchone()[0]
        recent = c.execute("""
            SELECT session_id, started_at, dominant_emotion, topic_summary, turn_count
            FROM sessions ORDER BY started_at DESC LIMIT 8
        """).fetchall()
        return {
            "total_exchanges": ex,
            "total_sessions": se,
            "known_facts": fa,
            "somatic_patterns": sp,
            "recent_sessions": [
                {
                    "session_id": r[0],
                    "date": time.strftime("%b %d %H:%M", time.localtime(r[1])),
                    "emotion": r[2],
                    "topics": r[3],
                    "turns": r[4],
                }
                for r in recent
            ],
        }
