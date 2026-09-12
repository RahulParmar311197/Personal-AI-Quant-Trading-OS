export default function HomePage() {
  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">PERSONAL AI QUANT TRADING OS</p>
          <h1>Research-first trading workspace</h1>
          <p className="subtitle">
            Market analysis, strategies, backtesting, AI/ML, risk and execution will be added
            behind explicit system boundaries.
          </p>
        </div>
        <span className="status">LIVE TRADING DISABLED</span>
      </header>

      <section className="grid" aria-label="System modules">
        {[
          ["Market Data", "Canonical data and validation layer"],
          ["Analysis", "Technical, price action, SMC and ICT"],
          ["Research", "Strategies, backtests and robustness"],
          ["Decision", "Ensemble scoring with bounded outputs"],
          ["Risk", "Independent permission and exposure controls"],
          ["Execution", "Paper-first broker and order lifecycle"],
        ].map(([title, description]) => (
          <article className="card" key={title}>
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
