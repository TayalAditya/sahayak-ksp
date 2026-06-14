import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { sendMessage } from './api';
import './App.css';

/* ════════════════════════════════════════════════════════════
   Sahayak — KSP Crime Intelligence Command Center
   ════════════════════════════════════════════════════════════ */

const nf = new Intl.NumberFormat('en-IN');
const fmt = (n) => (n == null || isNaN(n) ? '—' : nf.format(Math.round(n)));
const SERIES = ['#3b82f6', '#22d3ee', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#60a5fa', '#fbbf24', '#2dd4bf', '#fb7185'];

/* ── Icons ──────────────────────────────────────────────── */
const Emblem = ({ size = 30 }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
    <defs>
      <linearGradient id="emg" x1="0" y1="0" x2="40" y2="40">
        <stop offset="0" stopColor="#60a5fa" /><stop offset="1" stopColor="#2563eb" />
      </linearGradient>
    </defs>
    <path d="M20 2.5 5 8.5v9c0 9.4 6.3 16.9 15 20 8.7-3.1 15-10.6 15-20v-9L20 2.5Z"
      fill="url(#emg)" fillOpacity="0.14" stroke="url(#emg)" strokeWidth="1.6" strokeLinejoin="round" />
    <path d="M20 11.5 23 18l6.5.4-5 4.2 1.7 6.3L20 25.4 13.8 28.9l1.7-6.3-5-4.2 6.5-.4 3-6.5Z"
      fill="url(#emg)" />
  </svg>
);
const IconSend = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);
const IconMic = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0 0 14 0M12 19v3M8 22h8" />
  </svg>
);
const IconChevron = ({ up }) => (
  <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    {up ? <path d="M2 8l4-4 4 4" /> : <path d="M2 4l4 4 4-4" />}
  </svg>
);
const IconAlert = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);
const IconShield = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" />
  </svg>
);
const IconPlus = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);
const IconCopy = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);
const IconDb = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5" /><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3" />
  </svg>
);
const IconMenu = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);
const IconTheme = ({ dark }) => (
  dark ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4.5" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
    </svg>
  )
);

/* ── Preset queries ─────────────────────────────────────── */
const PRESETS = [
  { label: 'Crime distribution', desc: 'Top crime types by FIR count', q: 'What are the top 10 crime types by number of FIRs?' },
  { label: 'District hotspots', desc: 'Areas with highest crime density', q: 'Which 5 districts have the most FIRs?' },
  { label: 'Repeat offenders', desc: 'Habitual criminals by case count', q: 'Show the top 5 repeat offenders by number of cases' },
  { label: 'Annual trend', desc: 'FIR volume year-over-year', q: 'Show FIR trend by year' },
  { label: 'IPC vs BNS split', desc: 'Legal code transition after Jul 2024', q: 'How many FIRs are registered under IPC vs BNS?' },
  { label: 'Bail status', desc: 'Custody and bail breakdown', q: 'What is the bail status breakdown for arrested accused?' },
];

/* ════════════════════════════════════════════════════════════
   Data → chart inference
   ════════════════════════════════════════════════════════════ */
function analyze(columns, rows) {
  if (!rows?.length || !columns?.length) return null;
  const isNum = (v) => v !== null && v !== '' && !isNaN(Number(v));
  const isYear = (c) => rows.every((r) => /^(19|20)\d{2}$/.test(String(r[c] ?? '').trim()));
  const temporalCol = columns.find((c) => /^(year|month|date|yr|qtr|quarter|week|period|fy)$|_(year|month|date)$/i.test(c) || isYear(c));

  const numericCols = columns.filter((c) => c !== temporalCol && rows.every((r) => isNum(r[c])));
  // Label = an explicit temporal column (even if numeric), else first non-numeric column
  const labelCol = temporalCol || columns.find((c) => !numericCols.includes(c));
  if (!labelCol || !numericCols.length) return null;

  // Prefer a count-like numeric column for the value
  const valueCol =
    numericCols.find((c) => /count|total|cnt|num|firs?|cases?|n_|qty|freq/i.test(c)) || numericCols[0];

  const data = rows
    .map((r) => ({ label: String(r[labelCol] ?? '').trim(), value: Number(r[valueCol]) }))
    .filter((d) => d.label && !isNaN(d.value));
  if (data.length < 2) return null;

  const temporal = !!temporalCol;
  const splitLike = /status|split|type|code|category|class|gender|law|section|act/i.test(labelCol);

  let type;
  if (temporal && data.length >= 3) type = 'line';
  else if (splitLike && data.length <= 6) type = 'donut';
  else type = 'bar';

  let series = data;
  if (type === 'bar' || type === 'donut') series = [...data].sort((a, b) => b.value - a.value);
  if (type === 'bar') series = series.slice(0, 10);

  const total = data.reduce((s, d) => s + d.value, 0);
  return { type, series, total, labelCol, valueCol, count: data.length };
}

