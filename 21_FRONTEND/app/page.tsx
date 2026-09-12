import DashboardStatePanel from "./dashboard-state";

const modules = [
  ["Market Data", "Canonical data and validation layer"],
  ["Analysis", "Technical, price action, SMC and ICT"],
  ["Research", "Strategies, backtests and robustness"],
  ["Decision", "Ensemble scoring with bounded outputs"],
  ["Risk", "Independent permission and exposure controls"],
  ["Execution", "Paper-first broker and order lifecycle"],
] as const;

const controls = [
  ["Market data", "Ready"],
  ["Decision engine", "Protected"],
  ["Risk engine", "Independent"],
  ["Live execution", "Disabled"],
] as const;

export default function HomePage() {
  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">PERSONAL AI QUANT TRADING OS</p>
          <h1>Operator dashboard</h1>
          <p className="subtitle">
            Research and execution state in one safety-first workspace. Live trading remains
            explicitly disabled.
          </p>
        </div>
        <span className="status">LIVE TRADING DISABLED</span>
      </header>

      <section className="dashboard-grid" aria-label="Trading system overview">
        <DashboardStatePanel />
        <article className="panel controls-panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">GUARDRAILS</p>
              <h2>Control plane</h2>
            </div>
          </div>
          <ul className="control-list">
            {controls.map(([name, value]) => (
              <li key={name}>
                <span>{name}</span>
                <strong>{value}</strong>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="modules" aria-label="System modules">
        <div className="section-heading">
          <p className="section-label">MODULES</p>
          <h2>Trading stack</h2>
        </div>
        <div className="grid">
          {modules.map(([title, description]) => (
            <article className="card" key={title}>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
