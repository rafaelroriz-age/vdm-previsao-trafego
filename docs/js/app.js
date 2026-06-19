/**
 * app.js — Previsão de Tráfego (Regressão OLS)
 * Frontend de visualização + configuração/execução do pipeline (estilo Streamlit).
 */
(function () {
    'use strict';

    var TARGETS = ['vmd', 'vmdc', 'n_usace', 'n_aashto'];
    var TARGET_LABELS = { vmd: 'VMD', vmdc: 'VMDc', n_usace: 'N-USACE', n_aashto: 'N-AASHTO' };
    var TARGET_UNIT = { vmd: 'veíc/dia', vmdc: 'veíc. pesados/dia', n_usace: 'rep. eixo (USACE)', n_aashto: 'rep. eixo (AASHTO)' };

    var SOURCE_COLORS = { observado: '#22c55e', previsto: '#3b82f6', media_global: '#f59e0b' };
    var SOURCE_LABELS = { observado: 'Observado', previsto: 'Previsto (regressão)', media_global: 'Previsto (média)' };
    var SCALE_COLORS = ['#2b83ba', '#abdda4', '#ffffbf', '#fdae61', '#d7191c', '#800000'];

    var CLASS_COLORS = {
        'Radiais': '#e74c3c', 'Longitudinais': '#3498db', 'Transversais': '#2ecc71',
        'Diagonais': '#f39c12', 'Ligações': '#9b59b6'
    };

    var DATA = {};
    var PIPELINE = { defaultConfig: null, options: null };
    var state = { target: 'vmd', tab: 'resultado', breaks: [], filters: {} };
    var map, currentLayers = [];
    var charts = {};

    /* ─────────── Utils ─────────── */
    function fmt(n) {
        if (n === null || n === undefined || isNaN(n)) return '-';
        if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + ' M';
        if (Math.abs(n) >= 1e3) return Math.round(n).toLocaleString('pt-BR');
        return (Math.round(n * 100) / 100).toLocaleString('pt-BR');
    }
    function quantileBreaks(values, n) {
        var v = values.filter(function (x) { return x !== null && !isNaN(x); }).sort(function (a, b) { return a - b; });
        if (!v.length) return [0, 1, 2, 3, 4, 5];
        var breaks = [];
        for (var i = 0; i < n; i++) breaks.push(v[Math.floor((i / n) * (v.length - 1))]);
        breaks.push(v[v.length - 1]);
        return breaks;
    }
    function colorFor(value, breaks) {
        if (value === null || isNaN(value)) return '#475569';
        for (var i = breaks.length - 2; i >= 0; i--) {
            if (value >= breaks[i]) return SCALE_COLORS[Math.min(i, SCALE_COLORS.length - 1)];
        }
        return SCALE_COLORS[0];
    }
    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
    function showPipelineStatus(msg, isError) {
        var el = document.getElementById('pipeline-status');
        if (!el) return;
        el.style.color = isError ? '#ef4444' : '#94a3b8';
        el.textContent = msg || '';
    }
    async function apiGet(url) {
        var r = await fetch(url);
        if (!r.ok) throw new Error('Falha API GET ' + url + ' (' + r.status + ')');
        return r.json();
    }
    async function apiPost(url, payload) {
        var r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload || {})
        });
        var out = await r.json().catch(function () { return {}; });
        if (!r.ok || out.ok === false) {
            throw new Error(out.error || out.message || ('Falha API POST ' + url));
        }
        return out;
    }

    /* ─────────── Map ─────────── */
    function initMap() {
        map = L.map('map', { center: [-15.7, -49.6], zoom: 7, zoomControl: false });
        L.control.zoom({ position: 'topright' }).addTo(map);
        L.control.scale({ position: 'bottomleft', imperial: false }).addTo(map);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; CARTO', subdomains: 'abcd', maxZoom: 19
        }).addTo(map);
    }
    function clearLayers() { currentLayers.forEach(function (l) { map.removeLayer(l); }); currentLayers = []; }
    function fitToData() {
        var l = L.geoJSON(DATA.segments);
        var b = l.getBounds();
        if (b.isValid()) map.fitBounds(b, { padding: [20, 20] });
    }

    function passesFilter(p) {
        var t = state.target, f = state.filters;
        var src = p[t + '_source'];
        var val = p[t + '_final'];
        if (f.source && f.source !== 'all' && src !== f.source) return false;
        if (f.regional && f.regional !== 'all' && String(p.regional) !== f.regional) return false;
        if (f.classe && f.classe !== 'all' && p.classe !== f.classe) return false;
        if (f.min != null && val < f.min) return false;
        if (f.max != null && val > f.max) return false;
        return true;
    }

    function renderMap() {
        clearLayers();
        var t = state.target;
        var layer = L.geoJSON(DATA.segments, {
            filter: function (feat) { return passesFilter(feat.properties); },
            style: function (feat) {
                var p = feat.properties;
                var src = p[t + '_source'];
                return {
                    color: colorFor(p[t + '_final'], state.breaks),
                    weight: src === 'observado' ? 3.2 : 2,
                    opacity: src === 'media_global' ? 0.45 : 0.85,
                    dashArray: src === 'observado' ? null : '5,5',
                    lineCap: 'round'
                };
            },
            onEachFeature: function (feat, l) {
                l.bindPopup(createPopup(feat.properties), { maxWidth: 320 });
                l.on('mouseover', function () { this.setStyle({ weight: 5.5, opacity: 1 }); this.bringToFront(); });
                l.on('mouseout', function () { layer.resetStyle(this); });
            }
        }).addTo(map);
        currentLayers.push(layer);
        renderLegend();
    }

    function createPopup(p) {
        var t = state.target;
        var src = p[t + '_source'] || 'previsto';
        var obs = p[t + '_obs'], pred = p[t + '_pred'], fin = p[t + '_final'];
        var rows = '';
        TARGETS.forEach(function (tt) {
            rows += '<div class="popup-detail"><span class="popup-detail-label">' + TARGET_LABELS[tt] + '</span><br>' +
                '<span class="popup-detail-value">' + fmt(p[tt + '_final']) + '</span></div>';
        });
        return '<div class="popup-content"><div class="popup-header">' +
            '<span class="popup-sre">' + (p.sre || '-') + '</span>' +
            '<span class="popup-badge ' + src + '">' + (SOURCE_LABELS[src] || src) + '</span></div>' +
            '<div class="popup-vmd" style="color:' + colorFor(fin, state.breaks) + '">' + fmt(fin) + '</div>' +
            '<div class="popup-vmd-label">' + TARGET_LABELS[t] + ' — ' + TARGET_UNIT[t] + '</div>' +
            '<div class="popup-details">' +
            '<div class="popup-detail"><span class="popup-detail-label">Observado</span><br><span class="popup-detail-value">' + fmt(obs) + '</span></div>' +
            '<div class="popup-detail"><span class="popup-detail-label">Previsto</span><br><span class="popup-detail-value">' + fmt(pred) + '</span></div>' +
            '<div class="popup-detail"><span class="popup-detail-label">GO</span><br><span class="popup-detail-value">' + (p.go || '-') + '</span></div>' +
            '<div class="popup-detail"><span class="popup-detail-label">Regional</span><br><span class="popup-detail-value">' + (p.regional || '-') + '</span></div>' +
            '<div class="popup-detail"><span class="popup-detail-label">Classe</span><br><span class="popup-detail-value">' + (p.classe || '-') + '</span></div>' +
            '<div class="popup-detail"><span class="popup-detail-label">Extensão</span><br><span class="popup-detail-value">' + (p.extensao || 0) + ' km</span></div>' +
            '</div></div>';
    }

    function renderLegend() {
        var box = document.getElementById('legend-items');
        document.getElementById('legend-title').textContent = TARGET_LABELS[state.target] + ' (' + TARGET_UNIT[state.target] + ')';
        box.innerHTML = '';
        var b = state.breaks;
        for (var i = 0; i < SCALE_COLORS.length; i++) {
            var lo = b[i], hi = b[i + 1];
            if (lo === undefined) break;
            if (hi !== undefined && Math.round(hi) === Math.round(lo)) continue; // pula faixas vazias
            var label = fmt(lo) + (hi !== undefined ? ' – ' + fmt(hi) : '+');
            box.insertAdjacentHTML('beforeend',
                '<div class="legend-item"><span class="legend-color" style="background:' + SCALE_COLORS[i] + '"></span>' + label + '</div>');
        }
        box.insertAdjacentHTML('beforeend', '<div class="legend-item" style="margin-top:6px"><span class="legend-color" style="background:#22c55e"></span>linha cheia = observado</div>');
        box.insertAdjacentHTML('beforeend', '<div class="legend-item"><span class="legend-line-dash" style="border-color:#3b82f6"></span>tracejado = previsto</div>');
    }

    function zoomToFeature(sre) {
        var feat = DATA.segments.features.find(function (f) { return f.properties.sre === sre; });
        if (!feat) return;
        var l = L.geoJSON(feat);
        map.fitBounds(l.getBounds(), { padding: [60, 60], maxZoom: 12 });
        l.addTo(map); currentLayers.push(l);
        L.geoJSON(feat).bindPopup(createPopup(feat.properties)).addTo(map).openPopup();
    }

    /* ─────────── Sidebar: Resultado ─────────── */
    function renderResultado() {
        var t = state.target;
        document.getElementById('intro-target').textContent = TARGET_LABELS[t];
        var feats = DATA.segments.features.map(function (f) { return f.properties; });
        var obs = feats.filter(function (p) { return p[t + '_source'] === 'observado'; });
        var pred = feats.filter(function (p) { return p[t + '_source'] === 'previsto'; });
        var mg = feats.filter(function (p) { return p[t + '_source'] === 'media_global'; });
        var vals = feats.map(function (p) { return p[t + '_final']; }).filter(function (x) { return x != null && !isNaN(x); });
        var mean = vals.reduce(function (a, b) { return a + b; }, 0) / (vals.length || 1);

        document.getElementById('stats-resultado').innerHTML =
            card(feats.length, 'Segmentos') +
            card(obs.length, 'Observados', 'success') +
            card(pred.length, 'Previstos (OLS)', 'accent') +
            card(mg.length, 'Previstos (média)', 'warning') +
            card(fmt(mean), 'Média ' + TARGET_LABELS[t], '', true);

        renderDistChart(vals);
        renderRegionalChart(feats);
    }
    function card(value, label, cls, wide) {
        return '<div class="stat-card' + (wide ? ' wide' : '') + '"><span class="stat-value ' + (cls || '') + '">' +
            (typeof value === 'number' ? value.toLocaleString('pt-BR') : value) + '</span><span class="stat-label">' + label + '</span></div>';
    }

    function renderDistChart(vals) {
        var b = state.breaks;
        var counts = new Array(SCALE_COLORS.length).fill(0);
        vals.forEach(function (v) {
            for (var i = b.length - 2; i >= 0; i--) { if (v >= b[i]) { counts[Math.min(i, counts.length - 1)]++; break; } }
        });
        var labels = [];
        for (var i = 0; i < counts.length; i++) labels.push(fmt(b[i]) + (b[i + 1] !== undefined ? '–' + fmt(b[i + 1]) : '+'));
        drawChart('chart-dist', 'bar', {
            labels: labels,
            datasets: [{ data: counts, backgroundColor: SCALE_COLORS }]
        }, { plugins: { legend: { display: false } }, scales: axes() });
    }

    function renderRegionalChart(feats) {
        var t = state.target;
        var groups = {};
        feats.forEach(function (p) {
            var r = p.regional || '?';
            if (!groups[r]) groups[r] = { sum: 0, n: 0 };
            var v = p[t + '_final'];
            if (v != null && !isNaN(v)) { groups[r].sum += v; groups[r].n++; }
        });
        var labels = Object.keys(groups).sort();
        var data = labels.map(function (r) { return groups[r].n ? groups[r].sum / groups[r].n : 0; });
        drawChart('chart-regional', 'bar', {
            labels: labels,
            datasets: [{ label: 'Média ' + TARGET_LABELS[t], data: data, backgroundColor: '#3b82f6' }]
        }, { indexAxis: 'y', plugins: { legend: { display: false } }, scales: axes() });
    }

    /* ─────────── Sidebar: Calibração ─────────── */
    function renderCalibracao() {
        var t = state.target;
        var cal = (DATA.calibration.targets || {})[t] || {};
        var m = cal.metrics || {};
        var scatter = cal.scatter_data || [];
        document.getElementById('stats-calibracao').innerHTML =
            card((m.r2_global != null ? m.r2_global.toFixed(3) : '-'), 'R² global', 'accent') +
            card((m.mape != null ? m.mape.toFixed(1) + '%' : '-'), 'MAPE', 'warning') +
            card(fmt(m.mae), 'MAE') +
            card(fmt(m.rmse), 'RMSE') +
            card(m.n_observacoes || 0, 'Observações', '', true);

        var pts = scatter.map(function (d) { return { x: d.observed, y: d.estimated }; });
        var maxv = Math.max.apply(null, scatter.map(function (d) { return Math.max(d.observed, d.estimated); }).concat([1]));
        drawChart('chart-scatter', 'scatter', {
            datasets: [
                { label: 'Segmentos', data: pts, backgroundColor: 'rgba(59,130,246,0.6)', pointRadius: 3 },
                { label: 'y = x', type: 'line', data: [{ x: 0, y: 0 }, { x: maxv, y: maxv }], borderColor: '#22c55e', borderDash: [5, 5], pointRadius: 0, fill: false }
            ]
        }, {
            plugins: { legend: { labels: { color: '#94a3b8', font: { size: 10 } } } },
            scales: {
                x: { title: { display: true, text: 'Observado', color: '#64748b' }, ticks: { color: '#64748b', callback: function (v) { return fmt(v); } }, grid: { color: 'rgba(51,65,85,0.3)' } },
                y: { title: { display: true, text: 'Estimado', color: '#64748b' }, ticks: { color: '#64748b', callback: function (v) { return fmt(v); } }, grid: { color: 'rgba(51,65,85,0.3)' } }
            }
        });

        var bins = [-100, -80, -50, -35, -20, 0, 20, 35, 50, 80, 100];
        var counts = new Array(bins.length - 1).fill(0);
        scatter.forEach(function (d) {
            var e = d.erro_pct; if (e == null) return;
            e = Math.max(-100, Math.min(100, e));
            for (var i = 0; i < bins.length - 1; i++) { if (e >= bins[i] && e < bins[i + 1]) { counts[i]++; break; } }
        });
        var labels = [];
        for (var i = 0; i < bins.length - 1; i++) labels.push(bins[i] + '..' + bins[i + 1]);
        var colors = labels.map(function (l) {
            var lo = parseInt(l.split('..')[0], 10);
            var a = Math.abs(lo);
            return a <= 35 ? '#22c55e' : (a <= 80 ? '#f59e0b' : '#ef4444');
        });
        drawChart('chart-resid', 'bar', { labels: labels, datasets: [{ data: counts, backgroundColor: colors }] },
            { plugins: { legend: { display: false } }, scales: axes() });
    }

    /* ─────────── Sidebar: Modelo ─────────── */
    function renderModelo() {
        var t = state.target;
        var tinfo = (DATA.metrics.targets || {})[t] || {};
        var slo = (DATA.metrics.slo || {})[t] || {};

        var ok = !!slo.aprovado;
        document.getElementById('slo-status').innerHTML =
            '<span class="badge-slo ' + (ok ? 'ok' : 'fail') + '">' + (ok ? '✓ APROVADO' : '✗ ABAIXO DO ALVO') + '</span>' +
            '<div class="note" style="margin-top:6px">R² global: <b>' + (slo.r2_global != null ? slo.r2_global.toFixed(3) : '-') + '</b> (alvo ≥ ' + (slo.r2_min != null ? slo.r2_min : '-') + ')<br>' +
            'MAPE: <b>' + (slo.mape != null ? slo.mape.toFixed(1) + '%' : '-') + '</b> (alvo ≤ ' + (slo.mape_max != null ? slo.mape_max : '-') + '%)</div>';

        var eq = tinfo.equations || {};
        var latexEl = document.getElementById('formula-latex');
        if (eq.latex && window.katex) {
            try { katex.render(eq.latex, latexEl, { throwOnError: false, displayMode: true }); }
            catch (e) { latexEl.textContent = eq.latex || '-'; }
        } else { latexEl.textContent = eq.latex || '-'; }

        document.getElementById('formula-excel-text').textContent = eq.excel || '-';
        document.getElementById('formula-texto-text').textContent = eq.texto || '-';

        var note = '';
        if (tinfo.log_transform) {
            note = 'Modelo em log: o resultado da fórmula é log(ŷ). Aplique ŷ = EXP(resultado)' +
                (tinfo.smearing ? ' × ' + tinfo.smearing.toFixed(4) + ' (fator de Duan).' : '.');
        }
        document.getElementById('formula-note').textContent = note;

        var rows = '<tr><th>Variável</th><th>Coef.</th><th>p-valor</th></tr>';
        rows += '<tr><td>intercepto</td><td class="num">' + (tinfo.intercept != null ? tinfo.intercept.toFixed(4) : '-') + '</td><td class="num">—</td></tr>';
        (tinfo.features || []).forEach(function (f) {
            rows += '<tr><td>' + f.feature + '</td><td class="num">' + f.coef.toFixed(4) + '</td><td class="num">' +
                (f.pvalue != null ? f.pvalue.toFixed(3) : '-') + '</td></tr>';
        });
        document.getElementById('coef-table').innerHTML = rows;
    }

    /* ─────────── Sidebar: Pipeline ─────────── */
    function parseTargetsChecked() {
        var t = [];
        document.querySelectorAll('.cfg-target-item').forEach(function (cb) {
            if (cb.checked) t.push(cb.value);
        });
        return t;
    }
    function selectedValuesBySelector(selector) {
        var el = document.querySelector(selector);
        if (!el) return [];
        var out = [];
        for (var i = 0; i < el.options.length; i++) {
            if (el.options[i].selected) out.push(el.options[i].value);
        }
        return out;
    }
    function renderGroupMergeControls(groupValues, currentMerges) {
        var countEl = document.getElementById('cfg-group-merge-count');
        var box = document.getElementById('cfg-group-merges-container');
        if (!countEl || !box) return;
        var n = parseInt(countEl.value || '0', 10);
        n = Math.max(0, Math.min(5, n));
        countEl.value = String(n);

        var html = '';
        for (var i = 0; i < n; i++) {
            var m = (currentMerges && currentMerges[i]) ? currentMerges[i] : null;
            var vals = m && m.values ? m.values : ((i === 0 && groupValues.indexOf('2') >= 0 && groupValues.indexOf('3') >= 0) ? ['2', '3'] : []);
            html += '<div class="merge-row">' +
                '<div class="mini-label">Grupos a fundir #' + (i + 1) + '</div>' +
                '<select multiple id="cfg-gmerge-' + i + '">' +
                (groupValues || []).map(function (g) {
                    var sel = vals.indexOf(g) >= 0 ? 'selected' : '';
                    return '<option value="' + esc(g) + '" ' + sel + '>' + esc(g) + '</option>';
                }).join('') +
                '</select>' +
                '</div>';
        }
        box.innerHTML = html;
    }
    function collectGroupMerges() {
        var countEl = document.getElementById('cfg-group-merge-count');
        if (!countEl) return [];
        var n = parseInt(countEl.value || '0', 10);
        var out = [];
        for (var i = 0; i < n; i++) {
            var vals = selectedValuesBySelector('#cfg-gmerge-' + i);
            if (vals.length >= 2) out.push({ values: vals, label: vals.join('+') });
        }
        return out;
    }
    function renderBoolMergeControls(lowCardMap, currentMerges) {
        var box = document.getElementById('cfg-bool-merges');
        if (!box) return;
        var mergeByCol = {};
        (currentMerges || []).forEach(function (m) { mergeByCol[m.column] = m; });
        var cols = Object.keys(lowCardMap || {});
        if (!cols.length) {
            box.innerHTML = '<div class="note">Sem categóricas de baixa cardinalidade para boolean merge.</div>';
            return;
        }
        box.innerHTML = cols.map(function (c) {
            var vals = lowCardMap[c] || [];
            var cur = mergeByCol[c] ? (mergeByCol[c].true_values || []) : [];
            var open = c === 'situacao' ? 'open' : '';
            return '<details class="bool-merge-box" ' + open + '>' +
                '<summary>' + esc(c) + ' (' + vals.join(' / ') + ')</summary>' +
                '<div class="bool-merge-body">' +
                '<div class="mini-label">Valores = TRUE</div>' +
                '<select multiple class="cfg-bool-select" data-col="' + esc(c) + '">' +
                vals.map(function (v) {
                    var sel = cur.indexOf(v) >= 0 ? 'selected' : '';
                    return '<option value="' + esc(v) + '" ' + sel + '>' + esc(v) + '</option>';
                }).join('') +
                '</select></div></details>';
        }).join('');
    }
    function collectBoolMerges() {
        var out = [];
        document.querySelectorAll('.cfg-bool-select').forEach(function (sel) {
            var col = sel.dataset.col;
            var vals = [];
            for (var i = 0; i < sel.options.length; i++) {
                if (sel.options[i].selected) vals.push(sel.options[i].value);
            }
            if (vals.length) {
                out.push({
                    column: col,
                    true_values: vals,
                    new_name: col + '_is_' + vals.join('_').toLowerCase()
                });
            }
        });
        return out;
    }
    function selectedOptionsValues(selectEl) {
        if (!selectEl) return [];
        var out = [];
        for (var i = 0; i < selectEl.options.length; i++) {
            if (selectEl.options[i].selected) out.push(selectEl.options[i].value);
        }
        return out;
    }
    function collectPipelineConfig() {
        var targets = parseTargetsChecked();
        var perTarget = {};
        var mandatory = {};
        targets.forEach(function (t) {
            perTarget[t] = selectedOptionsValues(document.getElementById('cfg-feats-' + t));
            mandatory[t] = selectedOptionsValues(document.getElementById('cfg-mand-' + t));
        });

        var enc = {};
        document.querySelectorAll('.cfg-enc-item').forEach(function (sel) {
            enc[sel.dataset.col] = sel.value;
        });

        return {
            dataset_path: document.getElementById('cfg-dataset').value.trim(),
            group_col: document.getElementById('cfg-group-col').value,
            targets: targets,
            group_merges: collectGroupMerges(),
            boolean_merges: collectBoolMerges(),
            features_per_target: perTarget,
            mandatory_per_target: mandatory,
            encoding_choices: enc,
            pvalue_threshold: parseFloat(document.getElementById('cfg-pvalue').value || '0.15'),
            log_transform: document.getElementById('cfg-log').checked,
            clip_predictions: document.getElementById('cfg-clip').checked,
            use_max_features: document.getElementById('cfg-use-max').checked,
            max_features: parseInt(document.getElementById('cfg-max-feat').value || '6', 10),
            use_stratified: document.getElementById('cfg-strat').checked,
            min_train_region: parseInt(document.getElementById('cfg-min-train').value || '10', 10)
        };
    }
    function renderTargetsChecks(allTargets, selected) {
        var box = document.getElementById('cfg-targets');
        if (!box) return;
        box.innerHTML = (allTargets || []).map(function (t) {
            var on = (selected || []).indexOf(t) >= 0;
            return '<label><input type="checkbox" class="cfg-target-item" value="' + esc(t) + '" ' + (on ? 'checked' : '') + '> ' + esc(t) + '</label>';
        }).join('');
    }
    function renderEncodingControls(categoricals, defaults) {
        var box = document.getElementById('cfg-encoding');
        if (!box) return;
        if (!categoricals || !categoricals.length) {
            box.innerHTML = '<div class="note">Sem colunas categóricas candidatas.</div>';
            return;
        }
        box.innerHTML = categoricals.map(function (c) {
            var v = (defaults && defaults[c]) ? defaults[c] : 'onehot';
            return '<div class="filter-group"><label>' + esc(c) + '</label>' +
                '<select class="cfg-enc-item" data-col="' + esc(c) + '">' +
                '<option value="onehot" ' + (v === 'onehot' ? 'selected' : '') + '>One-Hot</option>' +
                '<option value="label" ' + (v === 'label' ? 'selected' : '') + '>Label</option>' +
                '</select></div>';
        }).join('');
    }
    function renderFeaturesPerTarget(perTarget, selectedTargets, featuresDefault, mandatoryDefault) {
        var box = document.getElementById('cfg-features-per-target');
        if (!box) return;
        box.innerHTML = '';
        (selectedTargets || []).forEach(function (t) {
            var cands = (perTarget && perTarget[t] && perTarget[t].all) ? perTarget[t].all : [];
            var d1 = (featuresDefault && featuresDefault[t]) ? featuresDefault[t] : [];
            var d2 = (mandatoryDefault && mandatoryDefault[t]) ? mandatoryDefault[t] : [];
            var html = '<div class="feature-box">' +
                '<h4>' + esc(t) + '</h4>' +
                '<div class="mini-label">Features (CTRL para multi-seleção)</div>' +
                '<select multiple id="cfg-feats-' + esc(t) + '">' +
                cands.map(function (f) {
                    var sel = d1.indexOf(f) >= 0 ? 'selected' : '';
                    return '<option value="' + esc(f) + '" ' + sel + '>' + esc(f) + '</option>';
                }).join('') +
                '</select>' +
                '<div class="mini-label">Obrigatórias</div>' +
                '<select multiple id="cfg-mand-' + esc(t) + '">' +
                cands.map(function (f) {
                    var sel = d2.indexOf(f) >= 0 ? 'selected' : '';
                    return '<option value="' + esc(f) + '" ' + sel + '>' + esc(f) + '</option>';
                }).join('') +
                '</select>' +
                '</div>';
            box.insertAdjacentHTML('beforeend', html);
        });
    }
    async function refreshCandidatesFromUI() {
        var cfgNow = collectPipelineConfig();
        showPipelineStatus('Atualizando candidatas...', false);
        var cands = await apiPost('/api/candidates', cfgNow);
        PIPELINE.options = cands;
        var selectedTargets = cfgNow.targets;
        renderGroupMergeControls(cands.group_values || [], cfgNow.group_merges || []);
        renderBoolMergeControls(cands.low_card_categories || {}, cfgNow.boolean_merges || []);
        renderEncodingControls(cands.candidates.categorical || [], cfgNow.encoding_choices || {});
        renderFeaturesPerTarget(cands.per_target || {}, selectedTargets, cfgNow.features_per_target || {}, cfgNow.mandatory_per_target || {});
        showPipelineStatus('Candidatas atualizadas.', false);
    }
    async function runPipelineFromUI() {
        var btn = document.getElementById('btn-run-pipeline');
        var payload = collectPipelineConfig();
        if (!payload.targets || !payload.targets.length) {
            showPipelineStatus('Selecione ao menos um target.', true);
            return;
        }
        btn.disabled = true;
        showPipelineStatus('Executando pipeline... isso pode levar alguns segundos.', false);
        try {
            await apiPost('/api/run', payload);
            await loadDataFiles();
            recomputeBreaks();
            renderHeader();
            renderMap();
            renderActiveTab();
            showPipelineStatus('Pipeline concluído e mapa atualizado.', false);
            setTab('resultado');
        } catch (e) {
            showPipelineStatus('Erro: ' + e.message, true);
        } finally {
            btn.disabled = false;
        }
    }
    async function uploadDatasetFromUI() {
        var input = document.getElementById('cfg-upload');
        if (!input || !input.files || !input.files.length) {
            showPipelineStatus('Selecione um arquivo para upload.', true);
            return;
        }
        var fd = new FormData();
        fd.append('file', input.files[0]);
        showPipelineStatus('Enviando dataset...', false);
        var r = await fetch('/api/upload', { method: 'POST', body: fd });
        var out = await r.json().catch(function () { return {}; });
        if (!r.ok || out.ok === false) {
            throw new Error(out.error || 'Falha no upload');
        }
        document.getElementById('cfg-dataset').value = out.dataset_path || '';
        await refreshCandidatesFromUI();
        showPipelineStatus('Upload concluído: ' + (out.filename || 'arquivo') + '.', false);
    }
    async function initPipelinePanel() {
        try {
            var pack = await apiGet('/api/options');
            PIPELINE.defaultConfig = pack.default;
            PIPELINE.options = pack.options;

            var d = PIPELINE.defaultConfig;
            document.getElementById('cfg-dataset').value = d.dataset_path || '';

            var groupSelect = document.getElementById('cfg-group-col');
            groupSelect.innerHTML = (pack.options.columns || []).map(function (c) {
                return '<option value="' + esc(c) + '" ' + (c === d.group_col ? 'selected' : '') + '>' + esc(c) + '</option>';
            }).join('');

            var mergeCountEl = document.getElementById('cfg-group-merge-count');
            mergeCountEl.value = String((d.group_merges || []).length);
            renderGroupMergeControls(pack.options.group_values || [], d.group_merges || []);
            renderBoolMergeControls(pack.options.low_card_categories || {}, d.boolean_merges || []);

            document.getElementById('cfg-pvalue').value = d.pvalue_threshold != null ? d.pvalue_threshold : 0.15;
            document.getElementById('cfg-log').checked = !!d.log_transform;
            document.getElementById('cfg-clip').checked = !!d.clip_predictions;
            document.getElementById('cfg-use-max').checked = !!d.use_max_features;
            document.getElementById('cfg-max-feat').value = d.max_features != null ? d.max_features : 6;
            document.getElementById('cfg-strat').checked = !!d.use_stratified;
            document.getElementById('cfg-min-train').value = d.min_train_region != null ? d.min_train_region : 10;

            renderTargetsChecks(pack.options.targets_available || TARGETS, d.targets || TARGETS);
            renderEncodingControls((pack.options.candidates || {}).categorical || [], d.encoding_choices || {});
            renderFeaturesPerTarget(pack.options.per_target || {}, d.targets || TARGETS, d.features_per_target || {}, d.mandatory_per_target || {});

            document.getElementById('cfg-group-merge-count').addEventListener('change', function () {
                var cfgNow = collectPipelineConfig();
                renderGroupMergeControls((PIPELINE.options && PIPELINE.options.group_values) || [], cfgNow.group_merges || []);
            });
            document.getElementById('cfg-group-col').addEventListener('change', function () {
                refreshCandidatesFromUI().catch(function (e) { showPipelineStatus('Erro: ' + e.message, true); });
            });

            showPipelineStatus('Configuração carregada.', false);
        } catch (e) {
            showPipelineStatus('Não foi possível carregar opções da API: ' + e.message, true);
        }
    }

    /* ─────────── Charts helper ─────────── */
    function axes() {
        return {
            x: { ticks: { color: '#64748b', font: { size: 9 }, maxRotation: 60, minRotation: 0 }, grid: { color: 'rgba(51,65,85,0.3)' } },
            y: { ticks: { color: '#64748b', font: { size: 9 } }, grid: { color: 'rgba(51,65,85,0.3)' } }
        };
    }
    function drawChart(id, type, data, options) {
        var el = document.getElementById(id);
        if (!el) return;
        if (charts[id]) charts[id].destroy();
        charts[id] = new Chart(el.getContext('2d'), {
            type: type, data: data,
            options: Object.assign({ responsive: true, maintainAspectRatio: true }, options || {})
        });
    }

    /* ─────────── Header + target metrics ─────────── */
    function renderHeader() {
        var feats = DATA.segments.features.map(function (f) { return f.properties; });
        var t = state.target;
        var obs = feats.filter(function (p) { return p[t + '_source'] === 'observado'; }).length;
        var pred = feats.length - obs;
        document.getElementById('stat-total').textContent = feats.length;
        document.getElementById('stat-obs').textContent = obs;
        document.getElementById('stat-pred').textContent = pred;

        var all = DATA.metrics.slo || {};
        var allOk = all._todos_aprovados;
        var chip = document.getElementById('stat-slo');
        chip.className = 'stat-chip ' + (allOk ? 'ok' : 'fail');
        document.getElementById('stat-slo-text').textContent = allOk ? 'SLO OK' : 'SLO parcial';

        TARGETS.forEach(function (tt) {
            var s = (DATA.metrics.slo || {})[tt] || {};
            var el = document.getElementById('m-' + tt);
            if (el) el.textContent = s.r2_global != null ? 'R²=' + s.r2_global.toFixed(2) : '';
        });
    }

    /* ─────────── State changes ─────────── */
    function recomputeBreaks() {
        var t = state.target;
        var vals = DATA.segments.features.map(function (f) { return f.properties[t + '_final']; });
        state.breaks = quantileBreaks(vals, SCALE_COLORS.length);
    }
    function renderActiveTab() {
        if (state.tab === 'pipeline') return;
        if (state.tab === 'resultado') renderResultado();
        else if (state.tab === 'calibracao') renderCalibracao();
        else if (state.tab === 'modelo') renderModelo();
    }
    function setTarget(t) {
        state.target = t;
        document.querySelectorAll('.target-btn').forEach(function (b) { b.classList.toggle('active', b.dataset.target === t); });
        recomputeBreaks();
        renderHeader();
        renderMap();
        renderActiveTab();
    }
    function setTab(tab) {
        state.tab = tab;
        document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.toggle('active', b.dataset.tab === tab); });
        document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.toggle('active', p.id === 'panel-' + tab); });
        renderActiveTab();
    }

    /* ─────────── Filters + search ─────────── */
    function populateFilters() {
        var feats = DATA.segments.features.map(function (f) { return f.properties; });
        var regionais = Array.from(new Set(feats.map(function (p) { return p.regional; }).filter(Boolean))).sort();
        var classes = Array.from(new Set(feats.map(function (p) { return p.classe; }).filter(Boolean))).sort();
        var rsel = document.getElementById('filter-regional');
        rsel.innerHTML = '<option value="all">Todas</option>';
        regionais.forEach(function (r) { rsel.insertAdjacentHTML('beforeend', '<option value="' + r + '">' + r + '</option>'); });
        var csel = document.getElementById('filter-classe');
        csel.innerHTML = '<option value="all">Todas</option>';
        classes.forEach(function (c) { csel.insertAdjacentHTML('beforeend', '<option value="' + c + '">' + c + '</option>'); });
    }
    function applyFilters() {
        var min = parseFloat(document.getElementById('filter-min').value);
        var max = parseFloat(document.getElementById('filter-max').value);
        state.filters = {
            source: document.getElementById('filter-source').value,
            regional: document.getElementById('filter-regional').value,
            classe: document.getElementById('filter-classe').value,
            min: isNaN(min) ? null : min,
            max: isNaN(max) ? null : max
        };
        renderMap();
    }
    function doSearch(q) {
        var box = document.getElementById('search-results');
        q = (q || '').trim().toLowerCase();
        if (q.length < 2) { box.innerHTML = ''; return; }
        var t = state.target;
        var hits = DATA.segments.features.filter(function (f) {
            var p = f.properties;
            return (p.sre && p.sre.toLowerCase().indexOf(q) >= 0) ||
                (p.go && String(p.go).indexOf(q) >= 0) ||
                (p.regional && String(p.regional).toLowerCase().indexOf(q) >= 0);
        }).slice(0, 30);
        box.innerHTML = hits.map(function (f) {
            var p = f.properties;
            return '<div class="search-result-item" data-sre="' + p.sre + '"><div class="sre-name">' + p.sre + '</div>' +
                '<div class="sre-info">GO ' + (p.go || '-') + ' · Reg ' + (p.regional || '-') + ' · ' + TARGET_LABELS[t] + ' ' + fmt(p[t + '_final']) + '</div></div>';
        }).join('');
        box.querySelectorAll('.search-result-item').forEach(function (it) {
            it.addEventListener('click', function () { zoomToFeature(it.dataset.sre); });
        });
    }

    /* ─────────── Events ─────────── */
    function bindEvents() {
        document.querySelectorAll('.target-btn').forEach(function (b) {
            b.addEventListener('click', function () { setTarget(b.dataset.target); });
        });
        document.querySelectorAll('.tab-btn').forEach(function (b) {
            b.addEventListener('click', function () { setTab(b.dataset.tab); });
        });
        document.getElementById('btn-filter').addEventListener('click', applyFilters);
        var bRun = document.getElementById('btn-run-pipeline');
        if (bRun) bRun.addEventListener('click', runPipelineFromUI);
        var bRef = document.getElementById('btn-refresh-cands');
        if (bRef) bRef.addEventListener('click', function () {
            refreshCandidatesFromUI().catch(function (e) { showPipelineStatus('Erro: ' + e.message, true); });
        });
        var bUpload = document.getElementById('btn-upload-dataset');
        if (bUpload) bUpload.addEventListener('click', function () {
            uploadDatasetFromUI().catch(function (e) { showPipelineStatus('Erro: ' + e.message, true); });
        });
        var si = document.getElementById('search-input'), tmr;
        si.addEventListener('input', function () { clearTimeout(tmr); tmr = setTimeout(function () { doSearch(si.value); }, 250); });
        document.querySelectorAll('.copy-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var txt = document.getElementById(btn.dataset.copy).textContent;
                navigator.clipboard && navigator.clipboard.writeText(txt);
                btn.innerHTML = '<span class="material-icons-outlined" style="font-size:14px">check</span>';
                setTimeout(function () { btn.innerHTML = '<span class="material-icons-outlined" style="font-size:14px">content_copy</span>'; }, 1200);
            });
        });
    }

    async function loadDataFiles() {
        var base = 'data/';
        var names = ['segments.geojson', 'count_points.geojson', 'model_metrics.json', 'calibration_report.json'];
        var res = await Promise.all(names.map(function (n) { return fetch(base + n + '?t=' + Date.now()); }));
        for (var i = 0; i < res.length; i++) {
            if (!res[i].ok) throw new Error('Falha ao carregar ' + names[i] + ' (' + res[i].status + ')');
        }
        DATA.segments = await res[0].json();
        DATA.points = await res[1].json();
        DATA.metrics = await res[2].json();
        DATA.calibration = await res[3].json();
    }

    /* ─────────── Init ─────────── */
    async function init() {
        var loading = document.getElementById('loading');
        try {
            initMap();
            await loadDataFiles();
            await initPipelinePanel();

            populateFilters();
            bindEvents();
            recomputeBreaks();
            renderHeader();
            renderMap();
            renderResultado();

            loading.classList.add('hidden');
            setTimeout(function () {
                loading.style.display = 'none';
                map.invalidateSize();
                fitToData();
            }, 100);
        } catch (err) {
            loading.innerHTML = '<p style="color:#ef4444;padding:20px;max-width:600px;">Erro: ' + err.message + '</p>';
            console.error(err);
        }
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
