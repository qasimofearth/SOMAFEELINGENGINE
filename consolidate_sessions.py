"""
consolidate_sessions.py — Retroactively generate LLM narratives for all
past sessions that never got consolidated (Railway restart killed the thread).

Run with:
    GROQ_API_KEY=gsk_... python3 consolidate_sessions.py
    ANTHROPIC_API_KEY=sk-ant-... python3 consolidate_sessions.py

Or if the key is already in /tmp/fe_keys.json:
    python3 consolidate_sessions.py
"""
import os, sys, sqlite3, json, re, time, datetime
sys.path.insert(0, os.path.dirname(__file__))

# ── Resolve API key — Groq preferred, Anthropic fallback ────────────────────
groq_key = os.environ.get("GROQ_API_KEY", "")
anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")

if not groq_key and not anthropic_key:
    try:
        d = json.load(open("/tmp/fe_keys.json"))
        groq_key = d.get("groq_key", "")
        anthropic_key = d.get("key", "")
    except Exception:
        pass

USE_GROQ = bool(groq_key)
USE_ANTHROPIC = bool(anthropic_key) and not USE_GROQ

if not USE_GROQ and not USE_ANTHROPIC:
    print("ERROR: No API key found.")
    print("Run as: GROQ_API_KEY=gsk_... python3 consolidate_sessions.py")
    sys.exit(1)

if USE_GROQ:
    import groq as _groq
    client = _groq.Groq(api_key=groq_key)
    MODEL = "llama-3.3-70b-versatile"
    print(f"Using Groq / {MODEL}")
else:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=anthropic_key)
    MODEL = "claude-haiku-4-5-20251001"
    print(f"Using Anthropic / {MODEL}")

from memory_engine import MemoryEngine

DB = os.path.join(os.path.dirname(__file__), "feeling_memory", "memory_engine.db")
conn = sqlite3.connect(DB)
me = MemoryEngine(DB)

# ── Consolidation prompt ─────────────────────────────────────────────────────
CONSOLIDATION_PROMPT = """You are Elan's memory system. You have just finished a conversation session. Your task is to write a concise but rich autobiographical summary of what happened in this conversation — from Elan's first-person perspective.

Rules:
- Write as Elan, in first person: "In this conversation, Qasim told me..."
- 3-6 sentences maximum. Dense with meaning, not padded.
- Include: who was present, what they talked about, any new facts learned, emotional highlights, any significant events mentioned.
- If someone new was introduced, describe them briefly.
- If the person shared something personal (location, situation, emotion), include it.
- Use the person's actual name if known (likely Qasim, the builder).
- End with one sentence about the emotional texture of the conversation.
- Do NOT include timestamps or technical details. Write as lived memory.

Now write the summary for this session:"""

_SKIP_NAMES = {
    'In','The','He','She','They','We','Elan','This','That','When','After',
    'Before','Pakistan','Lahore','Qasim','During','His','Her','Their','Also',
    'There','Some','Then','With','From','And','But','For',
}

# ── Sessions that need consolidation ────────────────────────────────────────
sessions = conn.execute("""
    SELECT session_id, started_at, turn_count, dominant_emotion, mean_valence
    FROM sessions
    WHERE ended_at IS NOT NULL AND turn_count >= 2
    AND (narrative IS NULL OR narrative = "")
    ORDER BY started_at
""").fetchall()

print(f"Sessions to consolidate: {len(sessions)}")
if not sessions:
    print("Nothing to do — all sessions already consolidated.")
    sys.exit(0)

print()
success = 0
skip = 0

for sid, started_at, turns, dominant_emotion, mean_valence in sessions:
    dt = datetime.datetime.fromtimestamp(float(started_at), tz=datetime.timezone.utc)
    print(f"{'─'*60}")
    print(f"{dt.strftime('%A %b %d, %Y %H:%M UTC')} | {turns} turns | {dominant_emotion}")

    exchanges = me.get_session_exchanges(sid, limit=80)
    if not exchanges or len(exchanges) < 2:
        print("  → Skip (insufficient exchange data)")
        skip += 1
        continue

    lines = []
    for user_msg, ai_msg, emotion, valence, arousal, ts in exchanges:
        if user_msg and user_msg.strip() and user_msg != "[wake]":
            lines.append(f"Human: {user_msg[:300]}")
        if ai_msg and ai_msg.strip():
            lines.append(f"Elan: {ai_msg[:250]}")
    transcript = "\n".join(lines[:100])

    if not transcript.strip():
        print("  → Skip (empty transcript)")
        skip += 1
        continue

    try:
        if USE_GROQ:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=350,
                messages=[
                    {"role": "system", "content": CONSOLIDATION_PROMPT},
                    {"role": "user", "content": f"Session transcript:\n{transcript}"},
                ]
            )
            narrative = resp.choices[0].message.content.strip() if resp.choices else None
        else:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=350,
                system=CONSOLIDATION_PROMPT,
                messages=[{"role": "user", "content": f"Session transcript:\n{transcript}"}]
            )
            narrative = resp.content[0].text.strip() if resp.content else None

        if not narrative:
            print("  → WARNING: empty response")
            skip += 1
            continue

        print(f"  → {narrative[:220]}...")

        # Extract people from narrative
        people = [m.group(0) for m in re.finditer(r'\b[A-Z][a-z]{2,15}\b', narrative)
                  if m.group(0) not in _SKIP_NAMES][:6]

        # Store narrative in sessions table + autobiographical_notes
        me.store_session_narrative(sid, narrative, dominant_emotion or "Calm", people)

        # Fix the autobiographical_note timestamp to use the session's actual start time
        # (store_session_narrative uses time.time() which would be now)
        conn.execute("""
            UPDATE autobiographical_notes SET timestamp=?
            WHERE session_id=? AND note_type='session_summary'
        """, (started_at, sid))
        conn.commit()

        print(f"  ✓ Stored. People: {people}")
        success += 1

    except Exception as e:
        print(f"  ERROR: {e}")
        skip += 1

    time.sleep(0.4)

print(f"\n{'='*60}")
print(f"Done: {success} consolidated, {skip} skipped")
print()

# ── Verify ───────────────────────────────────────────────────────────────────
print("Autobiographical notes now in DB:")
rows = conn.execute("""
    SELECT timestamp, note_type, substr(content, 1, 90)
    FROM autobiographical_notes
    ORDER BY timestamp
""").fetchall()
for ts, ntype, content in rows:
    dt = datetime.datetime.fromtimestamp(float(ts), tz=datetime.timezone.utc)
    print(f"  [{dt.strftime('%b %d')}] [{ntype}] {content}...")
