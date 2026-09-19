import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const EXAMPLES = [
  'Show total spending by fiscal year',
  'Which agencies have the highest total obligations?',
  'What percentage is concentrated among the top ten recipients?',
];

const POWER_BI_REPORT_URL = 'https://app.powerbi.com/groups/me/reports/7171e917-4de9-4ce7-ac9e-34918540cf3a/7d10024e7d68ae80975d?experience=power-bi';

const POWER_BI_VISUALS = [
  {
    number: '01',
    title: 'Total Federal Obligations',
    view: 'KPI card',
    type: 'kpi',
    image: '/01-total-obligations.png',
    description: 'The headline KPI summarizes the total federal obligations represented in the report: 104.65bn.',
    insight: 'Answers: How much federal money is represented in the dataset?',
  },
  {
    number: '02',
    title: 'Top 10 Concentration',
    view: 'KPI card',
    type: 'concentration',
    image: '/02-top10-concentration.png',
    description: 'This KPI shows the share of all federal obligations held by the ten largest recipients: 24.14%.',
    insight: 'Answers: How concentrated is federal spending among the largest recipients?',
  },
  {
    number: '03',
    title: 'Unique Vendors',
    view: 'KPI card',
    type: 'vendors',
    image: '/03-unique-vendors.png',
    description: 'The vendor count gives the report a scale indicator, showing approximately 35K unique recipients or vendors.',
    insight: 'Answers: How broad is the federal procurement base?',
  },
  {
    number: '04',
    title: 'Top Recipients by Federal Obligations',
    view: 'Ranked table',
    type: 'table',
    image: '/06-top-recipients-table.png',
    description: 'The table ranks the ten largest recipients and exposes both their spending rank and total federal obligations for direct comparison.',
    insight: 'Answers: Which recipients receive the most federal obligations?',
  },
  {
    number: '05',
    title: 'Top Recipients by Federal Obligations',
    view: 'Horizontal bar chart',
    type: 'bars',
    image: '/04-top-recipients-bars.png',
    description: 'The bar chart turns the recipient ranking into a visual comparison, making the gap between the largest vendors immediately visible.',
    insight: 'Answers: How do the top recipients compare in obligation volume?',
  },
  {
    number: '06',
    title: 'Federal Obligations by Fiscal Year',
    view: 'Line chart',
    type: 'trend',
    image: '/05-fiscal-year-trend.png',
    description: 'The fiscal-year line chart shows how total obligations move across time and highlights peaks, declines, and recovery periods.',
    insight: 'Answers: How has federal spending changed by fiscal year?',
  },
  {
    number: '07',
    title: 'Period-over-Period Spending Change',
    view: 'Waterfall chart',
    type: 'columns',
    image: '/07-period-change.png',
    description: 'The waterfall chart separates increases and decreases by fiscal year so the contribution of each period to the overall change is visible.',
    insight: 'Answers: Which periods drove the increase or decrease in spending?',
  },
  {
    number: '08',
    title: 'Federal Obligations by Award Type',
    view: 'Pie chart',
    type: 'mix',
    image: '/08-award-type.png',
    description: 'The pie chart breaks total obligations into award types, showing the relative contribution of contracts, grants, and other award categories.',
    insight: 'Answers: Which award types make up federal obligations?',
  },
];

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

function VisualPreview({ image }) {
  return <img className="visual-canvas visual-image" src={image} alt="" />;
}

function PowerBIView() {
  const [selectedVisual, setSelectedVisual] = useState(null);
  const [visualZoom, setVisualZoom] = useState(1);

  function openVisual(visual) {
    setSelectedVisual(visual);
    setVisualZoom(1);
  }

  function closeVisual() {
    setSelectedVisual(null);
    setVisualZoom(1);
  }

  return (
    <section className="visuals-view">
      <div className="visuals-intro"><div><div className="eyebrow">POWER BI / REPORT PAGE 01</div><h1>US Government Spending<br /><em>&amp; Procurement Analysis.</em></h1></div><p>The actual Power BI page, documented visual by visual. Values shown here match the shared report snapshot dated 9/19/26.</p></div>
      <section className="live-report"><div className="live-report-header"><div><div className="panel-label"><span>CAPTURED</span> POWER BI REPORT</div><h2>US Government Spending &amp; Procurement Analysis</h2></div><a href={POWER_BI_REPORT_URL} target="_blank" rel="noreferrer">OPEN INTERACTIVE REPORT <span aria-hidden="true">↗</span></a></div><img className="report-screenshot" src="/MAIN%20HEADER%20IMAGE.png" alt="US Government Spending and Procurement Analysis Power BI dashboard" /></section>
      <div className="visual-grid">{POWER_BI_VISUALS.map((visual) => <article className="visual-card" key={`${visual.number}-${visual.view}`}><button className="visual-open" type="button" onClick={() => openVisual(visual)} aria-label={`Open ${visual.title} visual larger`}><div className="visual-card-header"><span>{visual.number} / {visual.view}</span><span>POWER BI VISUAL · VIEW LARGER ↗</span></div><VisualPreview image={visual.image} /></button><div className="visual-card-copy"><h2>{visual.title}</h2><p>{visual.description}</p><div className="visual-insight">{visual.insight}</div></div></article>)}</div>
      {selectedVisual && <div className="visual-modal" role="dialog" aria-modal="true" aria-labelledby="visual-modal-title" onClick={closeVisual}><div className="visual-modal-panel" onClick={(event) => event.stopPropagation()}><div className="visual-modal-header"><div><div className="panel-label"><span>{selectedVisual.number}</span> POWER BI VISUAL</div><h2 id="visual-modal-title">{selectedVisual.title}</h2></div><div className="visual-modal-actions"><button type="button" onClick={() => setVisualZoom((zoom) => Math.max(.75, zoom - .25))} aria-label="Zoom out">−</button><span>{Math.round(visualZoom * 100)}%</span><button type="button" onClick={() => setVisualZoom((zoom) => Math.min(3, zoom + .25))} aria-label="Zoom in">+</button><button type="button" onClick={() => setVisualZoom(1)} aria-label="Reset zoom">RESET</button><button className="visual-close" type="button" onClick={closeVisual} aria-label="Close visual">×</button></div></div><div className="visual-modal-image"><img src={selectedVisual.image} alt={selectedVisual.title} style={{ transform: `scale(${visualZoom})` }} /></div><p className="visual-modal-description">{selectedVisual.description}</p></div></div>}
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
        <nav className="tab-nav" aria-label="Workspace views"><button className={activeTab === 'query' ? 'active' : ''} type="button" aria-selected={activeTab === 'query'} onClick={() => setActiveTab('query')}>QUERY DESK</button><button className={activeTab === 'visuals' ? 'active' : ''} type="button" aria-selected={activeTab === 'visuals'} onClick={() => setActiveTab('visuals')}>POWER BI VISUALS <span>08</span></button></nav>
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