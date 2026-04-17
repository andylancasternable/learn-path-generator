/* charts.js – Chart.js helpers for LearnPath dashboard */

/* Shared colour palette */
const COLORS = {
  completed:   '#38d9a9',
  in_progress: '#4db8ff',
  not_started: '#2a2f45',
  accent:      '#6c63ff',
  accentLight: '#8b85ff',
  yellow:      '#f6c90e',
  muted:       '#8892a4',
  bg:          '#1a1d27',
  border:      '#2a2f45',
};

const CHART_DEFAULTS = {
  responsive: true,
  plugins: {
    legend: {
      labels: {
        color: COLORS.muted,
        font: { family: "'Segoe UI', system-ui, sans-serif", size: 12 },
      },
    },
    tooltip: {
      backgroundColor: '#22263a',
      titleColor: '#e2e8f0',
      bodyColor: '#8892a4',
      borderColor: '#2a2f45',
      borderWidth: 1,
    },
  },
};

/**
 * Render a horizontal bar chart comparing actual vs estimated hours
 * across modules on the path detail page.
 *
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {number[]} actual
 * @param {number[]} estimated
 */
function renderHoursBar(canvasId, labels, actual, estimated) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  /* Truncate long module labels */
  const shortLabels = labels.map(l => l.length > 22 ? l.slice(0, 20) + '…' : l);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: shortLabels,
      datasets: [
        {
          label: 'Actual (h)',
          data: actual,
          backgroundColor: COLORS.accent,
          borderRadius: 4,
          borderSkipped: false,
        },
        {
          label: 'Estimated (h)',
          data: estimated,
          backgroundColor: COLORS.border,
          borderRadius: 4,
          borderSkipped: false,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      indexAxis: 'y',
      scales: {
        x: {
          ticks:  { color: COLORS.muted },
          grid:   { color: 'rgba(42,47,69,.6)' },
          border: { color: COLORS.border },
        },
        y: {
          ticks:  { color: COLORS.muted, font: { size: 11 } },
          grid:   { display: false },
          border: { color: COLORS.border },
        },
      },
    },
  });
}

/**
 * Render a doughnut chart showing the module status breakdown.
 *
 * @param {string} canvasId
 * @param {{ completed: number, in_progress: number, not_started: number }} statusData
 */
function renderStatusDoughnut(canvasId, statusData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Completed', 'In Progress', 'Not Started'],
      datasets: [
        {
          data: [statusData.completed, statusData.in_progress, statusData.not_started],
          backgroundColor: [COLORS.completed, COLORS.in_progress, COLORS.not_started],
          borderColor: COLORS.bg,
          borderWidth: 3,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      cutout: '68%',
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: {
          position: 'bottom',
          labels: {
            color: COLORS.muted,
            padding: 14,
            font: { size: 12 },
            boxWidth: 12,
            borderRadius: 4,
          },
        },
      },
    },
  });
}

/**
 * Render a horizontal bar chart of overall completion % per path
 * on the dashboard page (shown when there are multiple paths).
 *
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {number[]} percentages
 */
function renderOverallChart(canvasId, labels, percentages) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const shortLabels = labels.map(l => l.length > 35 ? l.slice(0, 33) + '…' : l);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: shortLabels,
      datasets: [
        {
          label: 'Completion %',
          data: percentages,
          backgroundColor: percentages.map(p =>
            p >= 100 ? COLORS.completed :
            p > 0    ? COLORS.accent    : COLORS.border
          ),
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      indexAxis: 'y',
      scales: {
        x: {
          min: 0, max: 100,
          ticks:  { color: COLORS.muted, callback: v => v + '%' },
          grid:   { color: 'rgba(42,47,69,.6)' },
          border: { color: COLORS.border },
        },
        y: {
          ticks:  { color: COLORS.muted },
          grid:   { display: false },
          border: { color: COLORS.border },
        },
      },
    },
  });
}
