import { useState, useRef, useEffect } from 'react';
import { sendMessage } from './api';
import './App.css';

const SUGGESTED = [
  'How many theft cases are there?',
  'Which district has the most FIRs?',
  'Show the top 5 repeat offenders',
  'What is the FIR trend by year?',
  'Bail status breakdown of arrested accused',
  'Which gangs are linked to the most cases?',
];

function EvidencePanel({ sql, columns, rows, rowCount }) {
  if (!sql) return null;
  return (
    <div className="evidence-panel">
      <div className="evidence-title">Evidence Trail</div>
      <div className="evidence-sql">
        <span className="label">SQL executed:</span>
        <pre>{sql}</pre>
      </div>
      {rows && rows.length > 0 && (
        <div className="evidence-table-wrap">
          <div className="label">Source records ({rowCount} total, showing {Math.min(rows.length, 10)}):</div>
          <div className="table-scroll">
            <table className="evidence-table">
              <thead>
                <tr>{columns.map(c => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {rows.slice(0, 10).map((r, i) => (
                  <tr key={i}>
                    {columns.map(c => <td key={c}>{String(r[c] ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Message({ msg }) {
  const [showEvidence, setShowEvidence] = useState(false);
  if (msg.role === 'user') {
    return <div className="msg user"><span>{msg.text}</span></div>;
  }
  return (
    <div className="msg assistant">
      <div className="avatar">S</div>
      <div className="bubble">
        <div className="answer-text">{msg.answer}</div>
        {msg.sql && (
          <button className="evidence-toggle" onClick={() => setShowEvidence(v => !v)}>
            {showEvidence ? '▲ Hide evidence' : '▼ Show evidence & SQL'}
          </button>
        )}
        {showEvidence && (
          <EvidencePanel sql={msg.sql} columns={msg.columns} rows={msg.rows} rowCount={msg.rowCount} />
        )}
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

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function submit(question) {
    const q = question.trim();
    if (!q || loading) return;
    setMessages(m => [...m, { role: 'user', text: q }]);
    setInput('');
    setLoading(true);
    try {
      const data = await sendMessage(q, sessionId);
      setSessionId(data.session_id);
      setMessages(m => [...m, {
        role: 'assistant',
        answer: data.error ? `Unable to answer: ${data.error}` : data.answer,
        sql: data.sql,
        columns: data.columns || [],
        rows: data.rows || [],
        rowCount: data.row_count,
      }]);
    } catch {
      setMessages(m => [...m, { role: 'assistant', answer: 'Network error — is the backend running on port 8000?', sql: null }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <span className="logo">ಸಹಾಯಕ</span>
          <span className="logo-en">Sahayak</span>
          <span className="badge">KSP Crime Intelligence</span>
        </div>
        <div className="header-right">
          <button className={`lang-btn${lang === 'EN' ? ' active' : ''}`} onClick={() => setLang('EN')}>EN</button>
          <button className={`lang-btn${lang === 'KN' ? ' active' : ''}`} onClick={() => setLang('KN')}>ಕನ್ನಡ</button>
        </div>
      </header>

      <div className="chat-area">
        {messages.length === 0 && (
          <div className="welcome">
            <div className="welcome-icon">🔍</div>
            <div className="welcome-title">
              {lang === 'EN' ? 'Ask anything about the crime database' : 'ಅಪರಾಧ ಡೇಟಾದ ಬಗ್ಗೆ ಏನಾದರೂ ಕೇಳಿ'}
            </div>
            <div className="welcome-sub">Every answer is grounded in real records with a transparent evidence trail.</div>
            <div className="suggestions">
              {SUGGESTED.map(s => (
                <button key={s} className="suggestion" onClick={() => submit(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} msg={m} />)}
        {loading && (
          <div className="msg assistant">
            <div className="avatar">S</div>
            <div className="bubble thinking">Querying crime database…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <button className="voice-btn" title="Voice input (coming soon)">🎤</button>
        <input
          className="input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit(input)}
          placeholder={lang === 'EN' ? 'Ask a question about crime data…' : 'ಅಪರಾಧ ಡೇಟಾದ ಬಗ್ಗೆ ಪ್ರಶ್ನಿಸಿ…'}
          disabled={loading}
        />
        <button className="send-btn" onClick={() => submit(input)} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
