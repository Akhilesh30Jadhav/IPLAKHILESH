(function () {
  const data = window.DASHBOARD_DATA.players;
  const els = {
    horizon: document.getElementById("similarity-horizon"),
    type: document.getElementById("similarity-type"),
    mode: document.getElementById("similarity-mode"),
    player: document.getElementById("similarity-player"),
    options: document.getElementById("similarity-player-options"),
    table: document.getElementById("similarity-table"),
    summary: document.getElementById("similarity-summary"),
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

  function currentProfiles() {
    const profiles = els.type.value === "batter" ? data.batter_profiles : data.bowler_profiles;
    if (els.horizon.value !== "active") return profiles;
    return Object.fromEntries(Object.entries(profiles).filter(([, profile]) => Number(profile.summary.last_year || 0) >= 2025));
  }

  function similarityReason(primaryStyle, otherStyle, type) {
    const keys =
      type === "batter"
        ? ["phase_identity", "scoring_style", "pace_spin_bias", "pressure_trait", "handedness"]
        : ["phase_identity", "attack_profile", "bowling_family", "handedness_bias", "pressure_trait"];
    const labels = {
      handedness: "same handedness",
      phase_identity: "same phase role",
      scoring_style: "similar scoring style",
      pace_spin_bias: "similar pace-spin profile",
      bowling_family: "same bowling family",
      attack_profile: "similar attack profile",
      handedness_bias: "similar handedness matchup profile",
      pressure_trait: "similar pressure response",
    };
    const shared = keys.filter((key) => primaryStyle[key] && primaryStyle[key] === otherStyle[key]).map((key) => labels[key]);
    return shared.slice(0, 2).join(", ") || (type === "batter"
      ? "closest overall batting profile by phase and scoring pattern"
      : "closest overall bowling profile by phase, control, and wicket shape");
  }

  function similarityScore(profile, other, type) {
    const radarDiff =
      profile.radar.reduce((sum, axis, index) => sum + Math.abs(Number(axis.value || 0) - Number((other.radar[index] && other.radar[index].value) || 0)), 0) /
      Math.max(profile.radar.length, 1);
    const style = profile.style || {};
    const otherStyle = other.style || {};
    let score = 92 - 1.1 * radarDiff;
    if (type === "batter") {
      if (style.handedness === otherStyle.handedness && style.handedness && style.handedness !== "Unknown") score += 2;
      if (style.phase_identity === otherStyle.phase_identity) score += 3;
      if (style.scoring_style === otherStyle.scoring_style) score += 2;
      if (style.pace_spin_bias === otherStyle.pace_spin_bias) score += 2;
      if (style.pressure_trait === otherStyle.pressure_trait) score += 1;
    } else {
      if (style.bowling_family === otherStyle.bowling_family && style.bowling_family && style.bowling_family !== "Unknown") score += 3;
      if (style.phase_identity === otherStyle.phase_identity) score += 3;
      if (style.attack_profile === otherStyle.attack_profile) score += 2;
      if (style.handedness_bias === otherStyle.handedness_bias) score += 1;
      if (style.pressure_trait === otherStyle.pressure_trait) score += 1;
    }
    return Math.max(0, Math.min(98, score));
  }

  function refreshOptions() {
    const names = Object.keys(currentProfiles()).sort();
    els.options.innerHTML = names.map((name) => `<option value="${name}"></option>`).join("");
    if (!names.includes(els.player.value)) {
      els.player.value = names[0] || "";
    }
  }

  function render() {
    const profiles = currentProfiles();
    const profile = profiles[els.player.value] || profiles[Object.keys(profiles)[0]];
    if (!profile) return;
    els.player.value = profile.player;

    let rows = Object.values(profiles)
      .filter((candidate) => candidate.player !== profile.player)
      .map((candidate) => ({
        player: candidate.player,
        similarity_score: similarityScore(profile, candidate, els.type.value),
        reason: similarityReason(profile.style || {}, candidate.style || {}, els.type.value),
        expected_price: candidate.market && candidate.market.expected_price,
        role_bucket: candidate.market && candidate.market.role_bucket,
        is_overseas: candidate.market && candidate.market.is_overseas,
      }));
    if (els.mode.value === "domestic_replacement") {
      rows = rows.filter((row) => row.is_overseas === false);
    } else if (els.mode.value === "cheaper_alternative") {
      const anchorPrice = profile.market && profile.market.expected_price;
      rows = rows.filter((row) => row.expected_price != null && (anchorPrice == null || row.expected_price < anchorPrice));
    }
    rows = rows.sort((a, b) => b.similarity_score - a.similarity_score || (a.expected_price ?? 999) - (b.expected_price ?? 999)).slice(0, 20);

    renderTable(
      els.table,
      [
        { key: "player", label: "Player" },
        { key: "similarity_score", label: "Similarity", render: (value) => `${formatDecimal(value, 1)}%` },
        { key: "reason", label: "Why" },
        { key: "role_bucket", label: "Role", render: (value) => (value ? value.replaceAll("_", " ") : "--") },
        { key: "expected_price", label: "Exp. Price", render: (value) => (value == null ? "--" : `${formatDecimal(value)} Cr`) },
      ],
      rows
    );

    els.summary.innerHTML = `
      <div class="metric-card">
        <h5>${profile.player}</h5>
        <strong>${profile.trend_signal || "stable"}</strong>
        <p>${els.horizon.value === "active" ? "Active-only player pool." : "All-time player pool."} ${profile.market && profile.market.expected_price != null ? `Expected market price ${formatDecimal(profile.market.expected_price)} Cr.` : "No direct auction-market tag for this player."}</p>
      </div>
      <div class="metric-card">
        <h5>Search Mode</h5>
        <strong>${els.mode.options[els.mode.selectedIndex].textContent}</strong>
        <p>${rows.length} candidates after applying the current horizon and mode filters.</p>
      </div>
    `;
  }

  function init() {
    setOptions(els.horizon, ["all_time", "active"], (value) => (value === "all_time" ? "All-Time" : "Active"));
    setOptions(els.type, ["batter", "bowler"], (value) => value.charAt(0).toUpperCase() + value.slice(1));
    setOptions(els.mode, ["most_similar", "domestic_replacement", "cheaper_alternative"], (value) =>
      value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase())
    );
    [els.horizon, els.type, els.mode].forEach((el) =>
      el.addEventListener("change", () => {
        refreshOptions();
        render();
      })
    );
    els.player.addEventListener("change", render);
    refreshOptions();
    render();
  }

  init();
})();
