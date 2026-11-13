/**
 * Skeleton della Home: riproduce la struttura e la forma delle card reali
 * (hero, grafici, elenchi Conti/Salvadanai, ultimi movimenti), così il primo
 * caricamento non cambia il layout quando arrivano i dati.
 */
export function DashboardContentSkeleton() {
  return (
    <>
      <span className="visually-hidden" role="status">
        Caricamento della Home…
      </span>

      <section className="dash-summary">
        <div className="card dash-hero">
          <div className="dash-hero-head">
            <span className="skeleton dash-skeleton-label" aria-hidden="true" />
            <span
              className="skeleton dash-skeleton-wallet"
              aria-hidden="true"
            />
          </div>
          <span className="skeleton dash-skeleton-amount" aria-hidden="true" />
          <span className="skeleton dash-skeleton-subtitle" aria-hidden="true" />
          <span
            className="skeleton dash-skeleton-subtitle-2"
            aria-hidden="true"
          />
          <div className="dash-breakdown">
            {[0, 1, 2, 3].map((index) => (
              <div key={index}>
                <span
                  className="skeleton dash-skeleton-metric-label"
                  aria-hidden="true"
                />
                <span
                  className="skeleton dash-skeleton-metric-value"
                  aria-hidden="true"
                />
                {index === 2 && (
                  <span
                    className="skeleton dash-skeleton-metric-note"
                    aria-hidden="true"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card dash-charts">
        <div className="card-heading">
          <span className="skeleton dash-skeleton-heading" aria-hidden="true" />
        </div>
        <div className="stack">
          <div>
            <span className="skeleton dash-skeleton-label" aria-hidden="true" />
            <span className="skeleton dash-skeleton-chart" aria-hidden="true" />
            <span
              className="skeleton dash-skeleton-legend"
              aria-hidden="true"
            />
          </div>
          <div className="dash-charts-row">
            <div>
              <span
                className="skeleton dash-skeleton-label"
                aria-hidden="true"
              />
              <div className="dash-skeleton-inout">
                <span
                  className="skeleton dash-skeleton-inout-card"
                  aria-hidden="true"
                />
                <span
                  className="skeleton dash-skeleton-inout-card"
                  aria-hidden="true"
                />
                <span
                  className="skeleton dash-skeleton-track"
                  aria-hidden="true"
                />
              </div>
            </div>
            <div>
              <span
                className="skeleton dash-skeleton-label"
                aria-hidden="true"
              />
              <div className="dash-skeleton-bars">
                {[0, 1, 2, 3, 4, 5, 6].map((index) => (
                  <div key={index} className="dash-skeleton-bar">
                    <span
                      className="skeleton dash-skeleton-bar-label"
                      aria-hidden="true"
                    />
                    <span
                      className="skeleton dash-skeleton-bar-track"
                      aria-hidden="true"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="two-columns equal">
        <div className="card">
          <div className="card-heading">
            <span
              className="skeleton dash-skeleton-heading"
              aria-hidden="true"
            />
          </div>
          <div className="dash-skeleton-rows">
            {[0, 1, 2].map((index) => (
              <div key={index} className="dash-skeleton-row">
                <span
                  className="skeleton dash-skeleton-row-line"
                  aria-hidden="true"
                />
                <span
                  className="skeleton dash-skeleton-row-line-short"
                  aria-hidden="true"
                />
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="card-heading">
            <span
              className="skeleton dash-skeleton-heading"
              aria-hidden="true"
            />
          </div>
          <div className="dash-skeleton-rows">
            {[0, 1].map((index) => (
              <div key={index} className="dash-skeleton-row">
                <span
                  className="skeleton dash-skeleton-row-line"
                  aria-hidden="true"
                />
                <span
                  className="skeleton dash-skeleton-row-line-short"
                  aria-hidden="true"
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-heading">
          <span className="skeleton dash-skeleton-heading" aria-hidden="true" />
        </div>
        <div className="dash-skeleton-movements">
          {[0, 1, 2, 3].map((index) => (
            <div key={index} className="dash-skeleton-movement">
              <span
                className="skeleton dash-skeleton-avatar"
                aria-hidden="true"
              />
              <div className="dash-skeleton-movement-lines">
                <span
                  className="skeleton dash-skeleton-line-lg"
                  aria-hidden="true"
                />
                <span
                  className="skeleton dash-skeleton-line-sm"
                  aria-hidden="true"
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

/** Skeleton a forma di pagina per la Home, usato come fallback di route (setup/auth). */
export function HomeSkeleton() {
  return (
    <div className="stack-page dashboard-page" aria-busy="true">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Home</p>
          <h1>Le tue finanze</h1>
        </div>
      </section>

      <section className="dash-toolbar" aria-hidden="true">
        <div className="period-segmented">
          <span className="skeleton dash-skeleton-pill" />
          <span className="skeleton dash-skeleton-pill" />
          <span className="skeleton dash-skeleton-pill" />
          <span className="skeleton dash-skeleton-pill" />
        </div>
        <div className="dash-range">
          <span className="skeleton dash-skeleton-date" />
          <span className="dash-range-sep" aria-hidden="true">
            →
          </span>
          <span className="skeleton dash-skeleton-date" />
          <span className="skeleton dash-skeleton-apply" />
        </div>
      </section>

      <div className="dash-content">
        <DashboardContentSkeleton />
      </div>
    </div>
  );
}
