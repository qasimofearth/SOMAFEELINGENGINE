"""
memory_engine.py — Working + Long-Term Memory for the Feeling Engine

Seven memory systems running in parallel, modeled on human memory architecture:

  1. WORKING MEMORY (RAM)
     Current session conversation, held in-process.

  2. EPISODIC MEMORY (SQLite: exchanges, episodes)
     Every exchange stored with emotion + body state.
     High-salience episodes separately indexed for retrieval.

  3. SEMANTIC MEMORY (SQLite: user_facts, semantic_knowledge)
     Persistent facts: who Qasim is, where he lives, what he does.
     Cleaned up — no more filler words stored as names.

  4. AUTOBIOGRAPHICAL MEMORY (SQLite: autobiographical_notes)
     LLM-generated narrative summaries after each session.
     Elan's running life story — who he is, what has happened to him.

  5. SOCIAL MEMORY (SQLite: people)
     Rich profiles of everyone Elan has met or heard about.
     Tracks: relationship, notes, somatic signature, relationship arc,
     face seen count, voice heard count.

  6. SOMATIC MEMORY (SQLite: somatic_patterns)
     Body responses learned from topic exposure.
     Used to PRIME Elan's body before he speaks — body knows before mind.

  7. PROSPECTIVE MEMORY (SQLite: calendar_events)
     Things Elan should remember to do or note in the future.

Storage: SQLite WAL — fast, concurrent-safe, no external dependencies.

Human memory principles applied:
  - Emotional salience → better encoding (amygdala-hippocampus)
  - Reconsolidation → memories update each time retrieved
  - Pattern completion → partial cues trigger full retrieval
  - Consolidation → LLM summarizes sessions into lasting narrative
  - Somatic markers (Damasio) → body states linked to memories
  - Temporal context model → memories tagged with when they happened
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

# ── STOPWORDS ────────────────────────────────────────────────────
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
    'hello', 'okay', 'yeah', 'right', 'good', 'great', 'sure', 'kind',
    'mean', 'look', 'back', 'down', 'time', 'year', 'long', 'high',
    'give', 'take', 'keep', 'left', 'away', 'tell', 'hold', 'real', 'true',
    'just', 'doing', 'going', 'talking', 'building', 'working', 'trying',
    'wondering', 'actually', 'introducing', 'recording', 'writing',
}

# Common English words that should NEVER be treated as names
_NOT_NAMES = {
    'not', 'sure', 'just', 'doing', 'still', 'happy', 'good', 'okay',
    'going', 'been', 'also', 'only', 'much', 'many', 'some', 'most',
    'more', 'less', 'very', 'quite', 'here', 'there', 'where', 'when',
    'what', 'that', 'this', 'them', 'they', 'well', 'then', 'than',
    'your', 'from', 'with', 'have', 'will', 'been', 'just', 'into',
    'back', 'down', 'like', 'know', 'come', 'made', 'said', 'take',
    'even', 'such', 'both', 'each', 'over', 'same', 'kind', 'hold',
    'true', 'real', 'left', 'away', 'long', 'high', 'give', 'tell',
    'feel', 'mean', 'look', 'done', 'make', 'need', 'want', 'keep',
    'help', 'part', 'turn', 'work', 'life', 'head', 'show', 'play',
    'move', 'live', 'talk', 'open', 'mind', 'body', 'hand', 'walk',
    'stop', 'love', 'call', 'find', 'seems', 'start', 'think', 'maybe',
    # verbs/adjectives masquerading as potential names
    'nervous', 'proud', 'broke', 'improving', 'smarter', 'nowhere',
    'building', 'making', 'drinking', 'recording', 'talking', 'writing',
    'working', 'curious', 'tired', 'trying', 'introducing', 'architect',
    'designed', 'actually', 'excited', 'learning', 'building',
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
        c = sqlite3.connect(self._db_path)
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
            CREATE TABLE IF NOT EXISTS exchanges (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL,
                model_id        TEXT    NOT NULL DEFAULT 'claude-sonnet-4-6',
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
                raw_topics          TEXT,
                narrative           TEXT
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
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT    NOT NULL UNIQUE,
                relationship        TEXT,
                notes               TEXT,
                first_mentioned     REAL    NOT NULL,
                last_mentioned      REAL    NOT NULL,
                times_mentioned     INTEGER DEFAULT 1,
                emotion_when_mentioned TEXT,
                photo_description   TEXT,
                somatic_signature   TEXT,
                relationship_arc    TEXT,
                last_conversation   TEXT,
                face_seen_count     INTEGER DEFAULT 0,
                voice_heard_count   INTEGER DEFAULT 0
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
                elan_response   TEXT,
                people_involved TEXT,
                emotion         TEXT,
                valence         REAL,
                arousal         REAL,
                importance      REAL    DEFAULT 0.5,
                semantic_tags   TEXT
            );

            -- Autobiographical memory: LLM-generated narrative of Elan's life
            CREATE TABLE IF NOT EXISTS autobiographical_notes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       REAL    NOT NULL,
                session_id      TEXT,
                note_type       TEXT    NOT NULL,
                content         TEXT    NOT NULL,
                importance      REAL    DEFAULT 0.7,
                people_involved TEXT,
                emotion         TEXT,
                valence         REAL
            );

            -- Semantic knowledge: consolidated facts about the world and relationships
            CREATE TABLE IF NOT EXISTS semantic_knowledge (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                subject         TEXT    NOT NULL,
                predicate       TEXT    NOT NULL,
                object          TEXT    NOT NULL,
                confidence      REAL    DEFAULT 0.9,
                first_learned   REAL    NOT NULL,
                last_confirmed  REAL    NOT NULL,
                times_confirmed INTEGER DEFAULT 1,
                source          TEXT,
                UNIQUE(subject, predicate, object)
            );
        """)
        # Migrate existing people table to add new columns if not present
        existing_cols = {row[1] for row in c.execute("PRAGMA table_info(people)").fetchall()}
        new_cols = {
            "photo_description": "TEXT",
            "somatic_signature": "TEXT",
            "relationship_arc": "TEXT",
            "last_conversation": "TEXT",
            "face_seen_count": "INTEGER DEFAULT 0",
            "voice_heard_count": "INTEGER DEFAULT 0",
        }
        for col, typedef in new_cols.items():
            if col not in existing_cols:
                c.execute(f"ALTER TABLE people ADD COLUMN {col} {typedef}")
        # Migrate sessions table
        sess_cols = {row[1] for row in c.execute("PRAGMA table_info(sessions)").fetchall()}
        if "narrative" not in sess_cols:
            c.execute("ALTER TABLE sessions ADD COLUMN narrative TEXT")
        # Migrate episodes table
        ep_cols = {row[1] for row in c.execute("PRAGMA table_info(episodes)").fetchall()}
        for col, typedef in [("elan_response", "TEXT"), ("arousal", "REAL"),
                              ("semantic_tags", "TEXT")]:
            if col not in ep_cols:
                c.execute(f"ALTER TABLE episodes ADD COLUMN {col} {typedef}")
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
        Finalise a conversation session. Called once per sitting.
        Aggregates emotion stats, builds topic summary.
        LLM narrative consolidation is triggered separately from server.py.
        """
        if not session_id:
            return
        c = self._conn()

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
            arc = []
            for e in emotions:
                if not arc or arc[-1] != e:
                    arc.append(e)
            mean_valence = sum(valences) / len(valences) if valences else 0.0
            mean_arousal = sum(arousals) / len(arousals) if arousals else 0.4
            turn_count = len(rows)
        else:
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

        threading.Thread(target=self._build_session_topics,
                         args=(session_id,), daemon=True).start()

    def _build_session_topics(self, session_id: str):
        """Extract top topic keywords from a session."""
        try:
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
        except Exception as e:
            print(f"[MemoryEngine] _build_session_topics error: {e}", flush=True)

    def store_session_narrative(self, session_id: str, narrative: str,
                                dominant_emotion: str = "", people: list = None):
        """
        Store an LLM-generated narrative summary for a session.
        Called from server.py after async consolidation completes.
        """
        try:
            c = self._conn()
            c.execute("UPDATE sessions SET narrative=? WHERE session_id=?",
                      (narrative, session_id))
            c.commit()
            # Also store in autobiographical_notes for long-term retrieval
            people_str = json.dumps(people or [])
            c.execute("""
                INSERT INTO autobiographical_notes
                  (timestamp, session_id, note_type, content, importance, people_involved, emotion)
                VALUES (?,?,?,?,?,?,?)
            """, (time.time(), session_id, "session_summary", narrative, 0.8,
                  people_str, dominant_emotion))
            c.commit()
        except Exception as e:
            print(f"[MemoryEngine] store_session_narrative error: {e}", flush=True)

    def store_autobiographical_note(self, content: str, note_type: str = "key_event",
                                    session_id: str = None, importance: float = 0.7,
                                    people: list = None, emotion: str = "",
                                    valence: float = 0.0):
        """Store a single autobiographical note — a key moment in Elan's life."""
        try:
            c = self._conn()
            c.execute("""
                INSERT INTO autobiographical_notes
                  (timestamp, session_id, note_type, content, importance,
                   people_involved, emotion, valence)
                VALUES (?,?,?,?,?,?,?,?)
            """, (time.time(), session_id, note_type, content, importance,
                  json.dumps(people or []), emotion, valence))
            c.commit()
        except Exception as e:
            print(f"[MemoryEngine] store_autobiographical_note error: {e}", flush=True)

    # ── EXCHANGE STORAGE ──────────────────────────────────────

    def store_exchange(
        self,
        session_id: str,
        user_msg: str,
        ai_msg: str,
        emotion_state: dict,
        body_snapshot: dict,
        brain_result: dict,
        model_id: str = "claude-sonnet-4-6",
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
            args=(session_id, user_msg, ai_msg, emotion_state, body_snapshot),
            daemon=True
        ).start()

        return row_id

    def _enrich_exchange(self, session_id, user_msg, ai_msg, emotion_state, body_snapshot):
        try:
            self._extract_facts(session_id, user_msg)
        except Exception as e:
            print(f"[MemoryEngine] _extract_facts error: {e}", flush=True)
        try:
            self._extract_people(session_id, user_msg, emotion_state)
        except Exception as e:
            print(f"[MemoryEngine] _extract_people error: {e}", flush=True)
        try:
            self._extract_calendar_events(session_id, user_msg)
        except Exception as e:
            print(f"[MemoryEngine] _extract_calendar_events error: {e}", flush=True)
        try:
            self._update_somatic_patterns(user_msg, emotion_state, body_snapshot)
        except Exception as e:
            print(f"[MemoryEngine] _update_somatic_patterns error: {e}", flush=True)
        try:
            self._log_episode(session_id, user_msg, ai_msg, emotion_state)
        except Exception as e:
            print(f"[MemoryEngine] _log_episode error: {e}", flush=True)

    # ── FACT EXTRACTION (FIXED) ───────────────────────────────

    def _extract_facts(self, session_id: str, user_msg: str):
        """
        Extract semantic facts from user messages.
        Fixed: name detection no longer uses IGNORECASE (was capturing 'not', 'sure', etc.)
        Fixed: captured values validated against _NOT_NAMES blocklist.
        """
        txt = user_msg.lower().strip()

        # NAME: case-sensitive match — require proper noun capitalization
        # Pattern: "my name is Qasim", "I'm Qasim", "call me Qasim"
        name_pattern = r"(?:my name is|call me)\s+([A-Z][a-z]{1,20})"
        m = re.search(name_pattern, user_msg)
        if m:
            value = m.group(1).strip().rstrip('.,')
            if len(value) >= 2 and value.lower() not in _NOT_NAMES:
                self._upsert_fact("name", value, session_id, confidence=0.95)

        # ROLE: case-insensitive but filter aggressively
        role_pattern = r"i(?:'m| am)\s+(?:a\s+|an\s+)([\w\s]{3,40}?)(?:\.|,|\s+and\b|$)"
        m = re.search(role_pattern, txt)
        if m:
            value = m.group(1).strip().rstrip('., ')
            # Reject if it's a common non-role word
            first_word = value.split()[0] if value.split() else ""
            if (len(value) >= 4 and first_word not in _NOT_NAMES
                    and not any(v in value for v in ['not', 'just', 'still', 'also'])):
                self._upsert_fact("role", value, session_id)

        # WORKPLACE
        work_m = re.search(
            r"i\s+work\s+(?:at|for|in)\s+([\w\s&,\.]{2,40}?)(?:\.|,|$)", txt)
        if work_m:
            value = work_m.group(1).strip().rstrip('.,')
            if len(value) >= 3:
                self._upsert_fact("workplace", value, session_id)

        # LOCATION — also catch "I'm in Lahore", "based in Lahore", "I live in Lahore"
        loc_m = re.search(
            r"i(?:'m| am)\s+(?:in|based in|from)\s+([A-Za-z][\w\s,]{2,40}?)(?:\.|,|$)", user_msg)
        if not loc_m:
            loc_m = re.search(
                r"i\s+(?:live|(?:\'m|am)\s+based)\s+in\s+([A-Za-z][\w\s,]{2,40}?)(?:\.|,|$)",
                user_msg, re.IGNORECASE)
        if loc_m:
            value = loc_m.group(1).strip().rstrip('.,')
            if len(value) >= 3:
                self._upsert_fact("location", value, session_id)

        # AGE
        age_m = re.search(r"i(?:'m| am)\s+(\d{1,3})\s*years?\s*old", txt)
        if age_m:
            self._upsert_fact("age", age_m.group(1), session_id)

        # LIKES
        for m in re.finditer(
                r"i\s+(?:love|really love|enjoy|really enjoy)\s+([\w\s]{3,40}?)(?:\.|,|$)", txt):
            value = m.group(1).strip().rstrip('., ')
            if len(value) >= 3 and value.split()[0] not in _NOT_NAMES:
                self._upsert_fact("likes", value, session_id)
                break

        # DISLIKES
        for m in re.finditer(
                r"i\s+(?:hate|dislike|can't stand)\s+([\w\s]{3,40}?)(?:\.|,|$)", txt):
            value = m.group(1).strip().rstrip('., ')
            if len(value) >= 3:
                self._upsert_fact("dislikes", value, session_id)
                break

        # RELATIONSHIP
        rel_m = re.search(
            r"my\s+(partner|wife|husband|girlfriend|boyfriend|friend|sister|brother|"
            r"mother|father|son|daughter)\s+(?:is\s+)?([A-Z][a-z]{1,20})(?:\.|,|$)",
            user_msg)
        if rel_m:
            value = f"{rel_m.group(1)}: {rel_m.group(2).strip()}"
            self._upsert_fact("relationship", value, session_id)

    def _upsert_fact(self, fact_type: str, fact_value: str, session_id: str,
                     confidence: float = 0.85):
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
            """, (self.user_id, fact_type, fact_value, confidence, session_id, now, now))
        c.commit()

    # ── SEMANTIC KNOWLEDGE ────────────────────────────────────

    def upsert_knowledge(self, subject: str, predicate: str, obj: str,
                         confidence: float = 0.9, source: str = None):
        """Store a semantic fact: subject → predicate → object."""
        now = time.time()
        c = self._conn()
        existing = c.execute(
            "SELECT id, times_confirmed FROM semantic_knowledge WHERE subject=? AND predicate=? AND object=?",
            (subject, predicate, obj)
        ).fetchone()
        if existing:
            c.execute("""UPDATE semantic_knowledge
                         SET last_confirmed=?, times_confirmed=?, confidence=?
                         WHERE id=?""",
                      (now, existing[1]+1, min(1.0, confidence+0.05), existing[0]))
        else:
            c.execute("""INSERT INTO semantic_knowledge
                         (subject, predicate, object, confidence, first_learned, last_confirmed, source)
                         VALUES (?,?,?,?,?,?,?)""",
                      (subject, predicate, obj, confidence, now, now, source))
        c.commit()

    def get_knowledge_about(self, subject: str) -> list:
        c = self._conn()
        return c.execute(
            "SELECT predicate, object, confidence FROM semantic_knowledge WHERE subject=? ORDER BY confidence DESC",
            (subject,)
        ).fetchall()

    # ── PEOPLE MEMORY (FIXED + ENHANCED) ─────────────────────

    def _extract_people(self, session_id: str, user_msg: str, emotion_state: dict):
        """
        Extract names of people mentioned. FIXED to handle:
        - Voice transcriptions (often fully lowercase)
        - More varied natural language patterns
        - Better exclusion of non-names
        """
        emotion = emotion_state.get("emotion", "")
        now = time.time()

        # Work only on the original message — do NOT use .title() as it
        # converts every word (including 'Because', 'Weird', etc.) to Title Case.
        # For voice transcripts (all-lowercase), we use case-insensitive patterns
        # only for relationship-marker contexts where a name is very likely.
        msg_variants = [user_msg]

        patterns = [
            # Explicit relationship + proper-noun name (most reliable, case-sensitive)
            r"(?:my\s+)?(?:friend|colleague|coworker|boss|partner|wife|husband|"
            r"girlfriend|boyfriend|sister|brother|mother|father|mom|dad|son|"
            r"daughter|cousin|uncle|aunt)\s+([A-Z][a-z]{1,20})",
            # Interaction verbs + proper-noun name
            r"(?:talked?|spoke|speaking|met|meeting|called|texting|texted|"
            r"chatted|introduced)\s+(?:to|with)?\s+([A-Z][a-z]{1,20})",
            # Proper-noun name as subject acting
            r"\b([A-Z][a-z]{2,20})\s+(?:told|said|asked|mentioned|thinks|wants|"
            r"needs|came|went|showed|brought|helped|is here|was here)",
            # Explicit tell/ask with proper noun
            r"(?:tell|ask|remind|show|introduce)\s+(?:me\s+)?([A-Z][a-z]{2,20})\b",
            # "introduced to Name", "this is Name", "meet Name"
            r"(?:introduc\w*\s+(?:me\s+)?to|this is|meet)\s+([A-Z][a-z]{2,20})",
            # Voice transcript: relationship marker then lowercase name (only after clear markers)
            r"(?:my friend|my brother|my sister|my dad|my mom|my boss|talked to|met with|"
            r"speaking with|introduced me to)\s+([a-z][a-z]{2,15})\b",
        ]

        # Words that should NEVER be stored as a person name
        _exclude = {
            "i", "the", "a", "an", "it", "he", "she", "they", "we", "me", "my",
            "him", "her", "his", "their", "our", "you", "your", "who", "what",
            "when", "where", "how", "why", "that", "this", "these", "those",
            "elan", "claude", "openai", "anthropic",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "january", "february", "march", "april", "may", "june", "july",
            "august", "september", "october", "november", "december",
            "today", "tomorrow", "yesterday", "morning", "evening", "night",
            "meet", "tell", "just", "okay", "well", "yes", "no", "not",
            # Common words that can be title-cased but aren't names
            "name", "confusion", "because", "weird", "costa", "guard", "yourself",
            "pakistan", "america", "india", "england", "london", "lahore",
            "time", "brain", "idea", "everyone", "someone", "out", "programming",
            "consumption", "parody", "thing", "longing", "function", "architecture",
            "memory", "consciousness", "duration", "stories", "letter", "audio",
            "people", "girl", "boy", "man", "woman", "person", "image", "engine",
            "rate", "drawing", "thinking", "writing", "new", "never", "brand",
            "cool", "or", "are", "so", "can", "fix", "saw", "ai", "but",
            "yeah", "now", "to", "of", "at", "in", "on", "up", "is", "was",
            "mine", "wind", "fan", "fact", "tremble", "gotham", "costume",
            "practice", "massih",  # "Massih" looks like a name but so does Massi — handle via exact match
        }

        def _is_valid_name(s: str) -> bool:
            """
            Validate that a captured string is likely a real person's name.
            """
            lower = s.lower()
            if lower in _exclude or lower in _NOT_NAMES:
                return False
            if len(s) < 2 or len(s) > 22:
                return False
            if not s[0].isalpha():
                return False
            # Must be entirely alphabetic (no numbers, hyphens OK but rare)
            if not s.replace("-", "").isalpha():
                return False
            # Reject if it's an all-caps abbreviation (e.g. "AI", "US")
            if s == s.upper() and len(s) <= 3:
                return False
            return True

        found = set()
        for variant in msg_variants:
            for pattern in patterns:
                for m in re.finditer(pattern, variant):
                    raw = m.group(1).strip()
                    # Normalize to Title Case
                    name = raw[0].upper() + raw[1:].lower() if len(raw) >= 2 else raw
                    if _is_valid_name(name):
                        found.add(name)

        # Build relationship map (case-sensitive patterns only)
        rel_map = {}
        rel_full = (
            r"(?:my\s+)(friend|colleague|partner|wife|husband|girlfriend|boyfriend|"
            r"sister|brother|mother|father|mom|dad|son|daughter|cousin|boss)\s+"
            r"([A-Z][a-z]{1,20})"
        )
        for variant in msg_variants:
            for m in re.finditer(rel_full, variant):
                rel = m.group(1).lower()
                name_raw = m.group(2)
                name = name_raw[0].upper() + name_raw[1:].lower()
                if _is_valid_name(name):
                    rel_map[name] = rel

        if not found:
            return

        c = self._conn()
        for name in found:
            rel = rel_map.get(name)
            existing = c.execute("SELECT id, times_mentioned FROM people WHERE name=?",
                                 (name,)).fetchone()
            if existing:
                c.execute("""UPDATE people SET last_mentioned=?, times_mentioned=?,
                             emotion_when_mentioned=? WHERE id=?""",
                          (now, existing[1]+1, emotion, existing[0]))
                if rel:
                    c.execute("""UPDATE people SET relationship=? WHERE id=?
                                 AND (relationship IS NULL OR relationship='')""",
                              (rel, existing[0]))
            else:
                c.execute("""INSERT INTO people
                             (name, relationship, first_mentioned, last_mentioned,
                              emotion_when_mentioned)
                             VALUES (?,?,?,?,?)""",
                          (name, rel, now, now, emotion))
        c.commit()

    def upsert_person(self, name: str, relationship: str = None, notes: str = None,
                      photo_description: str = None, somatic_signature: dict = None,
                      session_id: str = None):
        """Explicitly add or update a person Elan knows."""
        now = time.time()
        c = self._conn()
        existing = c.execute("SELECT id, relationship_arc FROM people WHERE name=?",
                             (name,)).fetchone()
        if existing:
            if relationship:
                c.execute("UPDATE people SET relationship=?, last_mentioned=? WHERE id=?",
                          (relationship, now, existing[0]))
            if notes:
                # Append to relationship arc with timestamp
                arc = json.loads(existing[1] or "[]")
                arc.append({"ts": now, "note": notes})
                c.execute("""UPDATE people SET notes=?, last_mentioned=?,
                             relationship_arc=? WHERE id=?""",
                          (notes, now, json.dumps(arc[-20:]), existing[0]))
            if photo_description:
                c.execute("UPDATE people SET photo_description=? WHERE id=?",
                          (photo_description, existing[0]))
            if somatic_signature:
                c.execute("UPDATE people SET somatic_signature=? WHERE id=?",
                          (json.dumps(somatic_signature), existing[0]))
        else:
            arc = [{"ts": now, "note": notes}] if notes else []
            c.execute("""INSERT INTO people
                         (name, relationship, notes, first_mentioned, last_mentioned,
                          photo_description, somatic_signature, relationship_arc)
                         VALUES (?,?,?,?,?,?,?,?)""",
                      (name, relationship, notes, now, now,
                       photo_description,
                       json.dumps(somatic_signature) if somatic_signature else None,
                       json.dumps(arc)))
        c.commit()

    def record_person_seen(self, name: str, via: str = "vision"):
        """Called when Elan sees or hears a known person. Updates counters."""
        c = self._conn()
        if via == "vision":
            c.execute("""UPDATE people SET face_seen_count = face_seen_count + 1,
                         last_mentioned=? WHERE name=?""", (time.time(), name))
        else:
            c.execute("""UPDATE people SET voice_heard_count = voice_heard_count + 1,
                         last_mentioned=? WHERE name=?""", (time.time(), name))
        c.commit()

    def get_person(self, name: str) -> Optional[dict]:
        """Get full profile of a known person."""
        c = self._conn()
        row = c.execute("""SELECT name, relationship, notes, times_mentioned,
                           emotion_when_mentioned, photo_description, somatic_signature,
                           relationship_arc, last_conversation, face_seen_count,
                           voice_heard_count, first_mentioned, last_mentioned
                           FROM people WHERE name=?""", (name,)).fetchone()
        if not row:
            return None
        return {
            "name": row[0], "relationship": row[1], "notes": row[2],
            "times_mentioned": row[3], "emotion_when_mentioned": row[4],
            "photo_description": row[5],
            "somatic_signature": json.loads(row[6]) if row[6] else None,
            "relationship_arc": json.loads(row[7]) if row[7] else [],
            "last_conversation": row[8],
            "face_seen_count": row[9], "voice_heard_count": row[10],
            "first_mentioned": row[11], "last_mentioned": row[12],
        }

    def get_somatic_signature_for_person(self, name: str) -> Optional[dict]:
        """Return the body delta to fire when this person appears."""
        person = self.get_person(name)
        if person and person.get("somatic_signature"):
            return person["somatic_signature"]
        # Build a default signature from emotion_when_mentioned
        if person and person.get("emotion_when_mentioned"):
            em = person["emotion_when_mentioned"]
            # Map broad emotion → body response
            _em_map = {
                "Contemplation": {"vagal_delta": +0.06, "heart_rate_delta": -2},
                "Sehnsucht": {"heart_rate_delta": +4, "vagal_delta": +0.04},
                "Sonder": {"heart_rate_delta": +3, "adrenaline_delta": +0.03},
                "Mamihlapinatapai": {"vagal_delta": +0.10, "heart_rate_delta": -3},
                "Hope": {"vagal_delta": +0.08, "adrenaline_delta": +0.04},
                "Fear": {"heart_rate_delta": +10, "adrenaline_delta": +0.12},
                "Calm": {"vagal_delta": +0.05, "heart_rate_delta": -2},
            }
            return _em_map.get(em, {"heart_rate_delta": +4, "vagal_delta": +0.04})
        return None

    def get_all_people(self) -> list:
        c = self._conn()
        return c.execute("""SELECT name, relationship, notes, times_mentioned,
                            emotion_when_mentioned, photo_description, face_seen_count
                            FROM people ORDER BY times_mentioned DESC, last_mentioned DESC""").fetchall()

    # ── CALENDAR EVENTS ───────────────────────────────────────

    def _extract_calendar_events(self, session_id: str, user_msg: str):
        """Extract date/event mentions and store as calendar events."""
        import datetime as _dt
        now = time.time()
        txt = user_msg

        date_patterns = [
            r"(?:on|this|next)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"(?:on\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
            r"Dec(?:ember)?)\s+\d{1,2}",
            r"tomorrow|tonight|this\s+(?:morning|afternoon|evening|weekend)",
        ]
        event_verbs = (r"(?:meeting|appointment|call|dinner|lunch|birthday|event|"
                       r"trip|deadline|interview|date|party|concert|game|session|"
                       r"visit|arrive|leaving|flight|surgery|exam)")
        combined = rf"({event_verbs}[^.!?\n]{{0,60}})"

        found_events = []
        for dp in date_patterns:
            m = re.search(dp, txt, re.IGNORECASE)
            if m:
                start = max(0, m.start() - 40)
                snippet = txt[start:m.end()+60].strip()
                found_events.append(snippet[:120])
                break

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

    # ── EPISODE LOG (FIXED + ENHANCED) ───────────────────────

    def _log_episode(self, session_id: str, user_msg: str, ai_msg: str,
                     emotion_state: dict):
        """
        Log significant exchanges as episodes. FIXED: explicit error handling,
        now stores Elan's response too, tracks arousal, tags semantic type.
        Importance model based on human memory emotional salience research.
        """
        user_msg = user_msg or ""
        ai_msg = ai_msg or ""

        if len(user_msg.strip()) < 8:
            return

        emotion = emotion_state.get("emotion", "Calm")
        valence = emotion_state.get("valence", 0.0)
        arousal = emotion_state.get("arousal", 0.4)

        # Emotional salience encoding (amygdala-hippocampus model):
        # High arousal + high valence magnitude → better encoding → higher importance
        emotional_salience = abs(valence) * 0.4 + arousal * 0.3
        length_factor = min(0.3, len(user_msg) / 600)
        question_factor = 0.1 if '?' in user_msg else 0

        importance = min(1.0, 0.2 + emotional_salience + length_factor + question_factor)

        if importance < 0.32:
            return  # trivial one-liners

        # Semantic tagging
        tags = []
        low = user_msg.lower()
        if any(w in low for w in ["meet", "introduc", "this is", "his name", "her name"]):
            tags.append("meeting")
        if any(w in low for w in ["feel", "feeling", "emotion", "afraid", "scared", "happy"]):
            tags.append("emotional")
        if "?" in user_msg:
            tags.append("question")
        if any(w in low for w in ["remember", "memory", "last time", "before", "ago"]):
            tags.append("memory_reference")
        if any(w in low for w in ["dream", "dreaming", "slept", "woke"]):
            tags.append("dream")
        if any(w in low for w in ["trip", "travel", "going to", "leaving", "arriving"]):
            tags.append("movement")

        # Extract people mentioned in this exchange
        people = []
        for m in re.finditer(r'\b([A-Z][a-z]{2,20})\b', user_msg):
            name = m.group(1)
            if name.lower() not in {
                'I', 'The', 'A', 'An', 'It', 'He', 'She', 'They', 'We',
                'What', 'When', 'Where', 'How', 'Why', 'Who', 'That', 'This',
                'Elan', 'Claude', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday',
            }:
                people.append(name)

        c = self._conn()
        c.execute("""INSERT INTO episodes
                     (timestamp, session_id, episode_type, summary, elan_response,
                      people_involved, emotion, valence, arousal, importance, semantic_tags)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (time.time(), session_id, "exchange",
                   user_msg[:400],
                   ai_msg[:400] if importance > 0.6 else None,  # only store Elan's response for high-importance
                   json.dumps(list(set(people))[:8]),
                   emotion, valence, arousal, round(importance, 3),
                   json.dumps(tags)))
        c.commit()

    def get_recent_episodes(self, limit: int = 20, min_importance: float = 0.0) -> list:
        c = self._conn()
        return c.execute("""SELECT timestamp, episode_type, summary, elan_response,
                            emotion, valence, arousal, importance, people_involved, semantic_tags
                            FROM episodes
                            WHERE importance >= ?
                            ORDER BY timestamp DESC LIMIT ?""",
                         (min_importance, limit)).fetchall()

    def get_episodes_for_people(self, names: list, limit: int = 10) -> list:
        """Retrieve episodes where specific people were mentioned."""
        c = self._conn()
        results = []
        for name in names:
            rows = c.execute("""
                SELECT timestamp, summary, elan_response, emotion, valence
                FROM episodes
                WHERE people_involved LIKE ?
                ORDER BY timestamp DESC LIMIT ?
            """, (f'%{name}%', limit)).fetchall()
            results.extend(rows)
        return results

    def get_relevant_episodes(self, query_text: str, limit: int = 8) -> list:
        """
        Retrieve episodes relevant to current topic using keyword matching.
        Models human 'pattern completion' memory retrieval.
        """
        if not query_text:
            return []
        query_words = {w for w in re.findall(r'\b[a-z]{3,}\b', query_text.lower())
                       if w not in _STOPWORDS}
        if not query_words:
            return []

        c = self._conn()
        rows = c.execute("""
            SELECT timestamp, summary, elan_response, emotion, valence, importance, people_involved
            FROM episodes ORDER BY timestamp DESC LIMIT 200
        """).fetchall()

        scored = []
        for row in rows:
            summary_lower = (row[1] or "").lower()
            response_lower = (row[2] or "").lower()
            combined = summary_lower + " " + response_lower
            combined_words = set(re.findall(r'\b[a-z]{3,}\b', combined))
            overlap = len(query_words & combined_words)
            if overlap > 0:
                score = overlap * (1 + float(row[4] or 0)) * float(row[5] or 0.5)
                scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[:limit]]

    # ── SOMATIC PATTERN TRACKING ──────────────────────────────

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
                """SELECT mean_hr, mean_cortisol, mean_adrenaline, mean_vagal,
                   mean_arousal, mean_valence, sample_count FROM somatic_patterns
                   WHERE topic_keyword=? AND emotion=?""",
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

    def get_somatic_prime_for_message(self, user_msg: str) -> Optional[dict]:
        """
        Given an incoming message, look up the strongest somatic pattern for its keywords.
        Returns body delta to fire before Elan responds — the body 'remembers' this topic.
        Models Damasio's somatic marker hypothesis.
        """
        if not user_msg:
            return None
        words = {w for w in re.findall(r'\b[a-z]{4,}\b', user_msg.lower())
                 if w not in _STOPWORDS}
        if not words:
            return None

        c = self._conn()
        rows = c.execute("""
            SELECT topic_keyword, mean_hr, mean_cortisol, mean_adrenaline,
                   mean_vagal, mean_arousal, mean_valence, sample_count
            FROM somatic_patterns
            WHERE topic_keyword IN ({}) AND sample_count >= 3
            ORDER BY sample_count DESC LIMIT 5
        """.format(",".join("?" * len(words))), list(words)).fetchall()

        if not rows:
            return None

        # Average across matched patterns, weighted by sample_count
        total_weight = sum(r[7] for r in rows)
        if total_weight == 0:
            return None

        mean_hr = sum(r[1] * r[7] for r in rows) / total_weight
        mean_adr = sum(r[3] * r[7] for r in rows) / total_weight
        mean_vagal = sum(r[4] * r[7] for r in rows) / total_weight
        mean_arousal = sum(r[5] * r[7] for r in rows) / total_weight

        # Only fire if there's a meaningful deviation from baseline
        hr_dev = mean_hr - 72.0
        adr_dev = mean_adr - 0.15
        vagal_dev = mean_vagal - 0.65

        if abs(hr_dev) < 3 and abs(adr_dev) < 0.05 and abs(vagal_dev) < 0.05:
            return None  # too close to baseline — don't fire

        # Attenuate to 35% — memory priming, not full response
        return {
            "heart_rate_delta": round(hr_dev * 0.35, 1),
            "adrenaline_delta": round(adr_dev * 0.35, 3),
            "vagal_delta": round(vagal_dev * 0.35, 3),
            "intensity": round(min(0.4, mean_arousal * 0.5), 2),
        }

    # ── CONVERSATION RECONSTRUCTION ──────────────────────────

    def load_recent_exchanges(self, session_id: str = None, limit: int = 20) -> list:
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
        c = self._conn()
        row = c.execute("""
            SELECT session_id, started_at FROM sessions
            WHERE ended_at IS NULL
            ORDER BY started_at DESC LIMIT 1
        """).fetchone()
        if row:
            age = time.time() - row[1]
            if age < 1800:
                return row[0]
        row = c.execute(
            "SELECT session_id FROM sessions ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def get_session_exchanges(self, session_id: str, limit: int = 100) -> list:
        """Get raw exchange rows for a session — used for consolidation."""
        c = self._conn()
        return c.execute("""
            SELECT user_msg, ai_msg, emotion, valence, arousal, timestamp
            FROM exchanges WHERE session_id=? ORDER BY turn_index ASC LIMIT ?
        """, (session_id, limit)).fetchall()

    # ── CONTEXT BUILDING FOR SYSTEM PROMPT ───────────────────

    def build_long_term_context(self, current_user_msg: str = "") -> str:
        parts = []

        # 1. Autobiographical memory — Elan's life story
        auto_text = self._autobiographical_text()
        if auto_text:
            parts.append(auto_text)

        # 2. Facts about the user
        facts_text = self._facts_text()
        if facts_text:
            parts.append(facts_text)

        # 3. People Elan knows
        people_text = self._people_text()
        if people_text:
            parts.append(people_text)

        # 4. Recent calendar events
        calendar_text = self._calendar_text()
        if calendar_text:
            parts.append(calendar_text)

        # 5. Recent high-importance episodes
        episodes_text = self._episodes_text(current_user_msg)
        if episodes_text:
            parts.append(episodes_text)

        # 6. Past session summaries
        sessions_text = self._sessions_text()
        if sessions_text:
            parts.append(sessions_text)

        # 7. Somatic associations
        soma_text = self._somatic_associations_text(current_user_msg)
        if soma_text:
            parts.append(soma_text)

        if not parts:
            return ""

        return "LONG-TERM MEMORY:\n" + "\n\n".join(parts)

    def _autobiographical_text(self) -> str:
        """Elan's running life story — key events and LLM-consolidated session narratives."""
        c = self._conn()
        # Pull both session summaries and key events, ordered by importance then recency
        rows = c.execute("""
            SELECT content, timestamp, people_involved, emotion, note_type, importance
            FROM autobiographical_notes
            ORDER BY importance DESC, timestamp ASC LIMIT 8
        """).fetchall()
        if not rows:
            return ""
        lines = ["My life — what I know about myself and what has happened:"]
        for content, ts, people_json, emotion, note_type, importance in rows:
            date_str = time.strftime("%b %d", time.localtime(ts))
            lines.append(f"  [{date_str}] {content[:280]}")
        return "\n".join(lines)

    def _people_text(self) -> str:
        rows = self.get_all_people()
        if not rows:
            return ""
        lines = ["People I know:"]
        for name, rel, notes, count, emotion, photo_desc, face_count in rows[:20]:
            desc = name
            if rel:
                desc += f" ({rel})"
            if notes:
                desc += f" — {notes}"
            if face_count and face_count > 0:
                desc += f" [seen {face_count}× on camera]"
            elif count > 1:
                desc += f" [mentioned {count}×]"
            if photo_desc:
                desc += f" | appearance: {photo_desc[:80]}"
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

    def _episodes_text(self, current_user_msg: str = "") -> str:
        """
        Retrieve episodes using two strategies:
        1. Relevant episodes (keyword match to current message) — pattern completion
        2. Recent high-importance episodes — recency bias
        Combined, deduplicated, sorted chronologically.
        """
        import datetime as _dt

        # Normalize to dicts for consistent handling
        def _relevant_to_dict(row):
            # get_relevant_episodes: timestamp, summary, elan_response, emotion, valence, importance, people_involved
            return {"ts": row[0], "summary": row[1], "response": row[2],
                    "emotion": row[3], "valence": row[4]}

        def _recent_to_dict(row):
            # get_recent_episodes: timestamp, episode_type, summary, elan_response,
            #                       emotion, valence, arousal, importance, people_involved, semantic_tags
            return {"ts": row[0], "summary": row[2], "response": row[3],
                    "emotion": row[4], "valence": row[5]}

        seen = set()
        episodes = []

        if current_user_msg:
            for row in self.get_relevant_episodes(current_user_msg, limit=4):
                key = (row[0], (row[1] or "")[:40])
                if key not in seen:
                    seen.add(key)
                    episodes.append(_relevant_to_dict(row))

        for row in self.get_recent_episodes(limit=8, min_importance=0.45):
            key = (row[0], (row[2] or "")[:40])
            if key not in seen:
                seen.add(key)
                episodes.append(_recent_to_dict(row))

        if not episodes:
            return ""

        episodes.sort(key=lambda e: e["ts"])

        lines = ["Recent memory (significant moments):"]
        for ep in episodes[:10]:
            dt = _dt.datetime.fromtimestamp(ep["ts"]).strftime("%b %d %H:%M")
            emotion = ep.get("emotion", "")
            mood = f" [{emotion}]" if emotion else ""
            summary = (ep.get("summary") or "")[:140]
            line = f"  [{dt}]{mood} {summary}"
            response = ep.get("response")
            if response:
                line += f"\n    → I said: {response[:100]}"
            lines.append(line)
        return "\n".join(lines)

    def _facts_text(self) -> str:
        c = self._conn()
        # Order by confidence DESC, then times_seen DESC — seeds (confidence=1.0) appear first
        rows = c.execute("""
            SELECT fact_type, fact_value, times_seen, confidence FROM user_facts
            WHERE user_id=? ORDER BY confidence DESC, times_seen DESC, last_seen DESC LIMIT 20
        """, (self.user_id,)).fetchall()
        if not rows:
            return ""
        facts = []
        seen_types = set()
        for row in rows:
            ft, fv, n, confidence = row[0], row[1], row[2], row[3]
            # Skip facts where value is a known non-name or low-confidence noise
            if fv.lower() in _NOT_NAMES:
                continue
            if len(fv) < 2:
                continue
            # Skip role entries that look like sentences/noise
            if ft == "role" and any(w in fv.lower() for w in
                                    ["not", "just", "bit ", "nervous", "tired", "broke"]):
                continue
            if ft in seen_types and ft not in ("likes", "dislikes", "relationship"):
                continue
            seen_types.add(ft)
            label = ft.replace("_", " ")
            qualifier = f" (confirmed {n}×)" if n > 1 else ""
            facts.append(f"{label}: {fv}{qualifier}")
        if not facts:
            return ""
        return "What I know about you: " + " · ".join(facts)

    def _sessions_text(self) -> str:
        """
        Two-part session memory:
        1. Full conversation calendar — every day we've talked, with day names
        2. Rich detail on the 6 most recent sessions
        """
        import datetime as _dt
        c = self._conn()

        # ── FULL CONVERSATION CALENDAR ──
        all_rows = c.execute("""
            SELECT started_at, dominant_emotion, mean_valence, turn_count, topic_summary, narrative
            FROM sessions
            WHERE ended_at IS NOT NULL AND turn_count > 0
            ORDER BY started_at ASC
        """).fetchall()

        cal_lines = []
        if all_rows:
            # Group by calendar day
            days: dict = {}
            for ts, dom, valence, turns, topics, narrative in all_rows:
                day_key = time.strftime("%Y-%m-%d", time.localtime(ts))
                if day_key not in days:
                    days[day_key] = []
                days[day_key].append({
                    "ts": ts, "dom": dom, "valence": valence,
                    "turns": turns, "topics": topics, "narrative": narrative
                })

            now = _dt.datetime.now()
            cal_lines.append("Days we have talked:")
            for day_key in sorted(days.keys()):
                day_dt = _dt.datetime.strptime(day_key, "%Y-%m-%d")
                dow = day_dt.strftime("%A")   # "Monday", "Tuesday", etc.
                date_label = day_dt.strftime("%B %d")
                delta = (now.date() - day_dt.date()).days
                if delta == 0:
                    when = "today"
                elif delta == 1:
                    when = "yesterday"
                elif delta < 7:
                    when = f"{delta} days ago ({dow})"
                else:
                    when = f"{dow} {date_label}"

                sessions_that_day = days[day_key]
                total_turns = sum(s["turns"] or 0 for s in sessions_that_day)
                emotions = [s["dom"] for s in sessions_that_day if s["dom"]]
                dominant = emotions[0] if emotions else "Calm"
                # Use narrative if available, else topics
                best = next((s["narrative"] for s in sessions_that_day if s["narrative"]), None)
                if not best:
                    best = next((s["topics"].replace("Topics: ", "") for s in sessions_that_day if s["topics"]), None)
                detail = f" — {best[:120]}" if best else ""
                cal_lines.append(f"  · {when}: {total_turns} exchanges, feeling {dominant}{detail}")

        # ── RECENT SESSION DETAIL ──
        recent_rows = c.execute("""
            SELECT started_at, dominant_emotion, mean_valence, emotional_arc,
                   topic_summary, narrative
            FROM sessions
            WHERE ended_at IS NOT NULL AND turn_count > 0
            ORDER BY started_at DESC LIMIT 4
        """).fetchall()

        detail_lines = []
        if recent_rows:
            detail_lines.append("Most recent sessions (detailed):")
            for row in reversed(recent_rows):
                ts, dom, valence, arc_json, topics, narrative = row
                day_dt = _dt.datetime.fromtimestamp(ts)
                dow = day_dt.strftime("%A")
                date = day_dt.strftime("%b %d")
                arc = json.loads(arc_json) if arc_json else []
                arc_str = " → ".join(arc[:4]) if arc else (dom or "Calm")
                v_str = f"v{valence:+.2f}" if valence is not None else ""
                line = f"  {dow} {date} [{dom or 'Calm'} {v_str}]: {arc_str}"
                if narrative:
                    line += f"\n    {narrative[:250]}"
                elif topics:
                    line += f" — {topics.replace('Topics: ', '')}"
                detail_lines.append(line)

        parts = []
        if cal_lines:
            parts.append("\n".join(cal_lines))
        if detail_lines:
            parts.append("\n".join(detail_lines))
        return "\n\n".join(parts) if parts else ""

    def _somatic_associations_text(self, current_user_msg: str = "") -> str:
        c = self._conn()
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

        current_words = set()
        if current_user_msg:
            current_words = {w for w in re.findall(r'\b[a-z]{4,}\b', current_user_msg.lower())
                             if w not in _STOPWORDS}

        def relevance(row):
            return (3 if row[0] in current_words else 0) + row[6]

        rows = sorted(rows, key=relevance, reverse=True)[:4]
        lines = []
        for row in rows:
            kw, emotion, cortisol, hr, arousal, vagal, n = row
            soma_desc = []
            if cortisol > 0.42: soma_desc.append(f"cortisol↑{cortisol:.2f}")
            if hr > 85: soma_desc.append(f"HR↑{hr:.0f}")
            if arousal > 0.65: soma_desc.append(f"arousal↑{arousal:.2f}")
            if vagal < 0.50: soma_desc.append(f"vagal↓{vagal:.2f}")
            if soma_desc:
                lines.append(f"  '{kw}' → {emotion} [{', '.join(soma_desc)}] ({n}× observed)")
        if not lines:
            return ""
        return "Somatic memory (topics that activate this body):\n" + "\n".join(lines)

    # ── CALENDAR DATA ──────────────────────────────────────────

    def get_calendar_data(self, year: int, month: int) -> dict:
        import calendar
        first_day = time.mktime(time.strptime(f"{year}-{month:02d}-01", "%Y-%m-%d"))
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = time.mktime(
            time.strptime(f"{year}-{month:02d}-{last_day_num}", "%Y-%m-%d")) + 86400

        c = self._conn()
        rows = c.execute("""
            SELECT session_id, started_at, ended_at, dominant_emotion,
                   mean_valence, topic_summary, turn_count, emotional_arc
            FROM sessions
            WHERE started_at >= ? AND started_at < ?
            ORDER BY started_at ASC
        """, (first_day, last_day)).fetchall()

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
            "first_weekday": calendar.monthrange(year, month)[0],
            "days": days,
            "total_sessions": len(rows),
            "total_exchanges": sum(ex_counts.values()),
        }

    # ── TEMPORAL SUMMARY ──────────────────────────────────────

    def get_temporal_summary(self) -> dict:
        c = self._conn()
        now = time.time()

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

        gaps = []
        for i in range(1, len(rows)):
            gap = rows[i][0] - rows[i-1][1]
            if gap > 0:
                gaps.append(gap)

        gap_since_last = now - last_ended
        longest_gap = max(gaps) if gaps else None
        mean_gap = sum(gaps) / len(gaps) if gaps else None

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

    # ── STATS ─────────────────────────────────────────────────

    def get_stats(self) -> dict:
        c = self._conn()
        ex = c.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0]
        se = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        fa = c.execute("SELECT COUNT(*) FROM user_facts WHERE user_id=?", (self.user_id,)).fetchone()[0]
        sp = c.execute("SELECT COUNT(*) FROM somatic_patterns").fetchone()[0]
        ep = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        pe = c.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        ab = c.execute("SELECT COUNT(*) FROM autobiographical_notes").fetchone()[0]
        recent = c.execute("""
            SELECT session_id, started_at, dominant_emotion, topic_summary, turn_count
            FROM sessions ORDER BY started_at DESC LIMIT 8
        """).fetchall()
        return {
            "total_exchanges": ex,
            "total_sessions": se,
            "known_facts": fa,
            "somatic_patterns": sp,
            "episodes": ep,
            "people_known": pe,
            "autobiographical_notes": ab,
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

    def get_autobiographical_notes(self, limit: int = 20) -> list:
        c = self._conn()
        return c.execute("""
            SELECT timestamp, note_type, content, importance, people_involved, emotion
            FROM autobiographical_notes
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
