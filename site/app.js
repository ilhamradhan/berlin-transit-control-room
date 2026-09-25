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
      <section class="meta"><span>Release ${escapeHtml(artifact.release_id)}</span><span>Generated ${escapeHtml(artifact.generated_at)}</span></section>
      <section class="cards" aria-label="Summary metrics">
        <article><strong>${money(summary.median_delay_seconds)}</strong><span>Median predicted delay</span></article>
        <article><strong>${money(summary.p90_delay_seconds)}</strong><span>P90 predicted delay</span></article>
        <article><strong>${percent(summary.on_time_rate)}</strong><span>On-time observations</span></article>
        <article><strong>${percent(summary.severe_delay_rate)}</strong><span>Severe-delay observations</span></article>
        <article><strong>${percent(summary.cancellation_rate)}</strong><span>Source cancellations</span></article>
        <article><strong>${percent(summary.schedule_match_rate)}</strong><span>Schedule match</span></article>
        <article><strong>${percent(summary.realtime_coverage_rate)}</strong><span>Realtime coverage</span></article>
      </section>
      <section><h2>Mode / route / day</h2><div class="table-wrap"><table><thead><tr><th>Date</th><th>Mode</th><th>Route</th><th>Median</th><th>P90</th><th>On time</th></tr></thead><tbody>
        ${artifact.aggregates.map(row => `<tr><td>${escapeHtml(row.service_date)}</td><td>${escapeHtml(row.mode)}</td><td>${escapeHtml(row.route_id)}</td><td>${money(row.median_delay_seconds)}</td><td>${money(row.p90_delay_seconds)}</td><td>${percent(row.on_time_rate)}</td></tr>`).join("")}
      </tbody></table></div></section>
      <p class="note">Predictions are not actual arrivals. See <a href="docs.html">documentation</a> for definitions and limitations.</p>`;
  } catch (error) {
    root.innerHTML = `<p class="warning">Public data is unavailable. Try again later.</p>`;
  }
}

if (document.querySelector("#app")) loadArtifact();
