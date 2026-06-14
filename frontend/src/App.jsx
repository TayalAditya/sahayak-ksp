import { useState, useRef, useEffect, useCallback } from 'react';
import { sendMessage } from './api';
import './App.css';

/* ── SVG icons (no emojis) ── */
const IconSend = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const IconMic = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="2" width="6" height="12" rx="3"/>
    <path d="M5 10a7 7 0 0 0 14 0M12 19v3M8 22h8"/>
  </svg>
);
const IconChevron = ({ up }) => (
  <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    {up ? <path d="M2 8l4-4 4 4"/> : <path d="M2 4l4 4 4-4"/>}
  </svg>
);
const IconAlert = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);

/* ── Preset queries ── */
const PRESETS = [
  { label: 'Crime distribution', desc: 'Top crime types by FIR count', q: 'What are the top 10 crime types by number of FIRs?' },
  { label: 'District hotspots', desc: 'Areas with highest crime density', q: 'Which 5 districts have the most FIRs?' },
  { label: 'Repeat offenders', desc: 'Habitual criminals by case count', q: 'Show the top 5 repeat offenders by number of cases' },
  { label: 'Annual trend', desc: 'FIR volume year-over-year', q: 'Show FIR trend by year' },
  { label: 'IPC vs BNS split', desc: 'Legal code transition after Jul 2024', q: 'How many FIRs are registered under IPC vs BNS?' },
  { label: 'Bail status', desc: 'Custody and bail breakdown', q: 'What is the bail status breakdown for arrested accused?' },
];

/* ── Evidence Panel ── */
function EvidencePanel({ sql, columns, rows, rowCount }) {
  return (
    <div className="evidence-panel">
      {sql && (
        <div className="evidence-block">
          <div className="evidence-block-head">Query executed</div>
          <div className="evidence-block-body">
            <div className="sql-code">{sql}</div>
          </div>
        </div>
      )}
      {rows?.length > 0 && (
        <div className="evidence-block">
          <div className="evidence-block-head">Source records</div>
          <div className="evidence-block-body">
            <div className="row-count">{rowCount} total — showing {Math.min(rows.length, 10)}</div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>{columns.map(c => <th key={c}>{c}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.slice(0, 10).map((r, i) => (
                    <tr key={i}>{columns.map(c => <td key={c} title={String(r[c] ?? '')}>{String(r[c] ?? '')}</td>)}</tr>
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

/* ── Answer row ── */
function AnswerRow({ msg }) {
  const [open, setOpen] = useState(false);
  const hasEvidence = msg.sql || msg.rows?.length > 0;

  return (
    <div className="row row-answer">
      <div className="row-inner">
        <div className="answer-header">
          <span className="answer-label">Sahayak</span>
        </div>
        {msg.isError
          ? <div className="answer-error"><IconAlert /> {msg.answer}</div>
          : <div className="answer-text"
              dangerouslySetInnerHTML={{ __html:
                msg.answer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
              }}
            />
        }
        {hasEvidence && !msg.isError && (
          <button className="evidence-toggle" onClick={() => setOpen(v => !v)}>
            <IconChevron up={open} />
            {open ? 'Hide evidence trail' : `Evidence trail${msg.rowCount ? ` — ${msg.rowCount} records` : ''}`}
          </button>
        )}
        {open && <EvidencePanel sql={msg.sql} columns={msg.columns} rows={msg.rows} rowCount={msg.rowCount} />}
      </div>
    </div>
  );
}

/* ── App ── */
export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState('EN');
  const bottomRef = useRef();
  const inputRef = useRef();
  const feedRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const submit = useCallback(async (question) => {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setMessages(m => [...m, { role: 'query', text: q }]);
    setInput('');
    setLoading(true);
    try {
      const data = await sendMessage(q, sessionId);
      setSessionId(data.session_id);
      setMessages(m => [...m, {
        role: 'answer',
        answer: data.error ? `Unable to answer: ${data.error}` : data.answer,
        sql: data.sql,
        columns: data.columns ?? [],
        rows: data.rows ?? [],
        rowCount: data.row_count,
        isError: !!data.error,
      }]);
    } catch {
      setMessages(m => [...m, {
        role: 'answer',
        answer: 'Network error — make sure the backend is running on port 8000.',
        isError: true,
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [input, loading, sessionId]);

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  const placeholder = lang === 'EN'
    ? 'Enter a query about crime records, suspects, trends…'
    : 'ಅಪರಾಧ ದಾಖಲೆಗಳ ಬಗ್ಗೆ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ…';

  return (
    <div className="app">

      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-kn">ಸಹಾಯಕ</span>
          <span className="brand-en">Sahayak</span>
        </div>
        <div className="topbar-sep" />
        <span className="topbar-title">Crime Intelligence Platform</span>
        <div className="topbar-status">
          <span className="status-dot" />
          Online
        </div>
        <div className="topbar-right">
          <button className={`lang-pill${lang === 'EN' ? ' active' : ''}`} onClick={() => setLang('EN')}>EN</button>
          <button className={`lang-pill${lang === 'KN' ? ' active' : ''}`} onClick={() => setLang('KN')}>ಕನ್ನಡ</button>
        </div>
      </header>

      {/* Feed */}
      <div className="main">
        <div className="feed" ref={feedRef}>

          {/* Empty state */}
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-eyebrow">Karnataka State Police · SCRB</div>
              <h1 className="empty-title">
                {lang === 'EN' ? 'Query crime intelligence' : 'ಅಪರಾಧ ಮಾಹಿತಿ ಪ್ರಶ್ನಿಸಿ'}
              </h1>
              <p className="empty-sub">
                {lang === 'EN'
                  ? 'Ask questions about FIRs, accused, locations, and patterns. Every answer is grounded in real records with a full evidence trail.'
                  : 'ಎಫ್‌ಐಆರ್‌ಗಳು, ಆರೋಪಿಗಳು, ಸ್ಥಳಗಳು ಮತ್ತು ಮಾದರಿಗಳ ಬಗ್ಗೆ ಕೇಳಿ.'
                }
              </p>
              <div className="queries-label">Common queries</div>
              <div className="queries-grid">
                {PRESETS.map(p => (
                  <button key={p.q} className="query-card" onClick={() => submit(p.q)}>
                    <div className="query-card-label">{p.label}</div>
                    <div className="query-card-desc">{p.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message rows */}
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
              <AnswerRow key={i} msg={m} />
            )
          )}

          {/* Thinking */}
          {loading && (
            <div className="thinking-row">
              <div className="thinking-inner">
                <div className="thinking-dots"><span/><span/><span/></div>
                <span className="thinking-label">Querying database…</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="input-area">
        <div className="input-inner">
          <div className="input-row">
            <div className="input-wrap">
              <textarea
                ref={inputRef}
                className="input-field"
                rows={1}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder={placeholder}
                disabled={loading}
              />
              <button className="voice-btn-inner" title="Voice input">
                <IconMic />
              </button>
            </div>
            <button className="send-btn" onClick={() => submit()} disabled={loading || !input.trim()}>
              <IconSend />
              Send
            </button>
          </div>
          <div className="input-meta">
            <span><kbd>Enter</kbd> to send</span>
            <span><kbd>Shift+Enter</kbd> for new line</span>
          </div>
        </div>
      </div>

    </div>
  );
}
