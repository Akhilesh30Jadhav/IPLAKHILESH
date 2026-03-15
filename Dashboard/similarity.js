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

    let rows = (profile.comps || []).map((comp) => {
      const target = profiles[comp.player];
      return {
        ...comp,
        expected_price: target && target.market && target.market.expected_price,
        role_bucket: target && target.market && target.market.role_bucket,
        is_overseas: target && target.market && target.market.is_overseas,
      };
    });
    if (els.mode.value === "domestic_replacement") {
      rows = rows.filter((row) => row.is_overseas === false);
    } else if (els.mode.value === "cheaper_alternative") {
      const anchorPrice = profile.market && profile.market.expected_price;
      rows = rows.filter((row) => row.expected_price != null && (anchorPrice == null || row.expected_price < anchorPrice));
    }

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
        <p>${profile.market && profile.market.expected_price != null ? `Expected market price ${formatDecimal(profile.market.expected_price)} Cr.` : "No direct auction-market tag for this player."}</p>
      </div>
      <div class="metric-card">
        <h5>Search Mode</h5>
        <strong>${els.mode.options[els.mode.selectedIndex].textContent}</strong>
        <p>Uses the stored comp network, then filters candidates by domestic status or cheaper market price where relevant.</p>
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
