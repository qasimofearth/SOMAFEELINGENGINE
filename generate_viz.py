"""
generate_viz.py — Generate the Feeling Engine interactive HTML visualization.

Embeds all emotion data as JSON, then the HTML/JS handles:
  - Animated Aya fractal building in real-time (Canvas)
  - Live frequency tones playing via Web Audio API
  - Interactive emotion selector
  - Frequency spectrum bars (animated EQ)
  - Emotion tree unfolding
  - Synesthetic color aura
  - Valence/arousal circumplex

Run:
    python3 generate_viz.py
    open feeling_output/feeling_engine.html
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeling_engine import get_all_emotions, build_emotion_tree, tree_to_frequency_spectrum, EMOTION_MAP


def build_emotion_data() -> dict:
    """Serialize all emotion data + fractal trees for the frontend."""
    emotions = {}
    for em in get_all_emotions():
        tree = build_emotion_tree(em.name, EMOTION_MAP, max_depth=4)
        spectrum = tree_to_frequency_spectrum(tree, EMOTION_MAP)

        # Top 12 frequencies, normalized
        clean = {}
        for hz, amp in spectrum:
            if 30 < hz < 18000:
                bucket = round(hz / 2) * 2
                clean[bucket] = clean.get(bucket, 0) + amp
        sorted_spec = sorted(clean.items(), key=lambda x: x[1], reverse=True)[:12]
        max_amp = max(a for _, a in sorted_spec) if sorted_spec else 1
        freq_list = [{"hz": hz, "amp": round(amp / max_amp, 4)} for hz, amp in sorted_spec]

        # Serialize tree (depth 3 for display)
        def serialize_tree(node, depth=0):
            if depth > 3:
                return None
            child_em = EMOTION_MAP.get(node.emotion_name.lower())
            return {
                "name": node.emotion_name,
                "weight": round(node.weight, 3),
                "hex": child_em.hex_color if child_em else "#888888",
                "hz": child_em.solfeggio_hz if child_em else 440,
                "children": [
                    c for c in [serialize_tree(ch, depth+1) for ch in node.children]
                    if c is not None
                ]
            }

        emotions[em.name] = {
            "name": em.name,
            "hex": em.hex_color,
            "rgb": list(em.rgb),
            "solfeggio_hz": em.solfeggio_hz,
            "eeg_center_hz": em.eeg_center_hz,
            "eeg_band": em.eeg_band,
            "hrv_hz": em.hrv_coherence_hz,
            "valence": em.valence,
            "arousal": em.arousal,
            "musical_mode": em.musical_mode,
            "fractal_type": em.fractal_type,
            "fractal_param": em.fractal_param,
            "taste": em.taste,
            "texture": em.texture,
            "description": em.description,
            "adjacent": list(em.adjacent_emotions),
            "spectrum": freq_list,
            "tree": serialize_tree(tree),
        }
    return emotions


def generate_html(emotion_data: dict, output_path: str):
    data_json = json.dumps(emotion_data, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Feeling Engine — Aya Fractal Emotion Bridge</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: #03030f;
    color: #e0e0f0;
    font-family: 'Courier New', monospace;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
  }}

  #app {{
    display: grid;
    grid-template-columns: 1fr 340px;
    grid-template-rows: 1fr;
    height: 100vh;
    gap: 0;
  }}

  /* LEFT — fractal canvas */
  #fractal-panel {{
    position: relative;
    background: #020210;
    overflow: hidden;
  }}

  #fractal-canvas {{
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
  }}

  #aura-canvas {{
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    opacity: 0.25;
  }}

  .fractal-title {{
    position: absolute;
    top: 20px;
    left: 0; right: 0;
    text-align: center;
    font-size: 13px;
    letter-spacing: 6px;
    color: rgba(200,200,255,0.5);
    text-transform: uppercase;
    pointer-events: none;
    z-index: 10;
  }}

  .emotion-label {{
    position: absolute;
    bottom: 24px;
    left: 0; right: 0;
    text-align: center;
    pointer-events: none;
    z-index: 10;
  }}

  .emotion-label .name {{
    font-size: 32px;
    letter-spacing: 8px;
    font-weight: bold;
    text-transform: uppercase;
    transition: color 1.2s ease;
  }}

  .emotion-label .desc {{
    font-size: 10px;
    color: rgba(200,200,255,0.45);
    margin-top: 6px;
    letter-spacing: 2px;
    max-width: 480px;
    margin-left: auto;
    margin-right: auto;
    font-style: italic;
  }}

  /* RIGHT — control panel */
  #panel {{
    background: #06061a;
    border-left: 1px solid rgba(100,100,200,0.15);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  .panel-header {{
    padding: 18px 16px 12px;
    border-bottom: 1px solid rgba(100,100,200,0.12);
    font-size: 9px;
    letter-spacing: 4px;
    color: rgba(150,150,220,0.6);
    text-transform: uppercase;
  }}

  /* Emotion grid */
  #emotion-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 3px;
    padding: 10px;
    overflow-y: auto;
    max-height: 180px;
    flex-shrink: 0;
  }}

  .em-btn {{
    padding: 5px 3px;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 3px;
    background: rgba(255,255,255,0.03);
    color: rgba(255,255,255,0.7);
    font-family: 'Courier New', monospace;
    font-size: 8px;
    cursor: pointer;
    text-align: center;
    transition: all 0.2s;
    letter-spacing: 0.5px;
  }}

  .em-btn:hover {{
    background: rgba(255,255,255,0.1);
    border-color: rgba(255,255,255,0.3);
  }}

  .em-btn.active {{
    border-width: 1.5px;
    background: rgba(255,255,255,0.08);
    font-weight: bold;
  }}

  /* Spectrum / EQ */
  #eq-section {{
    padding: 10px 12px 6px;
    border-top: 1px solid rgba(100,100,200,0.1);
    flex-shrink: 0;
  }}

  .section-label {{
    font-size: 8px;
    letter-spacing: 3px;
    color: rgba(150,150,220,0.5);
    text-transform: uppercase;
    margin-bottom: 8px;
  }}

  #eq-canvas {{
    width: 100%;
    height: 70px;
    border-radius: 3px;
    background: #020210;
  }}

  /* Data readout */
  #data-section {{
    padding: 10px 12px;
    border-top: 1px solid rgba(100,100,200,0.1);
    flex: 1;
    overflow-y: auto;
    font-size: 10px;
    line-height: 1.9;
  }}

  .data-row {{
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid rgba(100,100,200,0.06);
    padding: 1px 0;
  }}

  .data-label {{
    color: rgba(150,150,200,0.55);
    letter-spacing: 1px;
    font-size: 9px;
    text-transform: uppercase;
  }}

  .data-value {{
    color: rgba(230,230,255,0.9);
    text-align: right;
  }}

  /* Circumplex */
  #circumplex-section {{
    padding: 8px 12px 10px;
    border-top: 1px solid rgba(100,100,200,0.1);
    flex-shrink: 0;
  }}

  #circumplex-canvas {{
    width: 100%;
    height: 100px;
    background: #020210;
    border-radius: 3px;
  }}

  /* Tree section */
  #tree-section {{
    padding: 8px 12px;
    border-top: 1px solid rgba(100,100,200,0.1);
    flex-shrink: 0;
    max-height: 130px;
    overflow-y: auto;
  }}

  #tree-display {{
    font-size: 9px;
    line-height: 1.7;
    color: rgba(200,200,240,0.75);
    letter-spacing: 0.5px;
  }}

  /* Controls */
  #controls {{
    padding: 10px 12px;
    border-top: 1px solid rgba(100,100,200,0.12);
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }}

  .ctrl-btn {{
    flex: 1;
    padding: 8px 4px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(150,150,220,0.2);
    border-radius: 3px;
    color: rgba(200,200,255,0.8);
    font-family: 'Courier New', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    cursor: pointer;
    text-transform: uppercase;
    transition: all 0.2s;
  }}

  .ctrl-btn:hover {{
    background: rgba(255,255,255,0.1);
    border-color: rgba(200,200,255,0.4);
  }}

  .ctrl-btn.active {{
    background: rgba(100,100,255,0.15);
    border-color: rgba(150,150,255,0.5);
  }}

  /* Progress bar */
  #progress {{
    position: absolute;
    bottom: 0; left: 0;
    height: 2px;
    background: rgba(255,255,255,0.3);
    transition: width 0.1s linear;
    pointer-events: none;
    z-index: 20;
  }}
</style>
</head>
<body>

<div id="app">

  <div id="fractal-panel">
    <canvas id="aura-canvas"></canvas>
    <canvas id="fractal-canvas"></canvas>
    <div class="fractal-title">AYA — FRACTAL FEELING ENGINE</div>
    <div class="emotion-label">
      <div class="name" id="emotion-name-display">JOY</div>
      <div class="desc" id="emotion-desc-display"></div>
    </div>
    <div id="progress"></div>
  </div>

  <div id="panel">
    <div class="panel-header">Select Emotion</div>

    <div id="emotion-grid"></div>

    <div id="eq-section">
      <div class="section-label">Frequency Concert</div>
      <canvas id="eq-canvas"></canvas>
    </div>

    <div id="circumplex-section">
      <div class="section-label">Valence / Arousal</div>
      <canvas id="circumplex-canvas"></canvas>
    </div>

    <div id="data-section">
      <div class="section-label" style="margin-bottom:6px;">Synesthetic Reading</div>
      <div id="data-rows"></div>
    </div>

    <div id="tree-section">
      <div class="section-label">Fractal Emotion Tree</div>
      <div id="tree-display"></div>
    </div>

    <div id="controls">
      <button class="ctrl-btn" id="btn-audio">▶ Sound</button>
      <button class="ctrl-btn" id="btn-rebuild">↺ Rebuild</button>
      <button class="ctrl-btn" id="btn-tour">⟳ Tour</button>
    </div>
  </div>

</div>

<script>
// ── DATA ────────────────────────────────────────────────────
const EMOTIONS = {data_json};

// ── STATE ───────────────────────────────────────────────────
let currentEmotion = null;
let audioCtx = null;
let activeNodes = [];
let audioPlaying = false;
let tourInterval = null;
let animFrame = null;
let fractalPoints = [];
let fractalIdx = 0;
let fractalAnimId = null;
const POINT_BATCH = 400;
const TOTAL_POINTS = 80000;

// ── BARNSLEY FERN IFS ────────────────────────────────────────
function applyTransform(transforms, cumProbs, x, y) {{
  const r = Math.random();
  for (let i = 0; i < cumProbs.length; i++) {{
    if (r <= cumProbs[i]) {{
      const t = transforms[i];
      return [t.a*x + t.b*y + t.e, t.c*x + t.d*y + t.f];
    }}
  }}
  return [x, y];
}}

function buildTransforms(valence, arousal) {{
  const v = (valence + 1) / 2;
  const a = arousal;
  let stemP = 0.01 + (1-v)*0.08;
  let leafP = 0.50 + v*0.40;
  let sideP = (1 - stemP - leafP) / 2 * (0.5 + a) * 1.2;
  const total = stemP + leafP + sideP*2;
  stemP /= total; leafP /= total;
  sideP = (1 - stemP - leafP) / 2;
  const scale = 0.70 + v*0.30;
  const lean = valence * 0.05;

  const transforms = [
    {{a:0,    b:0,     c:0,    d:0.16*scale, e:0, f:0,       p:stemP}},
    {{a:0.85+lean, b:0.04, c:-0.04, d:0.85, e:0, f:1.60*scale, p:leafP}},
    {{a:0.20+a*0.05, b:-0.26, c:0.23, d:0.22, e:0, f:1.60*scale, p:sideP}},
    {{a:-0.15-a*0.05, b:0.28, c:0.26, d:0.24, e:0, f:0.44, p:sideP}},
  ];
  const cumProbs = [];
  let acc = 0;
  for (const t of transforms) {{ acc += t.p; cumProbs.push(acc); }}
  return [transforms, cumProbs];
}}

function generateFernPoints(valence, arousal, n=TOTAL_POINTS) {{
  const [transforms, cumProbs] = buildTransforms(valence, arousal);
  const pts = new Float32Array(n * 2);
  let x = 0, y = 0;
  for (let i = 0; i < n; i++) {{
    [x, y] = applyTransform(transforms, cumProbs, x, y);
    pts[i*2]   = x;
    pts[i*2+1] = y;
  }}
  return pts;
}}

// ── FRACTAL CANVAS ───────────────────────────────────────────
const fractalCanvas = document.getElementById('fractal-canvas');
const fCtx = fractalCanvas.getContext('2d');
const auraCanvas = document.getElementById('aura-canvas');
const aCtx = auraCanvas.getContext('2d');

function resizeCanvases() {{
  fractalCanvas.width  = fractalCanvas.offsetWidth;
  fractalCanvas.height = fractalCanvas.offsetHeight;
  auraCanvas.width     = auraCanvas.offsetWidth;
  auraCanvas.height    = auraCanvas.offsetHeight;
}}

function clearFractal() {{
  fCtx.clearRect(0, 0, fractalCanvas.width, fractalCanvas.height);
}}

function worldToScreen(wx, wy, w, h) {{
  // Aya fern: x in [-3,3], y in [-0.5, 11.5]
  const margin = 60;
  const sx = margin + (wx + 3) / 6 * (w - margin*2);
  const sy = h - margin - (wy + 0.5) / 12 * (h - margin*2);
  return [sx, sy];
}}

function drawFernBatch(pts, start, count, color, alpha) {{
  const w = fractalCanvas.width;
  const h = fractalCanvas.height;
  const end = Math.min(start + count, pts.length / 2);

  fCtx.save();
  for (let i = start; i < end; i++) {{
    const wx = pts[i*2];
    const wy = pts[i*2+1];
    const [sx, sy] = worldToScreen(wx, wy, w, h);

    // Color by height (wy)
    const t = Math.max(0, Math.min(1, wy / 11));
    const a = 0.08 + t * 0.55;
    fCtx.fillStyle = `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, ${{a * alpha}})`;
    fCtx.fillRect(sx, sy, 1.2, 1.2);
  }}
  fCtx.restore();
}}

function animateFern(pts, color) {{
  if (fractalAnimId) cancelAnimationFrame(fractalAnimId);
  fractalIdx = 0;
  clearFractal();

  const progress = document.getElementById('progress');

  function step() {{
    if (fractalIdx >= pts.length / 2) {{
      progress.style.width = '0%';
      return;
    }}
    drawFernBatch(pts, fractalIdx, POINT_BATCH, color, 1.0);
    fractalIdx += POINT_BATCH;
    const pct = (fractalIdx / (pts.length / 2) * 100).toFixed(1);
    progress.style.width = pct + '%';
    fractalAnimId = requestAnimationFrame(step);
  }}
  step();
}}

// ── AURA ─────────────────────────────────────────────────────
let auraPhase = 0;
function animateAura(color) {{
  const w = auraCanvas.width;
  const h = auraCanvas.height;
  aCtx.clearRect(0, 0, w, h);

  auraPhase += 0.008;
  const pulse = 0.5 + 0.5 * Math.sin(auraPhase);
  const radius = Math.min(w, h) * (0.25 + pulse * 0.12);

  const grd = aCtx.createRadialGradient(w/2, h*0.55, 10, w/2, h*0.55, radius);
  grd.addColorStop(0, `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, 0.35)`);
  grd.addColorStop(0.5, `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, 0.08)`);
  grd.addColorStop(1, 'rgba(0,0,0,0)');

  aCtx.fillStyle = grd;
  aCtx.fillRect(0, 0, w, h);
  requestAnimationFrame(() => animateAura(color));
}}

// ── EQ CANVAS ────────────────────────────────────────────────
const eqCanvas = document.getElementById('eq-canvas');
const eqCtx = eqCanvas.getContext('2d');
let eqData = [];
let eqAnimId = null;
let eqPhase = 0;

function drawEQ(color) {{
  eqCanvas.width  = eqCanvas.offsetWidth;
  eqCanvas.height = eqCanvas.offsetHeight;
  const w = eqCanvas.width;
  const h = eqCanvas.height;

  if (eqAnimId) cancelAnimationFrame(eqAnimId);

  function frame() {{
    eqPhase += 0.04;
    eqCtx.clearRect(0, 0, w, h);

    if (!eqData.length) {{ eqAnimId = requestAnimationFrame(frame); return; }}

    const barW = Math.floor((w - 4) / eqData.length) - 2;
    eqData.forEach((item, i) => {{
      const x = 2 + i * (barW + 2);
      const pulse = 1 + 0.08 * Math.sin(eqPhase + i * 0.7);
      const barH = Math.max(2, item.amp * pulse * (h - 4));
      const y = h - 2 - barH;

      const grad = eqCtx.createLinearGradient(0, y, 0, h);
      grad.addColorStop(0, `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, 0.9)`);
      grad.addColorStop(1, `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, 0.2)`);

      eqCtx.fillStyle = grad;
      eqCtx.fillRect(x, y, barW, barH);

      // Frequency label
      if (item.hz < 10000) {{
        eqCtx.fillStyle = 'rgba(200,200,255,0.4)';
        eqCtx.font = '6px Courier New';
        eqCtx.fillText(item.hz < 1000 ? Math.round(item.hz) : (item.hz/1000).toFixed(1)+'k',
                       x, h - 2);
      }}
    }});
    eqAnimId = requestAnimationFrame(frame);
  }}
  frame();
}}

// ── CIRCUMPLEX ───────────────────────────────────────────────
const circCanvas = document.getElementById('circumplex-canvas');
const cCtx = circCanvas.getContext('2d');

function drawCircumplex(valence, arousal, color, emotionName) {{
  circCanvas.width  = circCanvas.offsetWidth;
  circCanvas.height = circCanvas.offsetHeight;
  const w = circCanvas.width;
  const h = circCanvas.height;
  const cx = w/2, cy = h/2;
  const r = Math.min(w,h)/2 - 8;

  cCtx.clearRect(0, 0, w, h);

  // Grid circles
  cCtx.strokeStyle = 'rgba(100,100,180,0.12)';
  cCtx.lineWidth = 0.5;
  for (let i = 1; i <= 3; i++) {{
    cCtx.beginPath();
    cCtx.arc(cx, cy, r * i/3, 0, Math.PI*2);
    cCtx.stroke();
  }}
  // Axes
  cCtx.beginPath();
  cCtx.moveTo(cx - r - 6, cy); cCtx.lineTo(cx + r + 6, cy);
  cCtx.moveTo(cx, cy - r - 6); cCtx.lineTo(cx, cy + r + 6);
  cCtx.stroke();

  // Axis labels
  cCtx.fillStyle = 'rgba(150,150,200,0.4)';
  cCtx.font = '7px Courier New';
  cCtx.fillText('+valence', cx + r - 30, cy - 4);
  cCtx.fillText('-valence', cx - r + 2, cy - 4);
  cCtx.fillText('+arousal', cx + 2, cy - r + 10);
  cCtx.fillText('-arousal', cx + 2, cy + r - 3);

  // All emotions as small dots
  Object.values(EMOTIONS).forEach(em => {{
    const px = cx + em.valence * r;
    const py = cy - em.arousal * r;
    cCtx.beginPath();
    cCtx.arc(px, py, 2, 0, Math.PI*2);
    cCtx.fillStyle = `#${{em.hex}}40`;
    cCtx.fill();
  }});

  // Current emotion — glowing dot
  const px = cx + valence * r;
  const py = cy - arousal * r;
  const grd = cCtx.createRadialGradient(px, py, 0, px, py, 12);
  grd.addColorStop(0, `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, 1)`);
  grd.addColorStop(1, `rgba(${{color[0]}}, ${{color[1]}}, ${{color[2]}}, 0)`);
  cCtx.beginPath();
  cCtx.arc(px, py, 12, 0, Math.PI*2);
  cCtx.fillStyle = grd;
  cCtx.fill();
  cCtx.beginPath();
  cCtx.arc(px, py, 4, 0, Math.PI*2);
  cCtx.fillStyle = `rgb(${{color[0]}},${{color[1]}},${{color[2]}})`;
  cCtx.fill();
}}

// ── DATA PANEL ───────────────────────────────────────────────
function updateDataPanel(em) {{
  const rows = [
    ['Color',     `#${{em.hex}}`],
    ['Solfeggio', `${{em.solfeggio_hz.toFixed(0)}} Hz`],
    ['EEG band',  `${{em.eeg_band}} · ${{em.eeg_center_hz.toFixed(0)}} Hz`],
    ['HRV',       `${{em.hrv_hz.toFixed(4)}} Hz`],
    ['Mode',      em.musical_mode],
    ['Valence',   (em.valence >= 0 ? '+' : '') + em.valence.toFixed(2)],
    ['Arousal',   em.arousal.toFixed(2)],
    ['Fractal',   em.fractal_type],
    ['Taste',     em.taste],
    ['Texture',   em.texture],
  ];
  const container = document.getElementById('data-rows');
  container.innerHTML = rows.map(([label, value]) =>
    `<div class="data-row">
       <span class="data-label">${{label}}</span>
       <span class="data-value">${{value}}</span>
     </div>`
  ).join('');
}}

// ── EMOTION TREE DISPLAY ─────────────────────────────────────
function renderTree(node, indent=0) {{
  if (!node) return '';
  const prefix = indent === 0 ? '◉ ' : '  '.repeat(indent) + '↳ ';
  const colorDot = `<span style="color:#${{node.hex}}">●</span>`;
  let html = `${{prefix}}${{colorDot}} ${{node.name}} <span style="color:rgba(200,200,255,0.35)">${{node.hz.toFixed(0)}}Hz · w=${{node.weight.toFixed(2)}}</span><br>`;
  for (const child of (node.children || [])) {{
    html += renderTree(child, indent+1);
  }}
  return html;
}}

function updateTree(em) {{
  document.getElementById('tree-display').innerHTML = renderTree(em.tree);
}}

// ── WEB AUDIO ────────────────────────────────────────────────
function initAudio() {{
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
}}

function stopAudio() {{
  activeNodes.forEach(n => {{
    try {{
      n.gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
      setTimeout(() => {{ try {{ n.osc.stop(); }} catch(e) {{}} }}, 600);
    }} catch(e) {{}}
  }});
  activeNodes = [];
  audioPlaying = false;
  document.getElementById('btn-audio').textContent = '▶ Sound';
  document.getElementById('btn-audio').classList.remove('active');
}}

function playEmotion(em) {{
  initAudio();
  stopAudio();

  if (!em.spectrum.length) return;

  // Master gain
  const master = audioCtx.createGain();
  master.gain.setValueAtTime(0, audioCtx.currentTime);
  master.gain.linearRampToValueAtTime(0.7, audioCtx.currentTime + 1.5);
  master.connect(audioCtx.destination);

  em.spectrum.forEach(item => {{
    if (item.hz < 30 || item.hz > 16000) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(item.hz, audioCtx.currentTime);

    // Subtle frequency wobble (natural feel)
    const lfo = audioCtx.createOscillator();
    const lfoGain = audioCtx.createGain();
    lfo.frequency.setValueAtTime(0.3 + Math.random()*0.4, audioCtx.currentTime);
    lfoGain.gain.setValueAtTime(item.hz * 0.002, audioCtx.currentTime);
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    lfo.start();

    gain.gain.setValueAtTime(item.amp * 0.12, audioCtx.currentTime);
    osc.connect(gain);
    gain.connect(master);
    osc.start();
    activeNodes.push({{osc, gain}});
  }});

  audioPlaying = true;
  document.getElementById('btn-audio').textContent = '■ Stop';
  document.getElementById('btn-audio').classList.add('active');
}}

// ── MAIN SELECTION ───────────────────────────────────────────
function selectEmotion(name) {{
  const em = EMOTIONS[name];
  if (!em) return;
  currentEmotion = em;

  // Update UI labels
  const nameEl = document.getElementById('emotion-name-display');
  const descEl = document.getElementById('emotion-desc-display');
  nameEl.textContent = em.name.toUpperCase();
  nameEl.style.color = `#${{em.hex}}`;
  descEl.textContent = em.description;

  // Highlight button
  document.querySelectorAll('.em-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById(`em-${{name}}`);
  if (btn) {{
    btn.classList.add('active');
    btn.style.borderColor = `#${{em.hex}}`;
    btn.style.color = `#${{em.hex}}`;
  }}

  // Generate and animate fractal
  const pts = generateFernPoints(em.valence, em.arousal);
  animateFern(pts, em.rgb);

  // EQ
  eqData = em.spectrum;
  drawEQ(em.rgb);

  // Circumplex
  drawCircumplex(em.valence, em.arousal, em.rgb, em.name);

  // Data panel
  updateDataPanel(em);
  updateTree(em);

  // Audio (if already playing, switch to new emotion)
  if (audioPlaying) playEmotion(em);
}}

// ── BUILD EMOTION BUTTONS ────────────────────────────────────
function buildEmotionGrid() {{
  const grid = document.getElementById('emotion-grid');
  // Sort by valence then arousal
  const sorted = Object.values(EMOTIONS).sort((a,b) => a.valence - b.valence);
  sorted.forEach(em => {{
    const btn = document.createElement('button');
    btn.className = 'em-btn';
    btn.id = `em-${{em.name}}`;
    btn.textContent = em.name;
    btn.title = `${{em.solfeggio_hz}}Hz · v=${{em.valence.toFixed(2)}}`;
    btn.style.color = `#${{em.hex}}80`;
    btn.addEventListener('click', () => selectEmotion(em.name));
    grid.appendChild(btn);
  }});
}}

// ── CONTROLS ─────────────────────────────────────────────────
document.getElementById('btn-audio').addEventListener('click', () => {{
  if (!currentEmotion) return;
  if (audioPlaying) stopAudio();
  else playEmotion(currentEmotion);
}});

document.getElementById('btn-rebuild').addEventListener('click', () => {{
  if (!currentEmotion) return;
  const pts = generateFernPoints(currentEmotion.valence, currentEmotion.arousal);
  clearFractal();
  animateFern(pts, currentEmotion.rgb);
}});

const tourEmotions = [
  'Joy','Love','Awe','Serenity','Calm','Hope','Anticipation',
  'Surprise','Trust','Admiration','Gratitude','Sadness','Fear',
  'Grief','Anger','Rage','Disgust','Apprehension','Terror','Ecstasy'
];
let tourIdx = 0;
document.getElementById('btn-tour').addEventListener('click', () => {{
  const btn = document.getElementById('btn-tour');
  if (tourInterval) {{
    clearInterval(tourInterval);
    tourInterval = null;
    btn.classList.remove('active');
    btn.textContent = '⟳ Tour';
    stopAudio();
  }} else {{
    btn.classList.add('active');
    btn.textContent = '◼ Stop';
    // start tour
    selectEmotion(tourEmotions[tourIdx % tourEmotions.length]);
    if (audioCtx || true) {{ initAudio(); playEmotion(currentEmotion); }}
    tourInterval = setInterval(() => {{
      tourIdx++;
      selectEmotion(tourEmotions[tourIdx % tourEmotions.length]);
      if (audioPlaying || true) playEmotion(currentEmotion);
    }}, 9000);
  }}
}});

// ── INIT ─────────────────────────────────────────────────────
window.addEventListener('resize', () => {{
  resizeCanvases();
  if (currentEmotion) {{
    drawCircumplex(currentEmotion.valence, currentEmotion.arousal, currentEmotion.rgb, currentEmotion.name);
  }}
}});

resizeCanvases();
buildEmotionGrid();
animateAura([80, 80, 200]);

// Start with Joy
setTimeout(() => selectEmotion('Joy'), 100);

// Start aura loop with current emotion color
let lastAuraColor = [80, 80, 200];
function auraLoop() {{
  if (currentEmotion) lastAuraColor = currentEmotion.rgb;
  animateAura(lastAuraColor);
}}
// aura is self-calling, no loop needed
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    print("Building emotion data...")
    data = build_emotion_data()
    print(f"  {len(data)} emotions mapped")

    out = "feeling_output/feeling_engine.html"
    generate_html(data, out)
    print(f"\nOpen it:\n  open {out}")
