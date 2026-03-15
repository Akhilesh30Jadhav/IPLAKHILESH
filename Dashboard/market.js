(function () {
  const data = window.DASHBOARD_DATA;
  const roleMarket = data.auction.role_market;
  const els = {
    boardType: document.getElementById("market-board-type"),
    team: document.getElementById("market-team"),
    role: document.getElementById("market-role"),
    table: document.getElementById("market-table"),
    cards: document.getElementById("market-cards"),
    bars: document.getElementById("market-bars"),
  };

  function formatDecimal(value, digits = 2) {
    return Number(value || 0).toFixed(digits);
  }

  function humanizeRole(value) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
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

  function renderBars(container, rows) {
    if (!rows.length) {
      container.innerHTML = `<p class="muted">No records available.</p>`;
      return;
    }
    const maxValue = Math.max(...rows.map((row) => Math.abs(Number(row.value || 0))), 1);
    container.innerHTML = rows
      .map(
        (row) => `
          <div class="bar-row">
            <div class="bar-label">${row.label}</div>
            <div class="bar-track"><div class="bar-fill ${row.value < 0 ? "alt" : ""}" style="width:${(Math.abs(row.value) / maxValue) * 100}%"></div></div>
            <div class="bar-value">${row.display}</div>
          </div>
        `
      )
      .join("");
  }

  function buildRows() {
    const boardType = els.boardType.value;
    const teamCode = els.team.value;
    const role = els.role.value;
    const roleRows =
      role === "all"
        ? Object.values(roleMarket.options_by_role).flat()
        : roleMarket.options_by_role[role] || [];
    const shareMap = (data.scenario.teams[teamCode] && data.scenario.teams[teamCode].mc_share_map) || {};
    let rows = roleRows.map((row) => ({ ...row, team_share: Number(shareMap[row.player_name] || 0) }));

    if (boardType === "underpriced") {
      rows = rows.sort((a, b) => b.value_surplus - a.value_surplus);
    } else if (boardType === "overpriced") {
      rows = rows.sort((a, b) => a.value_surplus - b.value_surplus);
    } else if (boardType === "contested") {
      rows = rows.sort((a, b) => b.purchase_share - a.purchase_share || b.price_std - a.price_std);
    } else {
      rows = Object.entries(roleMarket.options_by_role)
        .map(([roleKey, options]) => {
          const top = [...options].sort((a, b) => b.value_surplus - a.value_surplus)[0];
          return top ? { ...top, role_bucket: roleKey } : null;
        })
        .filter(Boolean)
        .sort((a, b) => b.value_surplus - a.value_surplus);
    }
    return rows.slice(0, 15);
  }

  function render() {
    const rows = buildRows();
    renderTable(
      els.table,
      [
        { key: "player_name", label: "Player" },
        { key: "role_bucket", label: "Role", render: (value) => humanizeRole(value) },
        { key: "expected_price", label: "Exp. Price", render: (value) => `${formatDecimal(value)} Cr` },
        { key: "value_surplus", label: "Value Surplus", render: (value) => `${value >= 0 ? "+" : ""}${formatDecimal(value)} Cr` },
        { key: "purchase_share", label: "League Buy %", render: (value) => `${formatDecimal(value * 100, 1)}%` },
        { key: "team_share", label: `${els.team.value} Buy %`, render: (value) => `${formatDecimal(value * 100, 1)}%` },
      ],
      rows
    );

    els.cards.innerHTML = rows.slice(0, 4).map((row) => `
      <div class="metric-card">
        <h5>${row.player_name}</h5>
        <strong>${row.value_surplus >= 0 ? "+" : ""}${formatDecimal(row.value_surplus)} Cr</strong>
        <p>${humanizeRole(row.role_bucket)} · expected price ${formatDecimal(row.expected_price)} Cr · league buy rate ${formatDecimal(row.purchase_share * 100, 1)}%</p>
      </div>
    `).join("");

    renderBars(
      els.bars,
      rows.slice(0, 10).map((row) => ({
        label: row.player_name,
        value: Number(row.value_surplus),
        display: `${row.value_surplus >= 0 ? "+" : ""}${formatDecimal(row.value_surplus)} Cr`,
      }))
    );
  }

  function init() {
    setOptions(els.boardType, ["underpriced", "overpriced", "contested", "highest_surplus_by_role"], (value) =>
      value === "highest_surplus_by_role" ? "Highest Surplus By Role" : value.replace("_", " ").replace(/\b\w/g, (char) => char.toUpperCase())
    );
    setOptions(els.team, Object.keys(data.scenario.teams));
    setOptions(els.role, ["all", ...roleMarket.roles], (value) => (value === "all" ? "All Roles" : humanizeRole(value)));
    [els.boardType, els.team, els.role].forEach((el) => el.addEventListener("change", render));
    render();
  }

  init();
})();
