(function () {
  const data = window.DASHBOARD_DATA.batter_diagnostics;
  const PHASE_ORDER = ["powerplay", "middle", "death"];

  const els = {
    horizon: document.getElementById("batter-horizon"),
    search: document.getElementById("batter-search"),
    options: document.getElementById("batter-options"),
    headline: document.getElementById("batter-headline"),
    scoutingCall: document.getElementById("batter-scouting-call"),
    styleContext: document.getElementById("batter-style-context"),
    phaseCards: document.getElementById("batter-phase-cards"),
    pressureCards: document.getElementById("batter-pressure-cards"),
    venueTable: document.getElementById("batter-venue-table"),
    venuePressureTable: document.getElementById("batter-venue-pressure-table"),
    familyCards: document.getElementById("batter-family-cards"),
    dismissalTable: document.getElementById("batter-dismissal-table"),
    targetTable: document.getElementById("batter-target-table"),
    troubleTable: document.getElementById("batter-trouble-table"),
    methodology: document.getElementById("batter-methodology"),
  };

  function formatDecimal(value, digits = 2) {
    return Number(value || 0).toFixed(digits);
  }

  function titleCase(value) {
    return String(value || "")
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function renderTable(table, columns, rows) {
    const head = columns.map((column) => `<th>${column.label}</th>`).join("");
    const body = rows.length
      ? rows
          .map(
            (row) =>
              `<tr>${columns
                .map((column) => `<td>${column.render ? column.render(row[column.key], row) : row[column.key] ?? ""}</td>`)
                .join("")}</tr>`
          )
          .join("")
      : `<tr><td colspan="${columns.length}" class="replay-empty">No usable sample yet.</td></tr>`;
    table.innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
  }

  function setOptions(values, preferred) {
    els.options.innerHTML = values.map((name) => `<option value="${name}"></option>`).join("");
    if (!values.includes(els.search.value)) {
      els.search.value = values.includes(preferred) ? preferred : values[0] || "";
    }
  }

  function currentOptions() {
    return els.horizon.value === "Active" ? data.active_batter_options : data.batter_options;
  }

  function currentPlayer() {
    return els.search.value;
  }

  function phaseRows(player) {
    return data.phase_splits
      .filter((row) => row.batter_name === player)
      .sort((a, b) => PHASE_ORDER.indexOf(a.phase) - PHASE_ORDER.indexOf(b.phase));
  }

  function pressureRows(player) {
    return data.pressure_splits.filter((row) => row.batter_name === player);
  }

  function venueRows(player) {
    return data.venue_splits
      .filter((row) => row.batter_name === player)
      .sort((a, b) => b.runs - a.runs)
      .slice(0, 8);
  }

  function venuePressureRows(player) {
    return data.venue_pressure_splits
      .filter((row) => row.batter_name === player)
      .sort((a, b) => b.runs - a.runs)
      .slice(0, 8);
  }

  function familyRows(player) {
    return data.family_splits.filter((row) => row.batter_name === player);
  }

  function matchupRows(player) {
    const rows = data.bowler_matchups.filter((row) => row.batter_name === player);
    if (els.horizon.value !== "Active") {
      return rows;
    }
    const activeBowlerSet = new Set(data.active_bowler_options || []);
    return rows.filter((row) => activeBowlerSet.has(row.bowler_name));
  }

  function dismissalRows(player) {
    return data.dismissal_modes.filter((row) => row.batter_name === player).slice(0, 8);
  }

  function strongestPhase(rows) {
    return rows.slice().sort((a, b) => b.impact_score - a.impact_score || b.strike_rate - a.strike_rate)[0];
  }

  function weakestPhase(rows) {
    return rows.slice().sort((a, b) => a.impact_score - b.impact_score || a.strike_rate - b.strike_rate)[0];
  }

  function pressureEdge(rows) {
    const high = rows.find((row) => row.pressure_state === "High Pressure");
    const standard = rows.find((row) => row.pressure_state === "Standard");
    return {
      high,
      standard,
      delta: Number(((high?.strike_rate || 0) - (standard?.strike_rate || 0)).toFixed(2)),
    };
  }

  function bestFamily(rows) {
    return rows.slice().sort((a, b) => b.strike_rate - a.strike_rate)[0];
  }

  function worstFamily(rows) {
    return rows.slice().sort((a, b) => b.dismissal_rate - a.dismissal_rate || a.strike_rate - b.strike_rate)[0];
  }

  function bestMatchups(rows) {
    return rows
      .filter((row) => row.balls >= 10)
      .sort((a, b) => b.attack_score - a.attack_score)
      .slice(0, 6);
  }

  function troubleMatchups(rows) {
    return rows
      .filter((row) => row.balls >= 10)
      .sort((a, b) => b.risk_score - a.risk_score)
      .slice(0, 6);
  }

  function renderHeadline(summary) {
    els.headline.innerHTML = `
      <div class="replay-card">
        <h4>Career Runs</h4>
        <strong>${summary.runs}</strong>
        <p>${summary.matches} matches in the IPL sample.</p>
      </div>
      <div class="replay-card">
        <h4>Strike Rate</h4>
        <strong>${formatDecimal(summary.strike_rate, 1)}</strong>
        <p>${summary.balls} balls faced.</p>
      </div>
      <div class="replay-card">
        <h4>Impact Score</h4>
        <strong>${formatDecimal(summary.impact_score, 1)}</strong>
        <p>Phase-adjusted batting impact total.</p>
      </div>
      <div class="replay-card">
        <h4>Wins Added</h4>
        <strong>${formatDecimal(summary.wins_added, 2)}</strong>
        <p>${summary.active ? "Active player pool" : "All-time player pool"}.</p>
      </div>
    `;
  }

  function renderScoutingCall(player, summary, phase, pressure, family, venues, dismissals) {
    const bestPhase = strongestPhase(phase);
    const weakPhase = weakestPhase(phase);
    const bestType = bestFamily(family);
    const hardType = worstFamily(family);
    const topVenue = venues[0];
    const topDismissal = dismissals[0];
    const pressureLine =
      pressure.delta >= 8
        ? "His strike rate actually climbs in pressure phases, so he looks comfortable when the innings tightens."
        : pressure.delta <= -8
          ? "Pressure overs visibly drag his scoring rate down, so that is the first stress point opponents should chase."
          : "Pressure doesn’t materially distort his output, which suggests a fairly stable scoring base.";

    els.scoutingCall.innerHTML = `
      <div class="insight-card">
        <h5>${player} Scouting Read</h5>
        <p>
          ${player} profiles best in ${titleCase(bestPhase?.phase || "middle")}, where his phase impact and strike-rate shape are strongest.
          The softer zone comes in ${titleCase(weakPhase?.phase || "middle")}, which is where opponents are most likely to slow him down.
          ${bestType ? `${titleCase(bestType.bowl_family)} has been the friendlier bowling family for him, while ${titleCase(hardType?.bowl_family || "spin")} has created the more awkward trade-off between scoring and dismissal risk.` : ""}
          ${topVenue ? `${topVenue.venue} has been one of his better scoring venues in the archive.` : ""}
          ${pressureLine}
          ${topDismissal ? `His most common dismissal mode is ${topDismissal.dismissal_kind}, so fielding and bowling plans should be built around that exit route.` : ""}
        </p>
      </div>
    `;
  }

  function renderStyle(summary) {
    const style = summary.style || {};
    els.styleContext.innerHTML = `
      <div class="compare-card">
        <h5>${summary.player}</h5>
        <div class="summary-line"><span>Handedness</span><strong>${style.handedness || "Unknown"}</strong></div>
        <div class="summary-line"><span>Phase identity</span><strong>${style.phase_identity || "Unknown"}</strong></div>
        <div class="summary-line"><span>Scoring style</span><strong>${style.scoring_style || "Unknown"}</strong></div>
        <div class="summary-line"><span>Pace / spin bias</span><strong>${style.pace_spin_bias || "Unknown"}</strong></div>
        <div class="summary-line"><span>Pressure trait</span><strong>${style.pressure_trait || "Unknown"}</strong></div>
      </div>
      <div class="compare-card">
        <h5>Descriptor</h5>
        <p>${style.style_note || "This profile is derived from ball-by-ball phase, pressure, and bowling-type behavior."}</p>
      </div>
    `;
  }

  function renderPhaseCards(rows) {
    els.phaseCards.innerHTML = rows
      .map(
        (row) => `
          <div class="compare-card">
            <h5>${titleCase(row.phase)}</h5>
            <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
            <div class="summary-line"><span>Strike rate</span><strong>${formatDecimal(row.strike_rate, 1)}</strong></div>
            <div class="summary-line"><span>Impact score</span><strong>${formatDecimal(row.impact_score, 1)}</strong></div>
            <div class="summary-line"><span>Dismissals</span><strong>${row.dismissals}</strong></div>
          </div>
        `
      )
      .join("");
  }

  function renderPressureCards(rows) {
    els.pressureCards.innerHTML = rows
      .map(
        (row) => `
          <div class="compare-card">
            <h5>${row.pressure_state}</h5>
            <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
            <div class="summary-line"><span>Strike rate</span><strong>${formatDecimal(row.strike_rate, 1)}</strong></div>
            <div class="summary-line"><span>Dismissal rate</span><strong>${formatDecimal(row.dismissal_rate, 3)}</strong></div>
            <div class="summary-line"><span>Matches</span><strong>${row.matches}</strong></div>
          </div>
        `
      )
      .join("");
  }

  function renderFamilyCards(rows) {
    els.familyCards.innerHTML = rows.length
      ? rows
          .map(
            (row) => `
              <div class="compare-card">
                <h5>${row.bowl_family}</h5>
                <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
                <div class="summary-line"><span>Strike rate</span><strong>${formatDecimal(row.strike_rate, 1)}</strong></div>
                <div class="summary-line"><span>Dismissals</span><strong>${row.dismissals}</strong></div>
                <div class="summary-line"><span>Dismissal rate</span><strong>${formatDecimal(row.dismissal_rate, 3)}</strong></div>
              </div>
            `
          )
          .join("")
      : `<div class="compare-card"><p>No usable pace-spin split sample yet.</p></div>`;
  }

  function renderMethodology() {
    els.methodology.innerHTML = `
      <div class="method-card">
        <h5>What This Module Measures</h5>
        <p>${data.methodology.summary}</p>
      </div>
      <div class="method-card">
        <h5>What It Cannot See Yet</h5>
        <p>${data.methodology.limitations}</p>
      </div>
    `;
  }

  function renderTables(player) {
    renderTable(
      els.venueTable,
      [
        { key: "venue", label: "Venue" },
        { key: "runs", label: "Runs" },
        { key: "matches", label: "Matches" },
        { key: "strike_rate", label: "SR", render: (value) => formatDecimal(value, 1) },
        { key: "dismissals", label: "Outs" },
      ],
      venueRows(player)
    );
    renderTable(
      els.venuePressureTable,
      [
        { key: "venue", label: "Venue" },
        { key: "runs", label: "Runs" },
        { key: "matches", label: "Matches" },
        { key: "strike_rate", label: "Pressure SR", render: (value) => formatDecimal(value, 1) },
        { key: "dismissals", label: "Outs" },
      ],
      venuePressureRows(player)
    );
    renderTable(
      els.dismissalTable,
      [
        { key: "dismissal_kind", label: "Dismissal" },
        { key: "count", label: "Count" },
        { key: "share", label: "Share", render: (value) => `${formatDecimal(value * 100, 1)}%` },
      ],
      dismissalRows(player)
    );
    renderTable(
      els.targetTable,
      [
        { key: "bowler_name", label: "Bowler" },
        { key: "runs", label: "Runs" },
        { key: "balls", label: "Balls" },
        { key: "strike_rate", label: "SR", render: (value) => formatDecimal(value, 1) },
        { key: "dismissals", label: "Outs" },
      ],
      bestMatchups(matchupRows(player))
    );
    renderTable(
      els.troubleTable,
      [
        { key: "bowler_name", label: "Bowler" },
        { key: "dismissals", label: "Outs" },
        { key: "balls", label: "Balls" },
        { key: "strike_rate", label: "SR", render: (value) => formatDecimal(value, 1) },
        { key: "dismissal_rate", label: "Out Rate", render: (value) => formatDecimal(value, 3) },
      ],
      troubleMatchups(matchupRows(player))
    );
  }

  function render() {
    const player = currentPlayer();
    const summary = data.summaries[player];
    if (!summary) return;
    const phases = phaseRows(player);
    const pressure = pressureRows(player);
    const families = familyRows(player);
    const venues = venueRows(player);
    const dismissals = dismissalRows(player);

    renderHeadline(summary);
    renderScoutingCall(player, summary, phases, pressureEdge(pressure), families, venues, dismissals);
    renderStyle(summary);
    renderPhaseCards(phases);
    renderPressureCards(pressure);
    renderFamilyCards(families);
    renderTables(player);
    renderMethodology();
  }

  function init() {
    els.horizon.innerHTML = ["All-Time", "Active"]
      .map((value) => `<option value="${value}">${value}</option>`)
      .join("");
    els.horizon.value = "Active";
    setOptions(currentOptions(), "Yashaswi Jaiswal");
    els.horizon.addEventListener("change", () => {
      setOptions(currentOptions(), currentPlayer());
      render();
    });
    els.search.addEventListener("change", render);
    render();
  }

  init();
})();
