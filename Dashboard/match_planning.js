(function () {
  const data = window.DASHBOARD_DATA.match_planning;
  const els = {
    match: document.getElementById("match-select"),
    lens: document.getElementById("match-team-lens"),
    headline: document.getElementById("match-headline-cards"),
    venueSummary: document.getElementById("venue-summary"),
    venueTopBatters: document.getElementById("venue-top-batters"),
    venueTopBowlers: document.getElementById("venue-top-bowlers"),
    homeTitle: document.getElementById("home-team-title"),
    awayTitle: document.getElementById("away-team-title"),
    homeAnalysis: document.getElementById("home-team-analysis"),
    awayAnalysis: document.getElementById("away-team-analysis"),
    swot: document.getElementById("match-swot"),
    tactics: document.getElementById("match-tactics"),
  };

  function formatDecimal(value, digits = 2) {
    return Number(value || 0).toFixed(digits);
  }

  function setOptions(select, values, formatter) {
    select.innerHTML = "";
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = formatter ? formatter(value) : value;
      select.appendChild(option);
    });
  }

  function renderList(container, rows, formatter) {
    container.innerHTML = rows.map(formatter).join("");
  }

  function swotCard(title, items) {
    return `
      <div class="insight-card">
        <h5>${title}</h5>
        <ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>
      </div>
    `;
  }

  function playerCards(rows, kind) {
    return rows
      .map(
        (row) => `
          <div class="metric-card">
            <h5>${row.player}</h5>
            <strong>${formatDecimal(row.impact_score)}</strong>
            <p>${row.role} · wins added ${formatDecimal(row.wins_added)} · ${row.phase_identity || kind}</p>
          </div>
        `
      )
      .join("");
  }

  function render() {
    const match = data.matches.find((row) => String(row.match_id) === els.match.value) || data.matches[0];
    if (!match) return;

    const previousLens = els.lens.value;
    setOptions(els.lens, [match.home, match.away], (value) => `${value} Lens`);
    if ([match.home, match.away].includes(previousLens)) {
      els.lens.value = previousLens;
    } else {
      els.lens.value = match.home;
    }

    const focus = els.lens.value === match.home ? match.home_analysis : match.away_analysis;
    const opposition = els.lens.value === match.home ? match.away_analysis : match.home_analysis;

    els.headline.innerHTML = `
      <div class="replay-card">
        <h4>Fixture</h4>
        <strong>${match.label}</strong>
        <p>${match.date} · ${match.start}</p>
      </div>
      <div class="replay-card">
        <h4>Venue</h4>
        <strong>${match.venue}</strong>
        <p>${match.venue_profile.innings_count || 0} innings in the historical sample.</p>
      </div>
      <div class="replay-card">
        <h4>Team Lens</h4>
        <strong>${els.lens.value}</strong>
        <p>${focus.active_count} active players with usable evidence in the squad view.</p>
      </div>
      <div class="replay-card">
        <h4>Average Total</h4>
        <strong>${match.venue_profile.avg_total ? formatDecimal(match.venue_profile.avg_total, 1) : "N/A"}</strong>
        <p>Venue-wide historical innings total from the ball-by-ball archive.</p>
      </div>
    `;

    renderList(
      els.venueSummary,
      (match.venue_profile.phase_conditions || []).map((row) => ({
        title: row.phase.charAt(0).toUpperCase() + row.phase.slice(1),
        runRate: row.run_rate,
        wicketRate: row.wicket_rate,
      })),
      (row) => `
        <div class="metric-card">
          <h5>${row.title}</h5>
          <strong>${formatDecimal(row.runRate, 2)}</strong>
          <p>Run rate ${formatDecimal(row.runRate, 2)} · wicket rate ${formatDecimal(row.wicketRate, 3)}</p>
        </div>
      `
    );

    renderList(
      els.venueTopBatters,
      match.venue_profile.top_batters || [],
      (row) => `
        <div class="metric-card">
          <h5>${row.player}</h5>
          <strong>${formatDecimal(row.strike_rate, 1)}</strong>
          <p>${row.matches} matches · ${row.balls} balls at this venue.</p>
        </div>
      `
    );
    renderList(
      els.venueTopBowlers,
      match.venue_profile.top_bowlers || [],
      (row) => `
        <div class="metric-card">
          <h5>${row.player}</h5>
          <strong>${formatDecimal(row.economy, 2)}</strong>
          <p>${row.wickets} wickets · ${row.matches} matches at this venue.</p>
        </div>
      `
    );

    els.homeTitle.textContent = `${match.home} Active Core`;
    els.awayTitle.textContent = `${match.away} Active Core`;
    els.homeAnalysis.innerHTML = `
      <div class="insight-card">
        <h5>Top Batters</h5>
        <div class="metric-stack">${playerCards(match.home_analysis.top_batters || [], "batting")}</div>
      </div>
      <div class="insight-card">
        <h5>Top Bowlers</h5>
        <div class="metric-stack">${playerCards(match.home_analysis.top_bowlers || [], "bowling")}</div>
      </div>
    `;
    els.awayAnalysis.innerHTML = `
      <div class="insight-card">
        <h5>Top Batters</h5>
        <div class="metric-stack">${playerCards(match.away_analysis.top_batters || [], "batting")}</div>
      </div>
      <div class="insight-card">
        <h5>Top Bowlers</h5>
        <div class="metric-stack">${playerCards(match.away_analysis.top_bowlers || [], "bowling")}</div>
      </div>
    `;

    els.swot.innerHTML = `
      <div class="insight-stack">
        ${swotCard(`${els.lens.value} Strengths`, focus.swot.strengths || [])}
        ${swotCard(`${els.lens.value} Weaknesses`, focus.swot.weaknesses || [])}
      </div>
      <div class="insight-stack">
        ${swotCard(`${els.lens.value} Opportunities`, focus.swot.opportunities || [])}
        ${swotCard(`${els.lens.value} Threats`, focus.swot.threats || [])}
      </div>
    `;

    els.tactics.innerHTML = `
      <div class="insight-card">
        <h5>${els.lens.value} Tactical Plan</h5>
        <ul>${(focus.tactics || []).map((item) => `<li>${item}</li>`).join("")}</ul>
      </div>
      <div class="insight-card">
        <h5>Opposition Watch</h5>
        <ul>${(opposition.swot.strengths || []).slice(0, 2).map((item) => `<li>${item}</li>`).join("")}</ul>
      </div>
      <div class="insight-card">
        <h5>Method Note</h5>
        <p>${data.methodology.summary}</p>
      </div>
    `;
  }

  function init() {
    setOptions(els.match, data.matches.map((row) => String(row.match_id)), (value) => {
      const match = data.matches.find((row) => String(row.match_id) === value);
      return match ? `${match.date} · ${match.label}` : value;
    });
    [els.match, els.lens].forEach((element) => element.addEventListener("change", render));
    render();
  }

  init();
})();
