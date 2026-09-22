import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const EXAMPLES = [
  'Show total spending by fiscal year',
  'Which agencies have the highest total obligations?',
  'What percentage is concentrated among the top ten recipients?',
];

const POWER_BI_EMBED_URL = 'https://app.powerbi.com/reportEmbed?reportId=7171e917-4de9-4ce7-ac9e-34918540cf3a&autoAuth=true&ctid=76bed47f-8633-49b2-8de1-35950dd0251c&actionBarEnabled=true';

function formatValue(value) {
  if (typeof value === 'number') {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
  }
  return value ?? '—';
}

function ResultsTable({ columns, rows }) {
  if (!rows.length) return <div className="empty-state">No rows returned for this question.</div>;
  const visibleColumns = columns.length ? columns : Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{visibleColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => (
          <tr key={index}>{visibleColumns.map((column) => <td key={column}>{formatValue(row[column])}</td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function PowerBIView() {
  return (
    <section className="visuals-view">
      <div className="visuals-intro"><div><div className="eyebrow">POWER BI / LIVE REPORT</div><h1>US Government Spending<br /><em>&amp; Procurement Analysis.</em></h1></div><p>Use the report controls to filter the same procurement story across every chart, rather than relying on a static snapshot.</p></div>
      <section className="live-report"><div className="live-report-header"><div><div className="panel-label"><span>LIVE</span> POWER BI REPORT</div><h2>US Government Spending &amp; Procurement Analysis</h2></div></div><iframe className="powerbi-embed" title="US Government Spending and Procurement Analysis Power BI report" src={POWER_BI_EMBED_URL} allowFullScreen /></section>
      <section className="visual-guide" aria-label="How to read the Power BI report"><article><span>01</span><h2>Establish the scale</h2><p>Start with the obligation, concentration, and vendor KPI cards. Together they show total activity, how much is held by the largest recipients, and the breadth of the supplier base.</p></article><article><span>02</span><h2>Explain movement</h2><p>Use the fiscal-year trend and period-over-period change visuals to distinguish sustained movement from a one-year increase or decrease.</p></article><article><span>03</span><h2>Find the drivers</h2><p>Cross-filter recipient and award-type charts to identify who receives the funding and which procurement mechanisms explain the total.</p></article></section>
    </section>
  );
}

function App() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [answer, setAnswer] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('query');

  async function askQuestion(event) {
    event.preventDefault();
    if (!question.trim() || isLoading) return;
    setIsLoading(true);
    setAnswer(null);
    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      });
      const data = await response.json();
      setAnswer({ ...data, requestFailed: !response.ok });
    } catch {
      setAnswer({ error: 'Could not reach the API. Start FastAPI on port 8000.', requestFailed: true });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="rail"><div className="mark" aria-label="Ledger home">L<span>/</span></div><div className="rail-rule" /><div className="rail-caption">US<br />GOV</div><div className="rail-bottom">READ<br />ONLY</div></aside>
      <main className="workspace">
        <header className="topbar"><div className="breadcrumb"><span className="signal" /> LIVE ANALYTICS <span>/</span> USAspending</div><div className="topbar-meta">SQL SERVER <strong>·</strong> READ ONLY</div></header>
        <nav className="tab-nav" aria-label="Workspace views"><button className={activeTab === 'query' ? 'active' : ''} type="button" aria-selected={activeTab === 'query'} onClick={() => setActiveTab('query')}>QUERY DESK</button><button className={activeTab === 'visuals' ? 'active' : ''} type="button" aria-selected={activeTab === 'visuals'} onClick={() => setActiveTab('visuals')}>POWER BI REPORT <span>LIVE</span></button></nav>
        {activeTab === 'query' ? <><section className="intro"><div className="eyebrow">PUBLIC PROCUREMENT / QUERY DESK</div><h1>Ask the ledger<br /><em>what changed.</em></h1><p className="intro-copy">Translate a plain-language question into a validated, read-only query across the federal spending views.</p></section>
        <section className="query-panel"><div className="panel-label"><span>01</span> NATURAL-LANGUAGE QUERY</div><form onSubmit={askQuestion}><textarea aria-label="Ask about federal spending" maxLength="1000" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about federal spending..." /><div className="query-footer"><div className="examples"><span>TRY</span>{EXAMPLES.map((example) => <button type="button" key={example} onClick={() => setQuestion(example)}>{example}</button>)}</div><button className="ask-button" type="submit" disabled={isLoading || !question.trim()}>{isLoading ? 'RUNNING' : 'ASK LEDGER'} <span aria-hidden="true">↗</span></button></div></form></section>
        {answer && <section className={`answer-section ${answer.error ? 'has-error' : ''}`}><div className="answer-heading"><div><div className="panel-label"><span>02</span> ANSWER</div><h2>{answer.error ? 'Query interrupted' : 'Query returned'}</h2></div><div className="result-status"><span className="status-dot" /> {answer.error ? 'REVIEW REQUIRED' : 'VALIDATED RESULT'}</div></div>{answer.error ? <div className="error-box">{answer.error}</div> : <><div className="stats-row"><div><span>ROWS RETURNED</span><strong>{answer.row_count}</strong></div><div><span>COLUMNS</span><strong>{answer.columns?.length || 0}</strong></div><div><span>ACCESS</span><strong>READ ONLY</strong></div></div><ResultsTable columns={answer.columns || []} rows={answer.rows || []} /></>}</section>}
        {answer?.sql && <section className="sql-section"><div className="panel-label"><span>03</span> GENERATED T-SQL</div><pre><code>{answer.sql}</code></pre><div className="sql-note"><span>✓</span> Parsed and constrained to approved analytical views · maximum 500 rows</div></section>}</> : <PowerBIView />}
        <footer><span>LEDGER / FEDERAL SPENDING INTELLIGENCE</span><span>DATA SOURCE: USASPENDING.GOV</span></footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>);