function buildKpis(a) {
  if (!a) return [];
  const { type, series, total, valueCol, count } = a;
  const metric = /count|fir|case/i.test(valueCol) ? 'records' : valueCol.replace(/_/g, ' ');
  const tiles = [];
  if (type === 'line') {
    const first = series[0], last = series[series.length - 1];
    const peak = series.reduce((m, d) => (d.value > m.value ? d : m), series[0]);
    const delta = first.value ? ((last.value - first.value) / first.value) * 100 : 0;
    tiles.push({ value: fmt(total), label: `total ${metric}`, sub: `${count} periods` });
    tiles.push({ value: fmt(peak.value), label: 'peak period', sub: peak.label, accent: true });
    tiles.push({ value: `${delta >= 0 ? '+' : ''}${delta.toFixed(0)}%`, label: 'net change', sub: `${first.label} → ${last.label}`, tone: delta >= 0 ? 'up' : 'down' });
  } else {
    const top = series[0];
    const share = total ? (top.value / total) * 100 : 0;
    tiles.push({ value: fmt(total), label: `total ${metric}`, sub: `${count} categories` });
    tiles.push({ value: fmt(top.value), label: 'highest', sub: top.label, accent: true });
    tiles.push({ value: `${share.toFixed(1)}%`, label: 'top share', sub: `of all ${metric}` });
  }
  return tiles;
}

/* Pull quoted example prompts out of a guidance/refusal message (question mark optional) */
function extractSuggestions(text) {
  if (!text) return [];
  const out = [];
  const re = /["“”]([^"“”\n]{6,140})["“”]/g;
  let m;
  while ((m = re.exec(text)) !== null && out.length < 8) {
    const s = m[1].trim();
    if (s && !out.includes(s)) out.push(s);
  }
  return out;
}

