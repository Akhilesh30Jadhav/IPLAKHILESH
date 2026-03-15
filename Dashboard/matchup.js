(function () {
  const data = window.DASHBOARD_DATA.matchups;
  const PHASES = ["powerplay", "middle", "death"];
  const PHASE_BASELINE_SR = { powerplay: 135, middle: 125, death: 160 };

  const els = {
    batter: document.getElementById("matchup-batter"),
    bowler: document.getElementById("matchup-bowler"),
    batterOptions: document.getElementById("matchup-batter-options"),
    bowlerOptions: document.getElementById("matchup-bowler-options"),
    liveSummary: document.getElementById("matchup-live-summary"),
    confidence: document.getElementById("matchup-confidence"),
    h2hCards: document.getElementById("matchup-h2h-cards"),
    batterCards: document.getElementById("matchup-batter-cards"),
    bowlerTable: document.getElementById("matchup-bowler-table"),
    pressureCards: document.getElementById("matchup-pressure-cards"),
    explainability: document.getElementById("matchup-explainability"),
    deathBattingTable: document.getElementById("death-batting-table"),
    deathBowlingTable: document.getElementById("death-bowling-table"),
  };

  function formatDecimal(value, digits = 2) {
    return Number(value || 0).toFixed(digits);
  }

  function titlePhase(phase) {
    return phase.charAt(0).toUpperCase() + phase.slice(1);
  }

  function renderTable(table, columns, rows) {
    const head = columns.map((column) => `<th>${column.label}</th>`).join("");
    const body = rows
      .map(
        (row) =>
          `<tr>${columns
            .map((column) => `<td>${column.render ? column.render(row[column.key], row) : row[column.key] ?? ""}</td>`)
            .join("")}</tr>`
      )
      .join("");
    table.innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
  }

  function init() {
    els.batterOptions.innerHTML = data.batter_options.map((name) => `<option value="${name}"></option>`).join("");
    els.bowlerOptions.innerHTML = data.bowler_options.map((name) => `<option value="${name}"></option>`).join("");
    els.batter.value = data.batter_options.includes("Yashaswi Jaiswal") ? "Yashaswi Jaiswal" : data.batter_options[0] || "";
    els.bowler.value = data.bowler_options.includes("Jasprit Bumrah") ? "Jasprit Bumrah" : data.bowler_options[0] || "";
    els.batter.addEventListener("change", render);
    els.bowler.addEventListener("change", render);
    renderDeathTables();
    render();
  }

  function render() {
    const batter = els.batter.value;
    const bowler = els.bowler.value;

    const batterRows = data.batter_vs_style.filter((row) => row.batter === batter);
    const bowlerRows = data.bowler_vs_hand.filter((row) => row.bowler === bowler);
    const batterPressure = data.pressure_batting.filter((row) => row.batter === batter);
    const bowlerPressure = data.pressure_bowling.filter((row) => row.bowler === bowler);
    const totalH2H = data.head_to_head_total.find((row) => row.batter === batter && row.bowler === bowler) || null;
    const phaseH2H = data.head_to_head_phase.filter((row) => row.batter === batter && row.bowler === bowler);
    const batterPhase = data.batter_phase_profiles[batter] || {};
    const bowlerPhase = data.bowler_phase_profiles[bowler] || {};
    const batterStyle = data.batter_style_profiles[batter] || {};
    const bowlerStyle = data.bowler_style_profiles[bowler] || {};
    const phaseContest = PHASES.map((phase) => phaseContestRow(phase, batterPhase[phase], bowlerPhase[phase], phaseH2H.find((row) => row.phase === phase)));

    renderLiveSummary(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle);
    renderConfidenceLayer(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle);
    renderHeadToHeadCards(batter, bowler, totalH2H, phaseH2H);
    renderBatterCards(batter, batterRows);
    renderBowlerTable(bowlerRows);
    renderPressureCards(batter, bowler, batterPressure, bowlerPressure);
    renderExplainability(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle);
  }

  function renderConfidenceLayer(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle) {
    const directBalls = Number((totalH2H && totalH2H.balls) || 0);
    const directDismissals = Number((totalH2H && totalH2H.dismissals) || 0);
    const directLabel = directBalls >= 18 || directDismissals >= 3 ? "Strong" : directBalls >= 8 ? "Moderate" : "Weak";
    const styleKnown = [
      batterStyle.handedness && batterStyle.handedness !== "Unknown",
      batterStyle.pace_spin_bias && !String(batterStyle.pace_spin_bias).includes("limited"),
      bowlerStyle.bowling_family && bowlerStyle.bowling_family !== "Unknown",
      bowlerStyle.bowling_style && bowlerStyle.bowling_style !== "Unknown style",
      bowlerStyle.handedness_bias && !String(bowlerStyle.handedness_bias).includes("limited"),
    ].filter(Boolean).length;
    const styleLabel = styleKnown >= 4 ? "Strong" : styleKnown >= 2 ? "Moderate" : "Weak";
    const phaseCoverage = phaseContest.filter((row) => row.batter_pct > 0 || row.bowler_pct > 0).length;
    const confidenceScore = Math.max(
      25,
      Math.min(
        96,
        32 + Math.min(directBalls, 24) * 1.2 + Math.min(directDismissals, 3) * 6 + phaseCoverage * 8 + styleKnown * 5
      )
    );
    const sampleBadge =
      directBalls >= 18 ? "deep direct sample" : directBalls >= 8 ? "usable direct sample" : directBalls ? "thin direct sample" : "no direct sample";

    els.confidence.innerHTML = `
      <div class="insight-card">
        <h5>Confidence Score</h5>
        <p class="confidence-score">${formatDecimal(confidenceScore, 0)} / 100</p>
        <div class="pill-row">
          <span class="pill accent">${sampleBadge}</span>
          <span class="pill">${phaseCoverage} phase signals</span>
        </div>
      </div>
      <div class="compare-grid">
        <div class="compare-card">
          <h5>Direct Evidence</h5>
          <div class="summary-line"><span>Status</span><strong>${directLabel}</strong></div>
          <div class="summary-line"><span>Balls</span><strong>${directBalls}</strong></div>
          <div class="summary-line"><span>Dismissals</span><strong>${directDismissals}</strong></div>
        </div>
        <div class="compare-card">
          <h5>Style Inference</h5>
          <div class="summary-line"><span>Status</span><strong>${styleLabel}</strong></div>
          <div class="summary-line"><span>Known tags</span><strong>${styleKnown} / 5</strong></div>
          <div class="summary-line"><span>Interpretation</span><strong>${styleLabel === "Strong" ? "Good stylistic context" : styleLabel === "Moderate" ? "Partial stylistic context" : "Use style cautiously"}</strong></div>
        </div>
      </div>
    `;
  }

  function phaseContestRow(phase, batterProfile, bowlerProfile, h2h) {
    const batterPct = Number((batterProfile && batterProfile.impact_pct) || 0);
    const bowlerPct = Number((bowlerProfile && bowlerProfile.impact_pct) || 0);
    let h2hAdj = 0;
    let evidenceWeight = 0;
    let evidence = "No direct head-to-head sample in this phase";

    if (h2h) {
      const dismissalRate = h2h.dismissals / Math.max(h2h.balls, 1);
      const ballsWeight = Math.min(1, h2h.balls / 12);
      const dismissalWeight = Math.min(1, h2h.dismissals / 2);
      const baselineSr = PHASE_BASELINE_SR[phase] || 130;
      const srComponent = ((h2h.strike_rate - baselineSr) / 20) * 6;
      const dismissalComponent = -dismissalRate * 140;
      evidenceWeight = Math.min(1, 0.35 * ballsWeight + 0.65 * dismissalWeight);
      h2hAdj = Math.max(-45, Math.min(25, (srComponent + dismissalComponent) * (0.45 + 0.55 * evidenceWeight)));
      evidence = `${h2h.runs} runs, ${h2h.balls} balls, ${h2h.dismissals} dismissals, SR ${formatDecimal(h2h.strike_rate)}`;
    }

    const netEdge = batterPct - bowlerPct + h2hAdj;
    let winner = "Even";
    if (netEdge >= 8) winner = "Batter";
    if (netEdge <= -8) winner = "Bowler";

    return {
      phase,
      batter_pct: batterPct,
      bowler_pct: bowlerPct,
      h2h_adj: Number(h2hAdj.toFixed(2)),
      evidence_weight: Number(evidenceWeight.toFixed(2)),
      net_edge: Number(netEdge.toFixed(2)),
      winner,
      evidence,
      batter_metric: batterProfile ? `SR Bayes ${formatDecimal(batterProfile.sr_bayes)}` : "No batter rank",
      bowler_metric: bowlerProfile ? `Econ Bayes ${formatDecimal(bowlerProfile.econ_bayes)}` : "No bowler rank",
    };
  }

  function renderLiveSummary(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle) {
    const strongestBatter = phaseContest.slice().sort((a, b) => b.net_edge - a.net_edge)[0];
    const strongestBowler = phaseContest.slice().sort((a, b) => a.net_edge - b.net_edge)[0];
    const overallVerdict = buildCommentatorCall(
      batter,
      bowler,
      totalH2H,
      phaseContest,
      strongestBatter,
      strongestBowler,
      batterStyle,
      bowlerStyle
    );

    els.liveSummary.innerHTML = `
      <div class="insight-card">
        <h5>Live AI-Style Contest Call</h5>
        <p>${overallVerdict}</p>
      </div>
      <div class="compare-grid">
        <div class="compare-card">
          <h5>${batter} Style Context</h5>
          <div class="summary-line"><span>Handedness</span><strong>${batterStyle.handedness || "Unknown"}</strong></div>
          <div class="summary-line"><span>Phase identity</span><strong>${batterStyle.phase_identity || "Unknown"}</strong></div>
          <div class="summary-line"><span>Scoring style</span><strong>${batterStyle.scoring_style || "Unknown"}</strong></div>
          <div class="summary-line"><span>Pace / spin</span><strong>${batterStyle.pace_spin_bias || "Unknown"}</strong></div>
          <div class="summary-line"><span>Descriptor</span><strong>${batterStyle.style_note || "Derived from ball-by-ball profile"}</strong></div>
        </div>
        <div class="compare-card">
          <h5>${bowler} Style Context</h5>
          <div class="summary-line"><span>Bowling family</span><strong>${bowlerStyle.bowling_family || "Unknown"}</strong></div>
          <div class="summary-line"><span>Style</span><strong>${bowlerStyle.bowling_style || "Unknown"}</strong></div>
          <div class="summary-line"><span>Phase identity</span><strong>${bowlerStyle.phase_identity || "Unknown"}</strong></div>
          <div class="summary-line"><span>Attack profile</span><strong>${bowlerStyle.attack_profile || "Unknown"}</strong></div>
          <div class="summary-line"><span>Descriptor</span><strong>${bowlerStyle.style_note || "Derived from ball-by-ball profile"}</strong></div>
        </div>
      </div>
      <div class="compare-grid">
        ${phaseContest
          .map(
            (row) => `
              <div class="compare-card">
                <h5>${titlePhase(row.phase)}</h5>
                <div class="summary-line"><span>Expected edge</span><strong>${row.winner}</strong></div>
                <div class="summary-line"><span>Net score</span><strong>${formatDecimal(row.net_edge)}</strong></div>
                <div class="summary-line"><span>${batter}</span><strong>${formatDecimal(row.batter_pct, 1)} pct</strong></div>
                <div class="summary-line"><span>${bowler}</span><strong>${formatDecimal(row.bowler_pct, 1)} pct</strong></div>
                <div class="summary-line"><span>Direct evidence weight</span><strong>${formatDecimal(row.evidence_weight, 2)}</strong></div>
                <div class="summary-line"><span>Direct evidence</span><strong>${row.evidence}</strong></div>
              </div>
            `
          )
          .join("")}
      </div>
    `;
  }

  function buildCommentatorCall(batter, bowler, totalH2H, phaseContest, strongestBatter, strongestBowler, batterStyle, bowlerStyle) {
    const batterEdges = phaseContest.filter((row) => row.winner === "Batter");
    const bowlerEdges = phaseContest.filter((row) => row.winner === "Bowler");
    const batterDescriptor = batterStyle.style_note || `${batterStyle.handedness || "unknown-hand"} ${batterStyle.phase_identity || "batter"}`;
    const bowlerDescriptor = bowlerStyle.style_note || `${String(bowlerStyle.phase_identity || "bowler").toLowerCase()} with a ${String(
      bowlerStyle.attack_profile || "balanced profile"
    ).toLowerCase()}`;
    const styleLead = `${batter} comes in as ${batterDescriptor}, while ${bowler} shapes this duel as ${bowlerDescriptor}.`;
    const h2hLine = totalH2H
      ? `${bowler} has already removed ${batter} ${totalH2H.dismissals} time${totalH2H.dismissals === 1 ? "" : "s"} in ${totalH2H.balls} balls, so there is real duel evidence here rather than just broad profile strength.`
      : `There is no direct ball-by-ball record for this exact pair, so the call leans more on each player's phase profile than on head-to-head history.`;

    if (strongestBowler.net_edge <= -25) {
      return `${styleLead} ${bowler} looks in command of this matchup. The biggest squeeze comes in ${titlePhase(
        strongestBowler.phase
      )}, where the bowler's phase profile and the direct contest evidence both tilt heavily his way. ${batter} may still find moments if he survives into ${titlePhase(
        strongestBatter.phase
      )}, but the default read is that ${bowler} controls the terms of engagement. ${h2hLine}`;
    }

    if (strongestBatter.net_edge >= 20) {
      return `${styleLead} ${batter} looks well set up to take this contest on. The cleanest scoring window is ${titlePhase(
        strongestBatter.phase
      )}, where the batter's phase output clearly outpaces the bowler's control signal. ${bowler} still has his best chance to drag the contest back in ${titlePhase(
        strongestBowler.phase
      )}, but the attacking advantage sits with ${batter}. ${h2hLine}`;
    }

    if (batterEdges.length && bowlerEdges.length) {
      return `${styleLead} This feels like a properly game-state-sensitive battle. ${batter} has the better attacking window in ${batterEdges
        .map((row) => titlePhase(row.phase))
        .join(", ")}, while ${bowler} is more likely to dictate terms in ${bowlerEdges
        .map((row) => titlePhase(row.phase))
        .join(", ")}. In other words, the matchup swings with phase and usage rather than being one-way traffic. ${h2hLine}`;
    }

    return `${styleLead} This is a fairly balanced contest on the available evidence. ${titlePhase(
      strongestBatter.phase
    )} is the nearest thing to a batting release valve, while ${titlePhase(
      strongestBowler.phase
    )} is where ${bowler} is best placed to keep the upper hand. ${h2hLine}`;
  }

  function renderHeadToHeadCards(batter, bowler, totalH2H, phaseH2H) {
    const totalCard = totalH2H
      ? `
        <div class="compare-card">
          <h5>${batter} vs ${bowler}</h5>
          <div class="summary-line"><span>Runs</span><strong>${totalH2H.runs}</strong></div>
          <div class="summary-line"><span>Balls</span><strong>${totalH2H.balls}</strong></div>
          <div class="summary-line"><span>Strike Rate</span><strong>${formatDecimal(totalH2H.strike_rate)}</strong></div>
          <div class="summary-line"><span>Dismissals</span><strong>${totalH2H.dismissals}</strong></div>
        </div>
      `
      : `
        <div class="compare-card">
          <h5>${batter} vs ${bowler}</h5>
          <div class="summary-line"><span>Direct sample</span><strong>Not available</strong></div>
          <div class="summary-line"><span>Interpretation</span><strong>Use phase quality only</strong></div>
        </div>
      `;

    const phaseCards = phaseH2H.length
      ? phaseH2H
          .map(
            (row) => `
              <div class="compare-card">
                <h5>${titlePhase(row.phase)}</h5>
                <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
                <div class="summary-line"><span>Balls</span><strong>${row.balls}</strong></div>
                <div class="summary-line"><span>SR</span><strong>${formatDecimal(row.strike_rate)}</strong></div>
                <div class="summary-line"><span>Dismissals</span><strong>${row.dismissals}</strong></div>
              </div>
            `
          )
          .join("")
      : "";

    els.h2hCards.innerHTML = totalCard + phaseCards;
  }

  function renderBatterCards(batter, batterRows) {
    const rows = batterRows.length ? batterRows : [{ bowl_family: "No style match", runs: 0, balls: 0, strike_rate: 0, dismissals: 0 }];
    els.batterCards.innerHTML = rows
      .map(
        (row) => `
          <div class="compare-card">
            <h5>${batter}</h5>
            <div class="summary-line"><span>Bowling Type</span><strong>${row.bowl_family}</strong></div>
            <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
            <div class="summary-line"><span>Balls</span><strong>${row.balls}</strong></div>
            <div class="summary-line"><span>Strike Rate</span><strong>${formatDecimal(row.strike_rate)}</strong></div>
            <div class="summary-line"><span>Dismissals</span><strong>${row.dismissals}</strong></div>
          </div>
        `
      )
      .join("");
  }

  function renderBowlerTable(rows) {
    const safeRows = rows.length
      ? rows
      : [
          {
            batter_hand: "No split available",
            phase: "All",
            balls: 0,
            runs: 0,
            wickets: 0,
            economy: 0,
          },
        ];
    renderTable(
      els.bowlerTable,
      [
        { key: "batter_hand", label: "Bat Hand" },
        { key: "phase", label: "Phase" },
        { key: "balls", label: "Balls" },
        { key: "runs", label: "Runs" },
        { key: "wickets", label: "Wickets" },
        { key: "economy", label: "Economy", render: (value) => formatDecimal(value) },
      ],
      safeRows
    );
  }

  function renderPressureCards(batter, bowler, batterPressure, bowlerPressure) {
    els.pressureCards.innerHTML = [
      ...batterPressure.map(
        (row) => `
          <div class="compare-card">
            <h5>${batter} · ${row.pressure_state}</h5>
            <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
            <div class="summary-line"><span>Balls</span><strong>${row.balls}</strong></div>
            <div class="summary-line"><span>Strike Rate</span><strong>${formatDecimal(row.strike_rate)}</strong></div>
            <div class="summary-line"><span>Dismissals</span><strong>${row.dismissals}</strong></div>
          </div>
        `
      ),
      ...bowlerPressure.map(
        (row) => `
          <div class="compare-card">
            <h5>${bowler} · ${row.pressure_state}</h5>
            <div class="summary-line"><span>Runs</span><strong>${row.runs}</strong></div>
            <div class="summary-line"><span>Balls</span><strong>${row.balls}</strong></div>
            <div class="summary-line"><span>Economy</span><strong>${formatDecimal(row.economy)}</strong></div>
            <div class="summary-line"><span>Wickets</span><strong>${row.wickets}</strong></div>
          </div>
        `
      ),
    ].join("");
  }

  function renderExplainability(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle) {
    const batterFavorable = phaseContest.filter((row) => row.winner === "Batter").map((row) => titlePhase(row.phase));
    const bowlerFavorable = phaseContest.filter((row) => row.winner === "Bowler").map((row) => titlePhase(row.phase));
    const dismissalText = totalH2H
      ? `${bowler} has dismissed ${batter} ${totalH2H.dismissals} time${totalH2H.dismissals === 1 ? "" : "s"} in the ball-by-ball sample.`
      : `This exact pair has no direct dismissal history in the current sample.`;
    const matchupWhy = buildWhyItMatters(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle);
    const riskText = buildRiskRead(totalH2H, phaseContest, batterStyle, bowlerStyle);

    els.explainability.innerHTML = `
      <div class="insight-card">
        <h5>${batter} Upside</h5>
        <p>${batterFavorable.length ? `${batter} projects best in ${batterFavorable.join(", ")} because his phase impact percentile outruns the bowler's control percentile there.` : `${batter} does not hold a clear phase edge in the current model.`}</p>
      </div>
      <div class="insight-card">
        <h5>${bowler} Upside</h5>
        <p>${bowlerFavorable.length ? `${bowler} projects best in ${bowlerFavorable.join(", ")} where his phase control and wicket threat dominate the matchup engine.` : `${bowler} does not hold a clear phase edge in the current model.`}</p>
      </div>
      <div class="insight-card">
        <h5>Direct Contest Evidence</h5>
        <p>${dismissalText}</p>
        <p>${data.methodology.contest_engine}</p>
      </div>
      <div class="insight-card">
        <h5>Style Context</h5>
        <p>${batter} is profiled as a ${batterStyle.phase_identity || "batter"} with a ${String(
          batterStyle.scoring_style || "mixed scoring profile"
        ).toLowerCase()} and a tendency that is ${String(batterStyle.pace_spin_bias || "split-neutral").toLowerCase()}. ${batterStyle.style_note ? `${batterStyle.style_note}. ` : ""}${bowler} is profiled as a ${String(
          bowlerStyle.phase_identity || "bowler"
        ).toLowerCase()} with a ${String(bowlerStyle.attack_profile || "balanced attack profile").toLowerCase()} and is ${String(
          bowlerStyle.handedness_bias || "neutral by handedness"
        ).toLowerCase()}. ${bowlerStyle.style_note || ""}</p>
      </div>
      <div class="insight-card">
        <h5>Why The Matchup Matters</h5>
        <p>${matchupWhy}</p>
      </div>
      <div class="insight-card">
        <h5>Matchup Risks</h5>
        <p>${riskText}</p>
      </div>
    `;
  }

  function buildWhyItMatters(batter, bowler, totalH2H, phaseContest, batterStyle, bowlerStyle) {
    const strongestBatter = phaseContest.slice().sort((a, b) => b.net_edge - a.net_edge)[0];
    const strongestBowler = phaseContest.slice().sort((a, b) => a.net_edge - b.net_edge)[0];
    const splitLine =
      strongestBatter.phase === strongestBowler.phase
        ? `Both players' strongest signals are colliding in ${titlePhase(strongestBatter.phase)}, which is why this duel is tactically important.`
        : `${batter}'s best route is ${titlePhase(strongestBatter.phase)}, while ${bowler}'s control zone is ${titlePhase(strongestBowler.phase)}. That phase split is exactly what a captain or analyst would game-plan around.`;
    const styleLine = `${batter}'s profile leans ${String(batterStyle.pace_spin_bias || "balanced").toLowerCase()}, while ${bowler} is a ${String(
      bowlerStyle.bowling_family || "mixed"
    ).toLowerCase()} option whose identity is ${String(bowlerStyle.phase_identity || "phase-flexible").toLowerCase()}. ${batterStyle.style_note ? `${batterStyle.style_note}. ` : ""}${bowlerStyle.style_note || ""}`;
    const h2hLine = totalH2H
      ? `The head-to-head sample adds context: ${totalH2H.runs} runs off ${totalH2H.balls} balls at ${formatDecimal(totalH2H.strike_rate)} with ${totalH2H.dismissals} dismissals.`
      : `There is no direct duel sample, so tactical interpretation depends more on the broader phase record.`;
    return `${splitLine} ${styleLine} ${h2hLine}`;
  }

  function buildRiskRead(totalH2H, phaseContest, batterStyle, bowlerStyle) {
    const strongest = phaseContest.slice().sort((a, b) => Math.abs(b.net_edge) - Math.abs(a.net_edge))[0];
    if (totalH2H && totalH2H.balls <= 6) {
      return `Direct evidence is informative here, but the sample is still tiny. The model treats repeated dismissals seriously, yet a handful of balls can still exaggerate the certainty of the call. The sharpest current signal is in ${titlePhase(strongest.phase)}. Style labels such as ${String(
        batterStyle.phase_identity || "the batter profile"
      ).toLowerCase()} and ${String(bowlerStyle.phase_identity || "the bowler profile").toLowerCase()} should therefore be read as support, not proof.`;
    }
    if (!totalH2H) {
      return `The biggest risk is the absence of direct duel evidence. Without head-to-head balls, the call is driven by broader phase quality and derived style labels, which are useful but less specific to this exact contest.`;
    }
    return `This call blends broad phase quality with direct duel evidence. The main uncertainty is whether the historical interaction remains stable in the exact role, phase, and game-state where the next contest happens.`;
  }

  function renderDeathTables() {
    renderTable(
      els.deathBattingTable,
      [
        { key: "batter", label: "Batter" },
        { key: "impact_score", label: "Impact", render: (value) => Math.round(value) },
        { key: "balls", label: "Balls" },
        { key: "sr_bayes", label: "SR Bayes", render: (value) => formatDecimal(value) },
      ],
      data.death_specialists.batting
    );
    renderTable(
      els.deathBowlingTable,
      [
        { key: "bowler", label: "Bowler" },
        { key: "impact_score", label: "Impact", render: (value) => Math.round(value) },
        { key: "balls", label: "Balls" },
        { key: "econ_bayes", label: "Econ Bayes", render: (value) => formatDecimal(value) },
        { key: "wickets", label: "Wickets" },
      ],
      data.death_specialists.bowling
    );
  }

  init();
})();
