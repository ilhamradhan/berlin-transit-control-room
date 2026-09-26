const money = (value) => value == null ? "—" : `${(value / 60).toFixed(1)} min`;
const percent = (value) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;
const escapeHtml = (value) => String(value ?? "—").replace(/[&<>\"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
}[character]));

async function loadArtifact() {
  const root = document.querySelector("#app");
  try {
    const response = await fetch("data/public_metrics.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Public artifact unavailable");
    const artifact = await response.json();
    const summary = artifact.summary;
    const generated = Date.parse(artifact.generated_at);
    const stale = !Number.isFinite(generated) || Date.now() - generated > 24 * 60 * 60 * 1000;
    const warnings = [];
    if (artifact.provenance.coverage_status === "low") warnings.push(`Low coverage: ${percent(summary.realtime_coverage_rate)} of expected slots.`);
    if (stale) warnings.push("This artifact is older than 24 hours and may be stale.");
    const warning = warnings.map(message => `<p class="warning">${escapeHtml(message)}</p>`).join("");
    root.innerHTML = `${warning}
      <section class="meta"><span>Release ${escapeHtml(artifact.release_id)}</span><span>Generated ${escapeHtml(artifact.generated_at)}</span><span>Campaign ${escapeHtml(artifact.provenance.campaign_days)} days</span></section>
      <section class="metric-group" aria-labelledby="delay-heading"><h2 id="delay-heading">Delay</h2><div class="cards">
        <article><strong>${money(summary.median_delay_seconds)}</strong><span>Median predicted delay</span></article>
        <article><strong>${money(summary.p90_delay_seconds)}</strong><span>P90 predicted delay</span></article>
      </div></section>
      <section class="metric-group" aria-labelledby="reliability-heading"><h2 id="reliability-heading">Reliability</h2><div class="cards">
        <article><strong>${percent(summary.on_time_rate)}</strong><span>On-time observations</span></article>
        <article><strong>${percent(summary.severe_delay_rate)}</strong><span>Severe-delay observations</span></article>
      </div></section>
      <section class="metric-group" aria-labelledby="evidence-heading"><h2 id="evidence-heading">Evidence quality</h2><div class="cards">
        <article><strong>${summary.cancellation_rate == null ? "Not reported in this release." : percent(summary.cancellation_rate)}</strong><span>Source cancellation rate</span><small>${summary.cancellation_rate == null ? "No cancellation field in this release." : "Reported by the source."}</small></article>
        <article><strong>${percent(summary.schedule_match_rate)}</strong><span>Schedule match</span></article>
        <article><strong>${percent(summary.realtime_coverage_rate)}</strong><span>Realtime coverage</span></article>
      </div></section>
      <section>
        <h2>Mode / route / day</h2><p class="table-note">Swipe horizontally on narrow screens to see all columns.</p><div class="table-wrap"><table><caption class="visually-hidden">Verified mode, route, and service-day aggregates</caption><thead><tr><th scope="col">Date</th><th scope="col">Mode</th><th scope="col">Route</th><th scope="col">Median</th><th scope="col">P90</th><th scope="col">On time</th></tr></thead><tbody>
        ${artifact.aggregates.map(row => `<tr><td>${escapeHtml(row.service_date)}</td><td>${escapeHtml(row.mode)}</td><td>${escapeHtml(row.route_id)}</td><td>${money(row.median_delay_seconds)}</td><td>${money(row.p90_delay_seconds)}</td><td>${percent(row.on_time_rate)}</td></tr>`).join("")}
      </tbody></table></div></section>
      <p class="note">Predictions are not actual arrivals. See <a href="docs.html">documentation</a> for definitions and limitations.</p>`;
  } catch (error) {
    root.innerHTML = `<p class="warning">Public data is unavailable. Try again later.</p>`;
  }
}

if (document.querySelector("#app")) loadArtifact();
