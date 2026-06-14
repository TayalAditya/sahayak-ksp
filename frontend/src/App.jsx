import { useState, useRef, useEffect, useCallback } from 'react';
import { sendMessage } from './api';
import './App.css';

const QUICK_CARDS = [
  { icon: '📊', title: 'Crime distribution', sub: 'Top crime types by FIR count', q: 'What are the top 10 crime types by number of FIRs?' },
  { icon: '📍', title: 'Hotspot districts', sub: 'Which areas have the most crimes', q: 'Which 5 districts have the most FIRs?' },
  { icon: '🔁', title: 'Repeat offenders', sub: 'Habitual criminals by case count', q: 'Show the top 5 repeat offenders by number of cases' },
  { icon: '📅', title: 'Annual trend', sub: 'FIR counts year by year', q: 'Show FIR trend by year' },
  { icon: '⚖️', title: 'IPC vs BNS', sub: 'Legal code split after July 2024', q: 'How many FIRs are under IPC vs BNS sections?' },
  { icon: '🔒', title: 'Bail status', sub: 'Custody & bail breakdown', q: 'What is the bail status breakdown for all arrested accused?' },
];

function EvidencePanel({ sql, columns, rows, rowCount }) {
  return (
    <div className="evidence-panel">
      {sql && (
        <div className="evidence-section">
          <div className="evidence-label">SQL executed</div>
          <div className="sql-block">{sql}</div>
        </div>
      )}
      {rows && rows.length > 0 && (
        <div className="evidence-section">
          <div className="evidence-label">Source records</div>
          <div className="rows-count">{rowCount} total — showing {Math.min(rows.length, 10)}</div>
          <div className="data-table-wrap">
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
      )}
    </div>
  );
}

function AiMessage({ msg }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const hasEvidence = msg.sql || (msg.rows && msg.rows.length > 0);

  return (
    <div className="msg-ai">
      <div className="ai-avatar">S</div>
      <div className="ai-content">
        <div className="ai-answer">
          {msg.error
            ? <span className="ai-error">⚠ {msg.answer}</span>
            : <span dangerouslySetInnerHTML={{ __html: msg.answer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
          }
        </div>
        {hasEvidence && (
          <div className="evidence-bar">
            <button className="evidence-toggle" onClick={() => setShowEvidence(v => !v)}>
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                {showEvidence
                  ? <path d="M2 8l4-4 4 4"/>
                  : <path d="M2 4l4 4 4-4"/>}
              </svg>
              {showEvidence ? 'Hide evidence trail' : `View evidence trail${msg.rowCount ? ` · ${msg.rowCount} records` : ''}`}
            </button>
          </div>
        )}
        {showEvidence && <EvidencePanel sql={msg.sql} columns={msg.columns} rows={msg.rows} rowCount={msg.rowCount} />}
      </div>
    </div>
  );
}

function ThinkingMessage() {
  return (
    <div className="msg-ai">
      <div className="ai-avatar">S</div>
      <div className="ai-content">
        <div className="ai-answer">
          <div className="thinking-dots"><span/><span/><span/></div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState('EN');
  const bottomRef = useRef();
  const inputRef = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const submit = useCallback(async (question) => {
    const q = (question || input).trim();
    if (!q || loading) return;
    setMessages(m => [...m, { role: 'user', text: q }]);
    setInput('');
    setLoading(true);
    try {
      const data = await sendMessage(q, sessionId);
      setSessionId(data.session_id);
      setMessages(m => [...m, {
        role: 'ai',
        answer: data.error ? `Unable to answer: ${data.error}` : data.answer,
        sql: data.sql,
        columns: data.columns || [],
        rows: data.rows || [],
        rowCount: data.row_count,
        error: !!data.error,
      }]);
    } catch {
      setMessages(m => [...m, { role: 'ai', answer: 'Network error — is the backend running on port 8000?', sql: null, error: true }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [input, loading, sessionId]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <span className="logo-kn">ಸಹಾಯಕ</span>
          <span className="logo-en">Sahayak</span>
        </div>
        <div className="header-divider" />
        <div className="header-badge">
          <span className="badge-dot" />
          KSP Crime Intelligence
        </div>
        <div className="header-right">
          <button className={`lang-btn${lang === 'EN' ? ' active' : ''}`} onClick={() => setLang('EN')}>EN</button>
          <button className={`lang-btn${lang === 'KN' ? ' active' : ''}`} onClick={() => setLang('KN')}>ಕನ್ನಡ</button>
        </div>
      </header>

      {/* Chat */}
      <div className="chat-area">
        {messages.length === 0 && (
          <div className="welcome">
            <div className="welcome-header">
              <div className="welcome-icon">🔍</div>
              <h1 className="welcome-title">
                {lang === 'EN' ? 'Query the crime database' : 'ಅಪರಾಧ ಡೇಟಾಬೇಸ್ ಪ್ರಶ್ನಿಸಿ'}
              </h1>
            </div>
            <p className="welcome-sub">
              {lang === 'EN'
                ? <>Ask in natural language. Every answer is grounded in real records with a <span>transparent evidence trail.</span></>
                : <>ಸಹಜ ಭಾಷೆಯಲ್ಲಿ ಕೇಳಿ. ಪ್ರತಿ ಉತ್ತರವು ನೈಜ ದಾಖಲೆಗಳಿಂದ ಪ್ರಮಾಣಿಕರಿಸಲ್ಪಟ್ಟಿದೆ.</>
              }
            </p>
            <div className="quick-label">Quick queries</div>
            <div className="quick-grid">
              {QUICK_CARDS.map(card => (
                <button key={card.q} className="quick-card" onClick={() => submit(card.q)}>
                  <span className="quick-card-icon">{card.icon}</span>
                  <div className="quick-card-text">
                    <div className="quick-card-title">{card.title}</div>
                    <div className="quick-card-sub">{card.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === 'user'
            ? <div key={i} className="msg-user"><div className="msg-user-bubble">{m.text}</div></div>
            : <AiMessage key={i} msg={m} />
        )}
        {loading && <ThinkingMessage />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <div className="input-row">
          <div className="input-wrap">
            <textarea
              ref={inputRef}
              className="input-field"
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={lang === 'EN' ? 'Ask about crime data, patterns, suspects…' : 'ಅಪರಾಧ ಮಾಹಿತಿಯ ಬಗ್ಗೆ ಕೇಳಿ…'}
              disabled={loading}
            />
            <button className="voice-btn" title="Voice input (Zia NLP — Phase 6)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="2" width="6" height="12" rx="3"/>
                <path d="M5 10a7 7 0 0 0 14 0M12 19v3M8 22h8"/>
              </svg>
            </button>
          </div>
          <button className="send-btn" onClick={() => submit()} disabled={loading || !input.trim()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            Send
          </button>
        </div>
        <div className="input-hint">Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line</div>
      </div>
    </div>
  );
}
