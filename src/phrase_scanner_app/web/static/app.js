/* PhraseScanner — client-side interactivity */
(function () {
  'use strict';

  const form = document.getElementById('scan-form');
  const scanBtn = document.getElementById('scan-btn');
  const statusBox = document.getElementById('status');
  const elapsedEl = document.getElementById('elapsed');
  const errorEl = document.getElementById('form-error');
  const resultsSection = document.getElementById('results');
  const statsRow = document.getElementById('stats-row');
  const topPhrasesCard = document.getElementById('top-phrases-card');
  const topPhrasesList = document.getElementById('top-phrases');
  const foundBody = document.getElementById('found-body');
  const scannedBody = document.getElementById('scanned-body');
  const foundCount = document.getElementById('found-count');
  const scannedCount = document.getElementById('scanned-count');
  const foundFilter = document.getElementById('found-filter');
  const scannedFilter = document.getElementById('scanned-filter');
  const foundEmpty = document.getElementById('found-empty');
  const scannedEmpty = document.getElementById('scanned-empty');
  const scanMeta = document.getElementById('scan-meta');
  const stopBtn = document.getElementById('stop-btn');
  const stoppedNote = document.getElementById('stopped-note');

  let elapsedTimer = null;
  let lastPayload = null;   // full /api/scan response, used for downloads
  let foundRows = [];       // pages with at least one match
  let scannedRows = [];     // pages scanned with no matches
  const sortState = { found: { key: null, dir: 1 }, scanned: { key: null, dir: 1 } };
  const NUMERIC_KEYS = new Set(['Phrases Found', 'Depth', 'Status Code']);

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }
  function clearError() {
    errorEl.hidden = true;
    errorEl.textContent = '';
  }

  function startElapsed() {
    let seconds = 0;
    elapsedEl.textContent = '0';
    clearInterval(elapsedTimer);
    elapsedTimer = setInterval(function () {
      seconds += 1;
      elapsedEl.textContent = String(seconds);
    }, 1000);
  }
  function stopElapsed() { clearInterval(elapsedTimer); }

  stopBtn.addEventListener('click', async function () {
    stopBtn.disabled = true;
    stopBtn.textContent = 'Stopping…';
    try {
      await fetch('/api/stop', { method: 'POST' });
    } catch (err) {
      /* the scan will end on its own; nothing else to do */
    }
  });

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    clearError();

    const payload = {
      urls: document.getElementById('urls').value,
      phrases: document.getElementById('phrases').value,
      delay: parseFloat(document.getElementById('delay').value),
      max_pages: parseInt(document.getElementById('max_pages').value, 10),
      max_depth: parseInt(document.getElementById('max_depth').value, 10),
    };

    scanBtn.disabled = true;
    scanBtn.textContent = 'Scanning…';
    stopBtn.disabled = false;
    stopBtn.textContent = 'Stop';
    statusBox.hidden = false;
    stoppedNote.hidden = true;
    startElapsed();

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        showError(data.error || 'Scan failed. Please check your input.');
        return;
      }

      lastPayload = data;
      renderResults(data);
    } catch (err) {
      showError('Could not reach the scanner. Is the server still running?');
    } finally {
      stopElapsed();
      statusBox.hidden = true;
      scanBtn.disabled = false;
      scanBtn.textContent = 'Scan now';
    }
  });

  function splitResults(rows) {
    const found = [];
    const scanned = [];
    (rows || []).forEach(function (r) {
      if (Number(r['Phrases Found']) > 0) found.push(r);
      else scanned.push(r);
    });
    return { found: found, scanned: scanned };
  }

  function renderResults(data) {
    const info = data.scan_info;
    stoppedNote.hidden = !info.stopped_early;
    scanMeta.textContent =
      'Scanned ' + info.total_pages_scanned + ' pages across ' + info.total_websites +
      ' site(s) · limits: ' + info.max_pages_per_site + ' pages, depth ' + info.max_depth +
      ', delay ' + info.delay + 's · ' + new Date(info.scan_date).toLocaleString();

    const stats = [
      { value: info.total_pages_scanned, label: 'Pages scanned' },
      { value: info.successful_scans, label: 'Successful' },
      { value: info.failed_scans, label: 'Failed' },
      { value: info.pages_with_phrases, label: 'Pages with matches' },
      { value: info.phrases_searched.length, label: 'Phrases searched' },
    ];
    statsRow.innerHTML = stats.map(function (s) {
      return '<div class="stat"><div class="stat-value">' + s.value +
        '</div><div class="stat-label">' + escapeHtml(s.label) + '</div></div>';
    }).join('');

    if (data.top_phrases && data.top_phrases.length) {
      const maxOcc = data.top_phrases[0].total_occurrences;
      topPhrasesList.innerHTML = data.top_phrases.map(function (p, i) {
        const pct = maxOcc > 0 ? Math.round((p.total_occurrences / maxOcc) * 100) : 0;
        return '<li><span class="rank">' + (i + 1) + '.</span>' +
          '<span class="phrase">' + escapeHtml(p.phrase) + '</span>' +
          '<span class="bar"><span class="bar-fill" style="width:' + pct + '%"></span></span>' +
          '<span class="count">' + p.total_occurrences + ' in ' + p.pages + ' page(s)</span></li>';
      }).join('');
      topPhrasesCard.hidden = false;
    } else {
      topPhrasesCard.hidden = true;
    }

    const split = splitResults(data.results);
    foundRows = split.found;
    scannedRows = split.scanned;
    foundFilter.value = '';
    scannedFilter.value = '';
    renderFoundTable(foundRows);
    renderScannedTable(scannedRows);

    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function statusBadge(r) {
    const failed = Boolean(r.Error);
    if (failed) return '<span class="badge error">failed</span>';
    if (r['Status Code']) return '<span class="badge">' + escapeHtml(String(r['Status Code'])) + '</span>';
    return '—';
  }

  function urlCell(url) {
    return '<td class="url"><a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(url) + '</a></td>';
  }

  function cmpRows(a, b, key, dir) {
    if (NUMERIC_KEYS.has(key)) {
      const av = a[key] === '' || a[key] == null ? -1 : Number(a[key]);
      const bv = b[key] === '' || b[key] == null ? -1 : Number(b[key]);
      const av2 = isNaN(av) ? -1 : av, bv2 = isNaN(bv) ? -1 : bv;
      return (av2 - bv2) * dir;
    }
    const av = String(a[key] || '').toLowerCase();
    const bv = String(b[key] || '').toLowerCase();
    return av < bv ? -1 * dir : av > bv ? 1 * dir : 0;
  }

  function visibleRows(rows, kind) {
    const q = (kind === 'found' ? foundFilter.value : scannedFilter.value).trim().toLowerCase();
    let out = q ? rows.filter(function (r) { return matchesFilter(r, q); }) : rows.slice();
    const sort = sortState[kind];
    if (sort.key) out.sort(function (a, b) { return cmpRows(a, b, sort.key, sort.dir); });
    return out;
  }

  function renderFoundTable(rows) {
    const display = visibleRows(rows, 'found');
    foundCount.textContent = foundRows.length;
    foundBody.innerHTML = display.map(function (r) {
      return '<tr>' + urlCell(r.URL) +
        '<td>' + escapeHtml(String(r['Phrases Found'])) + '</td>' +
        '<td>' + escapeHtml(r['Phrase Counts'] || '—') + '</td>' +
        '<td>' + escapeHtml(String(r.Depth)) + '</td>' +
        '<td>' + statusBadge(r) + '</td>' +
      '</tr>';
    }).join('');
    foundEmpty.hidden = display.length !== 0;
    foundEmpty.textContent = foundRows.length === 0 ? 'No pages with matches.' : 'No pages match your filter.';
    updateSortIndicators('found');
  }

  function renderScannedTable(rows) {
    const display = visibleRows(rows, 'scanned');
    scannedCount.textContent = scannedRows.length;
    scannedBody.innerHTML = display.map(function (r) {
      return '<tr>' + urlCell(r.URL) +
        '<td>' + escapeHtml(String(r.Depth)) + '</td>' +
        '<td>' + statusBadge(r) + '</td>' +
        '<td>' + escapeHtml(r.Error || '—') + '</td>' +
      '</tr>';
    }).join('');
    scannedEmpty.hidden = display.length !== 0;
    scannedEmpty.textContent = scannedRows.length === 0 ? 'No pages without matches.' : 'No pages match your filter.';
    updateSortIndicators('scanned');
  }

  function updateSortIndicators(kind) {
    const sort = sortState[kind];
    document.querySelectorAll('.th-sort[data-table="' + kind + '"]').forEach(function (btn) {
      const ind = btn.querySelector('.sort-ind');
      if (ind) ind.textContent = btn.dataset.key === sort.key ? (sort.dir === 1 ? '↑' : '↓') : '';
    });
  }

  document.querySelectorAll('.th-sort').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const kind = btn.dataset.table;
      const key = btn.dataset.key;
      const sort = sortState[kind];
      if (sort.key === key) {
        sort.dir = sort.dir === 1 ? -1 : 1;
      } else {
        sort.key = key;
        sort.dir = 1;
      }
      if (kind === 'found') renderFoundTable(foundRows); else renderScannedTable(scannedRows);
    });
  });

  function matchesFilter(row, q) {
    return (row.URL + ' ' + (row['Phrase List'] || '') + ' ' + (row.Error || '')).toLowerCase().includes(q);
  }

  foundFilter.addEventListener('input', function () {
    renderFoundTable(foundRows);
  });
  scannedFilter.addEventListener('input', function () {
    renderScannedTable(scannedRows);
  });

  document.getElementById('download-csv').addEventListener('click', function () {
    if (!lastPayload) return;
    downloadBlob(buildCsv(lastPayload.results), 'phrasescanner_results.csv', 'text/csv;charset=utf-8');
  });

  document.getElementById('download-json').addEventListener('click', function () {
    if (!lastPayload) return;
    const split = splitResults(lastPayload.results);
    const json = JSON.stringify({
      scan_info: lastPayload.scan_info,
      found_results: split.found,
      scanned_results: split.scanned,
    }, null, 2);
    downloadBlob(json, 'phrasescanner_results.json', 'application/json;charset=utf-8');
  });

  const CSV_FIELDNAMES = ['Section', 'URL', 'Phrases Found', 'Phrase List', 'Phrase Counts', 'Scan Time', 'Depth', 'Status Code', 'Error'];

  function csvEscape(value) {
    const s = String(value == null ? '' : value);
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function buildCsv(rows) {
    const split = splitResults(rows);
    const lines = [CSV_FIELDNAMES.join(',')];
    [['Found', split.found], ['Scanned', split.scanned]].forEach(function (pair) {
      pair[1].forEach(function (r) {
        lines.push(CSV_FIELDNAMES.map(function (name) {
          return csvEscape(name === 'Section' ? pair[0] : r[name]);
        }).join(','));
      });
    });
    return lines.join('\r\n');
  }

  function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
})();
