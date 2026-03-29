(function () {
  const data = window.DASHBOARD_DATA.match_planning;
  const els = {
    match: document.getElementById("match-select"),
    lens: document.getElementById("match-team-lens"),
    headline: document.getElementById("match-headline-cards"),
    venueSummary: document.getElementById("venue-summary"),
    venueTopBatters: document.getElementById("venue-top-batters"),
    venueTopBowlers: document.getElementById("venue-top-bowlers"),
    venuePressureBatters: document.getElementById("venue-pressure-batters"),
    venuePressureBowlers: document.getElementById("venue-pressure-bowlers"),
    focusAvailabilityTitle: document.getElementById("focus-availability-title"),
    oppositionAvailabilityTitle: document.getElementById("opposition-availability-title"),
    focusAvailability: document.getElementById("focus-availability"),
    oppositionAvailability: document.getElementById("opposition-availability"),
    homeTitle: document.getElementById("home-team-title"),
    awayTitle: document.getElementById("away-team-title"),
    homeAnalysis: document.getElementById("home-team-analysis"),
    awayAnalysis: document.getElementById("away-team-analysis"),
    swot: document.getElementById("match-swot"),
    tactics: document.getElementById("match-tactics"),
    aiStatus: document.getElementById("match-ai-status"),
  };
  let latestBriefRequest = 0;

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

  function tacticCard(title, items) {
    const rows = Array.isArray(items) ? items : [items];
    return `
      <div class="insight-card">
        <h5>${title}</h5>
        <ul>${rows.filter(Boolean).map((item) => `<li>${item}</li>`).join("")}</ul>
      </div>
    `;
  }

  function playerCards(rows, kind) {
    return rows
      .map(
        (row) => `
          <div class="metric-card">
            <h5>${row.player}</h5>
            <strong>Core Score ${formatDecimal(row.core_score ?? row.impact_score)}</strong>
            <p>${row.role} · wins added ${formatDecimal(row.wins_added)} · ${row.phase_identity || kind}${row.selection_probability !== undefined ? ` · sel ${formatDecimal(row.selection_probability, 2)}` : ""}</p>
          </div>
        `
      )
      .join("");
  }

  function availabilityLabel(status) {
    return {
      available: "Available",
      doubtful: "Doubtful",
      ruled_out: "Ruled Out",
      managed: "Managed",
      overseas_unavailable: "Overseas Unavailable",
      unknown: "Unknown",
    }[status] || "Unknown";
  }

  function availabilityCard(title, availability) {
    const flagged = availability?.flagged_players || [];
    const likelyXi = availability?.likely_xi || [];
    const statusCounts = availability?.status_counts || {};
    const summary = availability?.summary_line || "No Layer 3 availability intelligence loaded yet.";
    const flagsHtml = flagged.length
      ? flagged
          .slice(0, 4)
          .map((row) => {
            const sourceBits = [row.confidence, row.source_date].filter(Boolean).join(" · ");
            return `<li><strong>${row.player}</strong> · ${availabilityLabel(row.status)} · sel ${formatDecimal(row.selection_probability, 2)}${row.note ? ` · ${row.note}` : ""}${sourceBits ? ` <span class="muted">(${sourceBits})</span>` : ""}</li>`;
          })
          .join("")
      : `<li>No current flagged player statuses in the Layer 3 registry.</li>`;
    const xiHtml = likelyXi.length
      ? likelyXi
          .slice(0, 6)
          .map((row) => `<li><strong>${row.player}</strong> · ${row.role} · sel ${formatDecimal(row.selection_probability, 2)}${row.locked ? ` · ${row.lock_reason || "Locked"}` : ""}</li>`)
          .join("")
      : `<li>No projected XI available yet.</li>`;
    return `
      <div class="insight-card">
        <h5>${title}</h5>
        <p>${summary}</p>
        <p class="muted">
          XI confidence ${availability?.projected_available_xi || 0}/11 · explicit flags ${flagged.length}
          · doubtful ${statusCounts.doubtful || 0} · managed ${statusCounts.managed || 0}
          · ruled out ${statusCounts.ruled_out || 0}
        </p>
      </div>
      <div class="insight-card">
        <h5>Likely XI Watch</h5>
        <ul>${xiHtml}</ul>
      </div>
      <div class="insight-card">
        <h5>Selection Signals</h5>
        <ul>${flagsHtml}</ul>
      </div>
    `;
  }

  function humanizeBriefError(error) {
    const message = String(error?.message || error || "").trim();
    if (/429|rate limit|rate_limit_exceeded|tokens per day/i.test(message)) {
      return "Using structured fallback brief. Live AI summary is temporarily unavailable because the Groq quota has been reached.";
    }
    if (/Unable to reach Groq API|network|fetch/i.test(message)) {
      return "Using structured fallback brief. Live AI summary is temporarily unavailable because the Groq service could not be reached.";
    }
    return "Using structured fallback brief. Live AI summary is temporarily unavailable right now.";
  }

  function currentMatch() {
    return data.matches.find((row) => String(row.match_id) === els.match.value) || data.matches[0];
  }

  function syncLensOptions(match, preserveSelection = true) {
    const previousLens = els.lens.value;
    setOptions(els.lens, [match.home, match.away], (value) => `${value} Lens`);
    if (preserveSelection && [match.home, match.away].includes(previousLens)) {
      els.lens.value = previousLens;
    } else {
      els.lens.value = match.home;
    }
  }

  function render() {
    const match = currentMatch();
    if (!match) return;

    const focus = els.lens.value === match.home ? match.home_analysis : match.away_analysis;
    const opposition = els.lens.value === match.home ? match.away_analysis : match.home_analysis;
    const focusCode = els.lens.value;
    const oppositionCode = focusCode === match.home ? match.away : match.home;

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
        <strong>${focusCode}</strong>
        <p>${focus.projected_active_count || focus.active_count} projected active players with usable evidence after availability weighting.</p>
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
          <p>${row.runs} runs · ${row.matches} matches at this venue.</p>
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
    renderList(
      els.venuePressureBatters,
      match.venue_profile.pressure_batters || [],
      (row) => `
        <div class="metric-card">
          <h5>${row.player}</h5>
          <strong>${formatDecimal(row.strike_rate, 1)}</strong>
          <p>${row.runs} runs · ${row.matches} matches in high-pressure overs here.</p>
        </div>
      `
    );
    renderList(
      els.venuePressureBowlers,
      match.venue_profile.pressure_bowlers || [],
      (row) => `
        <div class="metric-card">
          <h5>${row.player}</h5>
          <strong>${formatDecimal(row.economy, 2)}</strong>
          <p>${row.wickets} wickets · ${row.matches} matches in high-pressure overs here.</p>
        </div>
      `
    );

    if (els.focusAvailabilityTitle) {
      els.focusAvailabilityTitle.textContent = `${focusCode} Availability Intel`;
    }
    if (els.oppositionAvailabilityTitle) {
      els.oppositionAvailabilityTitle.textContent = `${oppositionCode} Availability Intel`;
    }
    if (els.focusAvailability) {
      els.focusAvailability.innerHTML = availabilityCard(`${focusCode} Match-Day Watch`, focus.availability || {});
    }
    if (els.oppositionAvailability) {
      els.oppositionAvailability.innerHTML = availabilityCard(`${oppositionCode} Match-Day Watch`, opposition.availability || {});
    }

    els.homeTitle.textContent = `${focusCode} Focused Active Core`;
    els.awayTitle.textContent = `${oppositionCode} Opposition Active Core`;
    els.homeAnalysis.innerHTML = `
      <p class="muted">Sorted by CreaseIQ Core Score: phase impact + volume/control + wins added, adjusted for role and availability.</p>
      <div class="insight-card">
        <h5>Top Batters</h5>
        <div class="metric-stack">${playerCards(focus.top_batters || [], "batting")}</div>
      </div>
      <div class="insight-card">
        <h5>Top Bowlers</h5>
        <div class="metric-stack">${playerCards(focus.top_bowlers || [], "bowling")}</div>
      </div>
    `;
    els.awayAnalysis.innerHTML = `
      <p class="muted">Sorted by CreaseIQ Core Score: phase impact + volume/control + wins added, adjusted for role and availability.</p>
      <div class="insight-card">
        <h5>Top Batters</h5>
        <div class="metric-stack">${playerCards(opposition.top_batters || [], "batting")}</div>
      </div>
      <div class="insight-card">
        <h5>Top Bowlers</h5>
        <div class="metric-stack">${playerCards(opposition.top_bowlers || [], "bowling")}</div>
      </div>
    `;

    const fallbackSwotHtml = `
      <div class="insight-stack">
        ${swotCard(`${els.lens.value} Strengths`, focus.swot.strengths || [])}
        ${swotCard(`${els.lens.value} Weaknesses`, focus.swot.weaknesses || [])}
      </div>
      <div class="insight-stack">
        ${swotCard(`${els.lens.value} Opportunities`, focus.swot.opportunities || [])}
        ${swotCard(`${els.lens.value} Threats`, focus.swot.threats || [])}
      </div>
    `;
    els.swot.innerHTML = fallbackSwotHtml;

    const fallbackTacticsHtml = `
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
    els.tactics.innerHTML = fallbackTacticsHtml;

    if (els.aiStatus) {
      els.aiStatus.textContent = "Generating Groq tactical brief from Layer 1 historical intelligence and Layer 2 live context…";
    }

    const requestId = ++latestBriefRequest;

    fetch("/api/match-brief", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ match_id: match.match_id, team_lens: focusCode }),
    })
      .then(async (resp) => {
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ error: resp.statusText }));
          throw new Error(err.error || resp.statusText);
        }
        return resp.json();
      })
      .then((payload) => {
        if (!payload || !payload.brief) return;
        if (requestId !== latestBriefRequest) return;
        const brief = payload.brief;
        const aiSwot = brief.team_swot || {};
        const aiPlan = brief.tactical_plan || {};

        if (
          (aiSwot.strengths || []).length ||
          (aiSwot.weaknesses || []).length ||
          (aiSwot.opportunities || []).length ||
          (aiSwot.threats || []).length
        ) {
          els.swot.innerHTML = `
            <div class="insight-stack">
              ${swotCard(`${focusCode} Strengths`, aiSwot.strengths || [])}
              ${swotCard(`${focusCode} Weaknesses`, aiSwot.weaknesses || [])}
            </div>
            <div class="insight-stack">
              ${swotCard(`${focusCode} Opportunities`, aiSwot.opportunities || [])}
              ${swotCard(`${focusCode} Threats`, aiSwot.threats || [])}
            </div>
          `;
        }

        els.tactics.innerHTML = `
          ${tacticCard(`${focusCode} Batting Plan`, aiPlan.batting_plan || brief.recommended_plan || [])}
          ${tacticCard(`${focusCode} Bowling Plan`, aiPlan.bowling_plan || brief.tactical_edges || [])}
          ${tacticCard("Venue Plan", aiPlan.venue_plan || [brief.venue_read].filter(Boolean))}
          ${tacticCard("Opposition Watch", aiPlan.opposition_watch || brief.matchup_watch || [])}
          <div class="insight-card">
            <h5>Method Note</h5>
            <p>${aiPlan.method_note || brief.layer_note || data.methodology.summary}</p>
          </div>
        `;

        if (els.aiStatus) {
          els.aiStatus.textContent =
            brief.layer_note ||
            "Groq tactical brief loaded. Layer 1 uses historical ball-by-ball intelligence; Layer 2 adds live match context when available.";
        }
      })
      .catch((error) => {
        if (els.aiStatus) {
          els.aiStatus.textContent = humanizeBriefError(error);
        }
        els.swot.innerHTML = fallbackSwotHtml;
        els.tactics.innerHTML = fallbackTacticsHtml;
      });
  }

  // ── URL param: ?team=RR filters to that franchise ──────────────
  const urlParams = new URLSearchParams(window.location.search);
  const focusTeam = (urlParams.get("team") || "").toUpperCase();

  function applyTeamBranding() {
    if (!focusTeam) return;

    // Show sticky topbar
    const topbar = document.getElementById("rr-topbar");
    if (topbar) topbar.style.display = "flex";

    // Inject RR color overrides
    const styleTag = document.getElementById("rr-mode-styles");
    if (styleTag) {
      styleTag.textContent = `
        :root {
          --accent: #E8175D;
          --accent-soft: #FF4B82;
          --good: #E8175D;
        }
        .eyebrow { color: #E8175D !important; }
        .action-button {
          background: linear-gradient(135deg, #E8175D, #B5144A) !important;
          box-shadow: 0 4px 18px rgba(232,23,93,0.35) !important;
        }
        .replay-badge {
          background: linear-gradient(145deg, #14336B, #0C1230) !important;
          border-color: rgba(232,23,93,0.3) !important;
        }
        .replay-card { border-top: 3px solid #E8175D !important; }
        .metric-card strong { color: #E8175D !important; }
        .nav-links a:hover { background: rgba(232,23,93,0.15) !important; }
      `;
    }

    // Update page text
    const backLink = document.getElementById("back-link");
    const eyebrow = document.getElementById("page-eyebrow");
    const title = document.getElementById("page-title");
    const desc = document.getElementById("page-desc");
    const badge = document.getElementById("badge-top");
    if (backLink) { backLink.href = "./rr_hub.html"; backLink.textContent = "← Back to RR Hub"; }
    if (eyebrow) eyebrow.textContent = "Rajasthan Royals · Match Intelligence";
    if (title) title.textContent = "RR 2026 — Match-by-Match Tactical Brief";
    if (desc) desc.textContent =
      "Opponent-aware SWOT, phase-by-phase tactical plan, venue specialists, and pressure ratings for every RR fixture this season.";
    if (badge) badge.textContent = "RR Fixtures";

    // Show next match label in topbar
    const nextLabel = document.getElementById("rr-next-match-label");
    if (nextLabel) {
      const today = new Date().toISOString().slice(0, 10);
      const next = getTeamMatches().find((m) => m.date >= today);
      if (next) {
        const daysUntil = Math.round(
          (new Date(next.date) - new Date(today)) / 86400000
        );
        const label = daysUntil === 0 ? "MATCH DAY"
          : daysUntil === 1 ? "Tomorrow"
          : `In ${daysUntil} days`;
        nextLabel.textContent = `Next: ${next.label} · ${label}`;
      }
    }
  }

  function getTeamMatches() {
    if (!focusTeam) return data.matches;
    return data.matches.filter(
      (m) => m.home === focusTeam || m.away === focusTeam
    );
  }

  function getNextMatchId(matches) {
    const today = new Date().toISOString().slice(0, 10);
    const upcoming = matches.filter((m) => m.date >= today);
    if (upcoming.length > 0) return String(upcoming[0].match_id);
    return String(matches[matches.length - 1].match_id);
  }

  function init() {
    applyTeamBranding();

    const visibleMatches = getTeamMatches();

    setOptions(els.match, visibleMatches.map((row) => String(row.match_id)), (value) => {
      const match = data.matches.find((row) => String(row.match_id) === value);
      return match ? `${match.date} · ${match.label}` : value;
    });

    // Auto-select next upcoming match
    const nextId = getNextMatchId(visibleMatches);
    els.match.value = nextId;

    const initialMatch = currentMatch();
    if (initialMatch) {
      syncLensOptions(initialMatch, false);
      // Auto-select focus team lens if ?team= is set
      if (focusTeam && [initialMatch.home, initialMatch.away].includes(focusTeam)) {
        els.lens.value = focusTeam;
      }
    }

    els.match.addEventListener("change", () => {
      const match = currentMatch();
      if (!match) return;
      syncLensOptions(match, false);
      if (focusTeam && [match.home, match.away].includes(focusTeam)) {
        els.lens.value = focusTeam;
      }
      render();
    });
    els.lens.addEventListener("change", () => {
      render();
    });
    render();
  }

  init();
})();