/* Strip the harsh "Unable to answer:" prefix and bullet examples (shown as chips) */
function cleanAnswer(text, stripExamples) {
  let t = (text || '').replace(/^\s*Unable to answer:\s*/i, '');
  if (stripExamples) t = t.split('\n').filter((l) => !/^\s*[—–-]\s*["“”]/.test(l)).join('\n');
  return t.trim();
}

/* ════════════════════════════════════════════════════════════
   Charts (hand-built, zero dependencies)
   ════════════════════════════════════════════════════════════ */
function BarChart({ series }) {
  const max = Math.max(...series.map((d) => d.value)) || 1;
  return (
    <div className="bars">
      {series.map((d, i) => (
        <div className="bar-row" key={i}>
          <div className="bar-label" title={d.label}>{d.label}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(d.value / max) * 100}%`, animationDelay: `${i * 45}ms`, background: `linear-gradient(90deg, ${SERIES[0]}, ${SERIES[i % 2 ? 1 : 6]})` }} />
          </div>
          <div className="bar-val">{fmt(d.value)}</div>
        </div>
      ))}
    </div>
  );
}

function LineChart({ series }) {
  const W = 680, H = 240, pad = { t: 18, r: 18, b: 30, l: 46 };
  const innerW = W - pad.l - pad.r, innerH = H - pad.t - pad.b;
  const max = Math.max(...series.map((d) => d.value)) || 1;
  const niceMax = Math.ceil(max / 4) * 4 || 4;
  const x = (i) => pad.l + (series.length === 1 ? innerW / 2 : (i / (series.length - 1)) * innerW);
  const y = (v) => pad.t + innerH - (v / niceMax) * innerH;
  const pts = series.map((d, i) => `${x(i)},${y(d.value)}`).join(' ');
  const area = `M ${x(0)},${pad.t + innerH} L ${pts.replace(/ /g, ' L ')} L ${x(series.length - 1)},${pad.t + innerH} Z`;
  const ticks = [0, 1, 2, 3, 4].map((k) => (niceMax / 4) * k);
  const step = Math.ceil(series.length / 8);
  return (
    <div className="chart-svg-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="lg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3b82f6" stopOpacity="0.35" />
            <stop offset="1" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={pad.l} y1={y(t)} x2={W - pad.r} y2={y(t)} className="grid-line" />
            <text x={pad.l - 8} y={y(t) + 3} className="axis-label" textAnchor="end">{fmt(t)}</text>
          </g>
        ))}
        <path d={area} fill="url(#lg)" />
        <polyline points={pts} fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {series.map((d, i) => (
          <g key={i}>
            <circle cx={x(i)} cy={y(d.value)} r="3.5" className="dot-core" stroke="#60a5fa" strokeWidth="2" />
            {i % step === 0 && <text x={x(i)} y={H - 10} className="axis-label" textAnchor="middle">{d.label}</text>}
          </g>
        ))}
      </svg>
    </div>
  );
}

function DonutChart({ series, total }) {
  const R = 56, sw = 20, C = 2 * Math.PI * R, cx = 70, cy = 70;
  let acc = 0;
  const segs = series.map((d, i) => {
    const frac = total ? d.value / total : 0;
    const seg = { color: SERIES[i % SERIES.length], dash: frac * C, offset: -acc * C, frac, ...d };
    acc += frac;
    return seg;
  });
  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 140 140" className="donut">
        <circle cx={cx} cy={cy} r={R} fill="none" className="donut-track" strokeWidth={sw} />
        {segs.map((s, i) => (
          <circle key={i} cx={cx} cy={cy} r={R} fill="none" stroke={s.color} strokeWidth={sw}
            strokeDasharray={`${s.dash} ${C - s.dash}`} strokeDashoffset={s.offset}
            transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="butt" className="donut-seg" />
        ))}
        <text x={cx} y={cy - 4} className="donut-total" textAnchor="middle">{fmt(total)}</text>
        <text x={cx} y={cy + 12} className="donut-cap" textAnchor="middle">total</text>
      </svg>
      <div className="legend">
        {segs.map((s, i) => (
          <div className="legend-row" key={i}>
            <span className="legend-dot" style={{ background: s.color }} />
            <span className="legend-label" title={s.label}>{s.label}</span>
            <span className="legend-val">{fmt(s.value)}</span>
            <span className="legend-pct">{(s.frac * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const CHART_CAPTION = { bar: 'Ranking', line: 'Trend over time', donut: 'Breakdown' };
function Chart({ a }) {
  if (!a) return null;
  return (
    <div className="chart">
      <div className="chart-cap">{CHART_CAPTION[a.type]}</div>
      {a.type === 'bar' && <BarChart series={a.series} />}
      {a.type === 'line' && <LineChart series={a.series} />}
      {a.type === 'donut' && <DonutChart series={a.series} total={a.total} />}
    </div>
  );
}

/* ── Evidence (audit) panel ─────────────────────────────── */
function EvidencePanel({ sql, columns, rows, rowCount }) {
  return (
    <div className="evidence-panel">
      {sql && (
        <div className="evidence-block">
          <div className="evidence-block-head"><IconDb /> Query executed against CCTNS</div>
          <div className="evidence-block-body"><div className="sql-code">{sql}</div></div>
        </div>
      )}
      {rows?.length > 0 && (
        <div className="evidence-block">
          <div className="evidence-block-head"><IconShield /> Source records</div>
          <div className="evidence-block-body">
            <div className="row-count">{fmt(rowCount)} total — showing {Math.min(rows.length, 10)}</div>
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {rows.slice(0, 10).map((r, i) => (
                    <tr key={i}>{columns.map((c) => <td key={c} title={String(r[c] ?? '')}>{String(r[c] ?? '')}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Result card ────────────────────────────────────────── */
function ResultCard({ msg, onAsk }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const hasEvidence = !!(msg.sql || msg.rows?.length > 0);
  const a = useMemo(() => (msg.isError ? null : analyze(msg.columns, msg.rows)), [msg]);
  const kpis = useMemo(() => buildKpis(a), [a]);
  const suggestions = useMemo(() => extractSuggestions(msg.answer), [msg.answer]);

  // A no-data message with example prompts is guidance, not a hard failure — even if the backend flagged it as an error.
  const isGuidance = !hasEvidence && suggestions.length > 0;
  const showError = msg.isError && !isGuidance;

  const copy = () => {
    navigator.clipboard?.writeText(msg.answer || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  const html = cleanAnswer(msg.answer, isGuidance)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');

  return (
    <div className="row row-answer">
      <div className="row-inner">
        <div className="card">
          <div className="card-head">
            <span className="ans-brand"><Emblem size={18} /> Sahayak</span>
            {hasEvidence && !showError && (
              <span className="grounded-chip"><IconShield /> Grounded{msg.rowCount ? ` · ${fmt(msg.rowCount)} records` : ''}</span>
            )}
          </div>

          {showError ? (
            <div className="answer-error"><IconAlert /> {msg.answer}</div>
          ) : (
            <>
              {kpis.length > 0 && (
                <div className="kpi-row">
                  {kpis.map((k, i) => (
                    <div className={`kpi${k.accent ? ' kpi-accent' : ''}`} key={i}>
                      <div className={`kpi-val${k.tone ? ` tone-${k.tone}` : ''}`}>{k.value}</div>
                      <div className="kpi-label">{k.label}</div>
                      {k.sub && <div className="kpi-sub" title={k.sub}>{k.sub}</div>}
                    </div>
                  ))}
                </div>
              )}
              {a && <Chart a={a} />}
              <div className="answer-text" dangerouslySetInnerHTML={{ __html: html }} />
              {isGuidance && (
                <div className="suggest-row">
                  {suggestions.map((s, i) => (
                    <button className="suggest-chip" key={i} onClick={() => onAsk?.(s)}>{s}</button>
                  ))}
                </div>
              )}
            </>
          )}

          {hasEvidence && !showError && (
            <div className="card-actions">
              <button className="evidence-toggle" onClick={() => setOpen((v) => !v)}>
                <IconChevron up={open} />
                {open ? 'Hide evidence trail' : `Evidence trail${msg.rowCount ? ` — ${fmt(msg.rowCount)} records` : ''}`}
              </button>
              <button className="ghost-btn" onClick={copy}><IconCopy /> {copied ? 'Copied' : 'Copy'}</button>
            </div>
          )}
          {open && <EvidencePanel sql={msg.sql} columns={msg.columns} rows={msg.rows} rowCount={msg.rowCount} />}
        </div>
      </div>
    </div>
  );
}

const THEME_KEY = 'sahayak-theme';
const SpeechRec = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;

/* ════════════════════════════════════════════════════════════
   App
   ════════════════════════════════════════════════════════════ */
export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState('EN');
  const [navOpen, setNavOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || 'light');
  const [listening, setListening] = useState(false);
  const bottomRef = useRef();
  const inputRef = useRef();
  const recogRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);
  useEffect(() => () => recogRef.current?.abort(), []);

  const toggleVoice = useCallback(() => {
    if (!SpeechRec) return;
    if (listening) { recogRef.current?.stop(); return; }
    const recog = new SpeechRec();
    recog.lang = lang === 'KN' ? 'kn-IN' : 'en-IN';
    recog.interimResults = true;
    recog.continuous = false;
    recog.onresult = (e) => {
      let t = '';
      for (let i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
      setInput(t);
    };
    recog.onend = () => { setListening(false); recogRef.current = null; setTimeout(() => inputRef.current?.focus(), 50); };
    recog.onerror = () => { setListening(false); recogRef.current = null; };
    recogRef.current = recog;
    setListening(true);
    recog.start();
  }, [listening, lang]);

  const history = useMemo(
    () => messages.filter((m) => m.role === 'query').map((m) => m.text).reverse(),
    [messages]
  );

  const submit = useCallback(async (question) => {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setNavOpen(false);
    setMessages((m) => [...m, { role: 'query', text: q }]);
    setInput('');
    setLoading(true);
    try {
      const data = await sendMessage(q, sessionId);
      setSessionId(data.session_id);
      setMessages((m) => [...m, {
        role: 'answer',
        answer: data.error ? `Unable to answer: ${data.error}` : data.answer,
        sql: data.sql, columns: data.columns ?? [], rows: data.rows ?? [],
        rowCount: data.row_count, isError: !!data.error,
      }]);
    } catch {
      setMessages((m) => [...m, { role: 'answer', answer: 'Network error — make sure the backend is running on port 8000.', isError: true }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [input, loading, sessionId]);

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } };

  const placeholder = listening
    ? (lang === 'EN' ? 'Listening… speak your question' : 'ಕೇಳುತ್ತಿದೆ… ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಹೇಳಿ')
    : (lang === 'EN' ? 'Ask about FIRs, suspects, hotspots, trends…' : 'ಎಫ್‌ಐಆರ್, ಶಂಕಿತರು, ಪ್ರವೃತ್ತಿಗಳ ಬಗ್ಗೆ ಕೇಳಿ…');

  return (
    <div className="app">
      {/* Sidebar */}
      {navOpen && <div className="scrim" onClick={() => setNavOpen(false)} />}
      <aside className={`sidebar${navOpen ? ' open' : ''}`}>
        <div className="side-brand">
          <Emblem size={32} />
          <div className="side-brand-text">
            <div className="side-name">ಸಹಾಯಕ <span>Sahayak</span></div>
            <div className="side-org">SCRB · Karnataka State Police</div>
          </div>
        </div>

        <button className="new-query" onClick={() => { setMessages([]); setSessionId(null); setNavOpen(false); setTimeout(() => inputRef.current?.focus(), 50); }}>
          <IconPlus /> New query
        </button>

        <div className="side-section">
          <div className="side-label">Session history</div>
          {history.length === 0
            ? <div className="side-empty">No queries yet</div>
            : history.slice(0, 12).map((h, i) => (
                <button className="side-history" key={i} onClick={() => submit(h)} title={h}>{h}</button>
              ))}
        </div>

      </aside>

      {/* Main column */}
      <div className="main-col">
        <header className="topbar">
          <button className="menu-btn" onClick={() => setNavOpen((v) => !v)} aria-label="Menu"><IconMenu /></button>
          <span className="topbar-title">Crime Intelligence Platform</span>
          <div className="topbar-right">
            <button className="icon-btn" onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'} aria-label="Toggle theme">
              <IconTheme dark={theme === 'dark'} />
            </button>
            <div className="lang-group">
              <button className={`lang-pill${lang === 'EN' ? ' active' : ''}`} onClick={() => setLang('EN')}>EN</button>
              <button className={`lang-pill${lang === 'KN' ? ' active' : ''}`} onClick={() => setLang('KN')}>ಕನ್ನಡ</button>
            </div>
          </div>
        </header>

        <div className="feed">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-eyebrow">Karnataka State Police · State Crime Records Bureau</div>
              <h1 className="empty-title">{lang === 'EN' ? 'Query crime intelligence in plain language' : 'ಸಾಮಾನ್ಯ ಭಾಷೆಯಲ್ಲಿ ಅಪರಾಧ ಮಾಹಿತಿ ಪ್ರಶ್ನಿಸಿ'}</h1>
              <p className="empty-sub">
                {lang === 'EN'
                  ? 'Ask about FIRs, accused, locations and patterns. Every answer is grounded in real records, visualised, and backed by a full evidence trail.'
                  : 'ಎಫ್‌ಐಆರ್‌ಗಳು, ಆರೋಪಿಗಳು, ಸ್ಥಳಗಳು ಮತ್ತು ಮಾದರಿಗಳ ಬಗ್ಗೆ ಕೇಳಿ. ಪ್ರತಿ ಉತ್ತರವೂ ನೈಜ ದಾಖಲೆಗಳ ಆಧಾರಿತ.'}
              </p>
              <div className="queries-label">Common queries</div>
              <div className="queries-grid">
                {PRESETS.map((p) => (
                  <button key={p.q} className="query-card" onClick={() => submit(p.q)}>
                    <div className="query-card-label">{p.label}</div>
                    <div className="query-card-desc">{p.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === 'query' ? (
              <div key={i} className="row row-query">
                <div className="row-inner">
                  <div className="query-header">
                    <span className="query-tag">Query</span>
                    <span className="query-text">{m.text}</span>
                  </div>
                </div>
              </div>
            ) : (
              <ResultCard key={i} msg={m} onAsk={submit} />
            )
          )}

          {loading && (
            <div className="row row-answer">
              <div className="row-inner">
                <div className="card thinking">
                  <div className="thinking-dots"><span /><span /><span /></div>
                  <span className="thinking-label">Translating to query · running against CCTNS…</span>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-area">
          <div className="input-inner">
            <div className="input-row">
              <div className="input-wrap">
                <textarea ref={inputRef} className={`input-field${SpeechRec ? ' has-mic' : ''}`} rows={1} value={input}
                  onChange={(e) => setInput(e.target.value)} onKeyDown={onKey}
                  placeholder={placeholder} disabled={loading} />
                {SpeechRec && (
                  <button type="button" className={`voice-btn-inner${listening ? ' listening' : ''}`}
                    onClick={toggleVoice} title={listening ? 'Stop listening' : `Voice input · ${lang === 'KN' ? 'ಕನ್ನಡ' : 'English'}`}
                    aria-label="Voice input">
                    <IconMic />
                  </button>
                )}
              </div>
              <button className="send-btn" onClick={() => submit()} disabled={loading || !input.trim()}>
                <IconSend /> Send
              </button>
            </div>
            <div className="input-meta">
              <span><kbd>Enter</kbd> send</span>
              <span><kbd>Shift</kbd>+<kbd>Enter</kbd> new line</span>
              <span className="meta-spacer" />
              <span className="meta-note">Answers grounded in source records · audit-logged</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
