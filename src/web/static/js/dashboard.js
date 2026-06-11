document.addEventListener("DOMContentLoaded", function() {
    // DOM Elements
    const sessionSelect = document.getElementById("select-session");
    const driverContainer = document.getElementById("driver-list-container");
    const infoBanner = document.getElementById("session-info-banner");
    const resolvedGPName = document.getElementById("resolved-gp-name");
    const resolvedSessionDetails = document.getElementById("resolved-session-details");

    // Tabs elements
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // Charts containers
    const chartSpeedDiv = document.getElementById("chart-speed");
    const chartRpmDiv = document.getElementById("chart-rpm");
    const chartPedalsDiv = document.getElementById("chart-pedals");
    const chartStintsDiv = document.getElementById("chart-stints");
    const chartIntervalsDiv = document.getElementById("chart-intervals");
    const chartWeatherDiv = document.getElementById("chart-weather");
    const terminalLogDiv = document.getElementById("race-control-terminal");
    const pitstopsTableContainer = document.getElementById("pitstops-table-container");
    const chartDuelMapDiv = document.getElementById("chart-duel-map");

    // Colors mapping for drivers teams (Scuderia Ferrari inspired palette)
    const teamColors = {
        "Ferrari": "#e50914",
        "Mercedes": "#00a19c",
        "Red Bull Racing": "#1e41ff",
        "Red Bull": "#1e41ff",
        "McLaren": "#ff8700",
        "Aston Martin": "#006f62",
        "Alpine": "#0090ff",
        "Williams": "#005aff",
        "RB": "#0000ff",
        "Sauber": "#52e252",
        "Haas F1 Team": "#e60000",
        "Haas": "#e60000"
    };

    // Secondary lighter colors for the second driver of the same team (Grill-Me Outcome)
    const teamColorsSec = {
        "Ferrari": "#ff4d5a",
        "Mercedes": "#5efff8",
        "Red Bull Racing": "#708cff",
        "Red Bull": "#708cff",
        "McLaren": "#ffb861",
        "Aston Martin": "#4dffbe",
        "Alpine": "#7ad5ff",
        "Williams": "#6bb2ff",
        "RB": "#5285ff",
        "Sauber": "#a4ffa4",
        "Haas F1 Team": "#ff8080",
        "Haas": "#ff8080"
    };

    // Pirelli Tyre Compounds Colors Mapping
    const compoundColors = {
        "SOFT": "#e50914",
        "MEDIUM": "#fed500",
        "HARD": "#f8f9fa",
        "INTERMEDIATE": "#22c55e",
        "WET": "#3b82f6"
    };

    let allSessions = [];
    let activeDrivers = [];
    let activeSessionKey = null;

    // Helper to parse gap values to seconds floats (Grill-Me Outcome)
    function parseGapToLeader(gapStr) {
        if (!gapStr) return 0;
        const clean = gapStr.replace('+', '').replace('s', '').trim();
        if (clean.toLowerCase() === 'leader' || clean === '0.0' || clean === '0') {
            return 0;
        } else if (clean.toLowerCase().includes('lap')) {
            const laps = parseInt(clean) || 1;
            return laps * 40.0; // 40 seconds visual penalty representation per lap behind
        }
        return parseFloat(clean) || 0;
    }

    // Tabs Controller Logic
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.dataset.tab;

            // Toggle active state in navigation buttons
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Toggle active state in panes
            tabPanes.forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === targetTab) {
                    pane.classList.add("active");
                }
            });

            // Trigger window resize to adjust Plotly dimensions in the newly visible tab
            setTimeout(() => {
                window.dispatchEvent(new Event('resize'));
            }, 50);
        });
    });

    // Initialize: Fetch available sessions from API
    fetch("/api/sessions")
        .then(response => response.json())
        .then(sessions => {
            allSessions = sessions;
            sessionSelect.innerHTML = '<option value="">-- Selecione uma corrida --</option>';
            sessions.forEach(sess => {
                const opt = document.createElement("option");
                opt.value = sess.session_key;
                opt.textContent = `${sess.year} - GP do ${sess.country_name} (${sess.session_name})`;
                sessionSelect.appendChild(opt);
            });
        })
        .catch(err => {
            console.error("Erro ao carregar sessões:", err);
            sessionSelect.innerHTML = '<option value="">Erro ao carregar</option>';
        });

    // Handle Session Selection Change
    sessionSelect.addEventListener("change", function() {
        const sessionKey = sessionSelect.value;
        activeSessionKey = sessionKey;
        if (!sessionKey) {
            infoBanner.style.display = "none";
            document.getElementById("banner-winner").style.display = "none";
            driverContainer.innerHTML = '<p class="placeholder-text">Selecione uma sessão primeiro.</p>';
            clearCharts();
            return;
        }

        // 1. Update session info banner
        const session = allSessions.find(s => s.session_key == sessionKey);
        if (session) {
            resolvedGPName.textContent = `GP do ${session.country_name} - ${session.circuit_short_name}`;
            resolvedSessionDetails.textContent = `Temporada ${session.year} | Sessão: ${session.session_name} (${session.session_type}) | Chave: ${session.session_key}`;
            infoBanner.style.display = "flex";

            // 1.1 Fetch and display session winner (Grill-Me Outcome)
            fetch(`/api/winner?session_key=${sessionKey}`)
                .then(res => res.json())
                .then(winnerData => {
                    const winnerBanner = document.getElementById("banner-winner");
                    const winnerAcronym = document.getElementById("winner-name-acronym");
                    if (winnerData.length > 0) {
                        winnerAcronym.textContent = `${winnerData[0].driver} (${winnerData[0].team})`;
                        winnerBanner.style.display = "block";
                    } else {
                        winnerBanner.style.display = "none";
                    }
                })
                .catch(err => {
                    console.error("Erro ao buscar vencedor:", err);
                    document.getElementById("banner-winner").style.display = "none";
                });
        }

        // Show loading in drivers list
        driverContainer.innerHTML = '<p class="placeholder-text"><i class="fa-solid fa-circle-notch fa-spin"></i> Obtendo pilotos...</p>';
        clearCharts();

        // 2. Fetch active drivers for this session
        fetch(`/api/drivers?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(drivers => {
                activeDrivers = drivers;
                driverContainer.innerHTML = "";

                if (drivers.length === 0) {
                    driverContainer.innerHTML = '<p class="placeholder-text">Nenhum piloto ativo registrado.</p>';
                    return;
                }

                drivers.forEach(drv => {
                    const label = document.createElement("label");
                    label.className = "driver-item";
                    label.setAttribute("for", `drv-${drv.driver_number}`);

                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.id = `drv-${drv.driver_number}`;
                    checkbox.value = drv.driver_number;
                    checkbox.dataset.acronym = drv.name_acronym;
                    checkbox.dataset.team = drv.team_name;

                    // Bind change listener
                    checkbox.addEventListener("change", function() {
                        if (checkbox.checked) {
                            label.classList.add("active");
                        } else {
                            label.classList.remove("active");
                        }
                        updateCharts(sessionKey);
                    });

                    const infoBox = document.createElement("div");
                    infoBox.className = "driver-info-box";
                    infoBox.innerHTML = `<span class="driver-name">${drv.full_name} <span class="highlight-yellow">#${drv.driver_number}</span></span><span class="driver-team">${drv.team_name}</span>`;

                    label.appendChild(checkbox);
                    label.appendChild(infoBox);
                    driverContainer.appendChild(label);
                });

                // Load environmental data automatically since it's independent of the selected driver
                loadEnvironmentalData(sessionKey);
            })
            .catch(err => {
                console.error("Erro ao obter pilotos:", err);
                driverContainer.innerHTML = '<p class="placeholder-text text-danger">Erro ao carregar pilotos.</p>';
            });
    });

    function getCheckedDrivers() {
        const checked = [];
        driverContainer.querySelectorAll("input[type='checkbox']:checked").forEach(cb => {
            checked.push({
                number: parseInt(cb.value),
                acronym: cb.dataset.acronym,
                team: cb.dataset.team
            });
        });
        return checked;
    }

    function clearCharts() {
        document.getElementById("banner-winner").style.display = "none";
        chartSpeedDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Selecione GP e Pilotos...</div>';
        chartRpmDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Selecione GP e Pilotos...</div>';
        chartPedalsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Selecione GP e Pilotos...</div>';
        chartStintsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Aguardando seleção de GP e pilotos...</div>';
        chartIntervalsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Aguardando seleção...</div>';
        chartWeatherDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Selecione um GP primeiro...</div>';
        terminalLogDiv.innerHTML = '<p class="terminal-placeholder">Aguardando dados da sessão de GP...</p>';
        pitstopsTableContainer.innerHTML = '<p class="placeholder-text">Selecione GP e pilotos para analisar os pit stops.</p>';
        document.getElementById("duel-placeholder").style.display = "block";
        document.getElementById("duel-dashboard").style.display = "none";
        if (chartDuelMapDiv) {
            chartDuelMapDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando mapa de corner...</div>';
        }
    }

    function updateCharts(sessionKey) {
        const checkedDrivers = getCheckedDrivers();
        updateDuelDashboard(sessionKey, checkedDrivers);

        if (checkedDrivers.length === 0) {
            clearCharts();
            loadEnvironmentalData(sessionKey);
            return;
        }

        // Show loading in charts
        chartSpeedDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando velocidade...</div>';
        chartRpmDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando dados do motor...</div>';
        chartPedalsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando pedais e DRS...</div>';
        chartStintsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Calculando stints...</div>';
        chartIntervalsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Calculando gaps...</div>';
        pitstopsTableContainer.innerHTML = '<p class="placeholder-text"><i class="fa-solid fa-circle-notch fa-spin"></i> Buscando paradas no box...</p>';

        // Structures for multiple trace loading
        const speedTraces = [];
        const rpmTraces = [];
        const pedalsTraces = [];

        // Track how many drivers are selected per team to apply correct colors/styles
        const teamSelectionCount = {};

        const telemetryPromises = checkedDrivers.map(drv => {
            const team = drv.team;
            if (teamSelectionCount[team] === undefined) {
                teamSelectionCount[team] = 0;
            }
            const driverIndexInTeam = teamSelectionCount[team]++;

            // Dynamic Styling and Coloring Lighter/Darker (Grill-Me Outcome)
            let color = teamColors[team] || "#fed500";
            let lineDashStyle = "solid";

            if (driverIndexInTeam > 0) {
                color = teamColorsSec[team] || "#fed500";
                lineDashStyle = "dash"; // Dashed line for second driver of the same team
            }

            return fetch(`/api/telemetry?session_key=${sessionKey}&driver_number=${drv.number}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length > 0) {
                        const indices = data.map((_, i) => i);
                        const speeds = data.map(d => d.speed);
                        const rpms = data.map(d => d.rpm);
                        const gears = data.map(d => d.n_gear);
                        const throttles = data.map(d => d.throttle);
                        const brakes = data.map(d => d.brake);

                        // 1. Trace for Speed
                        speedTraces.push({
                            x: indices,
                            y: speeds,
                            type: 'scatter',
                            mode: 'lines',
                            name: `${drv.acronym} (#${drv.number})`,
                            line: { width: 2.5, color: color, dash: lineDashStyle },
                            hoverinfo: 'name+y'
                        });

                        // 2. Trace for RPM with gear info
                        rpmTraces.push({
                            x: indices,
                            y: rpms,
                            type: 'scatter',
                            mode: 'lines',
                            name: `${drv.acronym} (#${drv.number})`,
                            text: gears.map(g => g === 0 ? "N" : (g === -1 ? "R" : `M${g}`)),
                            hovertemplate: '%{name}<br>RPM: %{y}<br>Marcha: %{text}<extra></extra>',
                            line: { width: 2.2, color: color, dash: lineDashStyle }
                        });

                        // 3. Traces for Throttle and Brake
                        pedalsTraces.push({
                            x: indices,
                            y: throttles,
                            type: 'scatter',
                            mode: 'lines',
                            name: `${drv.acronym} - Acelerador`,
                            line: { width: 2, color: color, dash: lineDashStyle },
                            hovertemplate: '%{name}: %{y}%<extra></extra>'
                        });

                        pedalsTraces.push({
                            x: indices,
                            y: brakes.map(b => -b), // Plot brake as negative values for visual split layout
                            type: 'scatter',
                            mode: 'lines',
                            name: `${drv.acronym} - Freio`,
                            line: { width: 2, color: color === "#ffffff" ? "#cbd5e1" : color, dash: "dot" },
                            hovertemplate: '%{name}: %{y}%<extra></extra>'
                        });
                    }
                });
        });

        // 1. Process Telemetry charts when completed
        Promise.all(telemetryPromises).then(() => {
            // Speed Plot
            chartSpeedDiv.classList.remove("fade-in-chart");
            if (speedTraces.length === 0) {
                chartSpeedDiv.innerHTML = '<div class="placeholder-text">Sem dados de telemetria.</div>';
            } else {
                chartSpeedDiv.innerHTML = '';
                Plotly.newPlot(chartSpeedDiv, speedTraces, {
                    height: 280,
                    margin: { t: 20, b: 35, l: 45, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { title: 'Velocidade (km/h)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.2 }
                }, { responsive: true });
                chartSpeedDiv.classList.add("fade-in-chart");
            }

            // RPM Plot
            chartRpmDiv.classList.remove("fade-in-chart");
            if (rpmTraces.length === 0) {
                chartRpmDiv.innerHTML = '<div class="placeholder-text">Sem dados de motor.</div>';
            } else {
                chartRpmDiv.innerHTML = '';
                Plotly.newPlot(chartRpmDiv, rpmTraces, {
                    height: 280,
                    margin: { t: 20, b: 35, l: 45, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { title: 'Motor (RPM)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.2 }
                }, { responsive: true });
                chartRpmDiv.classList.add("fade-in-chart");
            }

            // Pedals Split Plot (Throttle vs Brake)
            chartPedalsDiv.classList.remove("fade-in-chart");
            if (pedalsTraces.length === 0) {
                chartPedalsDiv.innerHTML = '<div class="placeholder-text">Sem dados de controles.</div>';
            } else {
                chartPedalsDiv.innerHTML = '';
                Plotly.newPlot(chartPedalsDiv, pedalsTraces, {
                    height: 300,
                    margin: { t: 20, b: 35, l: 45, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { 
                        title: 'Acelerador (Tops) / Freio (Downs) %', 
                        gridcolor: 'rgba(255,255,255,0.03)', 
                        zeroline: true, 
                        zerolinecolor: 'rgba(255,255,255,0.1)' 
                    },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.2 }
                }, { responsive: true });
                chartPedalsDiv.classList.add("fade-in-chart");
            }
        });

        const checkedAcronyms = checkedDrivers.map(d => d.acronym);

        // 2. Load Stints Timeline (Horizontal Gantt Chart / Stacked bar)
        fetch(`/api/stints?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(stints => {
                const filtered = stints.filter(s => checkedAcronyms.includes(s.driver));
                chartStintsDiv.classList.remove("fade-in-chart");
                if (filtered.length === 0) {
                    chartStintsDiv.innerHTML = '<div class="placeholder-text">Sem registros de stints para os pilotos selecionados.</div>';
                    return;
                }

                // Process traces for Horizontal Stacked Bar representing stints Gantt
                const compoundGroups = {};
                filtered.forEach(st => {
                    const comp = st.compound.toUpperCase();
                    if (!compoundGroups[comp]) {
                        compoundGroups[comp] = {
                            x: [],
                            y: [],
                            base: [],
                            type: 'bar',
                            orientation: 'h',
                            name: comp,
                            marker: { color: compoundColors[comp] || "#6b7280" },
                            text: [],
                            hovertemplate: 'Piloto: %{y}<br>Voltas: %{base} a %{text}<br>Idade Pneu: %{customdata} voltas<extra></extra>'
                        };
                    }
                    
                    const lapsRun = st.lap_end - st.lap_start + 1;
                    compoundGroups[comp].x.push(lapsRun);
                    compoundGroups[comp].y.push(st.driver);
                    compoundGroups[comp].base.push(st.lap_start);
                    if (!compoundGroups[comp].customdata) {
                        compoundGroups[comp].customdata = [];
                    }
                    compoundGroups[comp].customdata.push(st.tyre_age_at_start);
                    compoundGroups[comp].text.push(st.lap_end);
                });

                chartStintsDiv.innerHTML = '';
                Plotly.newPlot(chartStintsDiv, Object.values(compoundGroups), {
                    height: 250,
                    margin: { t: 20, b: 35, l: 60, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { title: 'Volta da Corrida', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { gridcolor: 'rgba(255,255,255,0.03)', type: 'category' },
                    template: 'plotly_dark',
                    barmode: 'stack'
                }, { responsive: true });
                chartStintsDiv.classList.add("fade-in-chart");
            })
            .catch(err => {
                console.error("Erro ao carregar stints:", err);
                chartStintsDiv.innerHTML = '<div class="placeholder-text text-danger">Erro ao carregar stints.</div>';
            });

        // 3. Load Race Gaps / Intervals (Line chart of gaps over time to show leadership transitions - Grill-Me Outcome)
        fetch(`/api/intervals?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(intervals => {
                const filtered = intervals.filter(i => checkedAcronyms.includes(i.driver));
                chartIntervalsDiv.classList.remove("fade-in-chart");
                if (filtered.length === 0) {
                    chartIntervalsDiv.innerHTML = '<div class="placeholder-text">Sem dados de gaps.</div>';
                    return;
                }

                // Group by driver to draw lines over time
                const driverIntervals = {};
                checkedDrivers.forEach(drv => {
                    driverIntervals[drv.acronym] = {
                        x: [],
                        y: [],
                        type: 'scatter',
                        mode: 'lines',
                        name: `${drv.acronym} (${drv.team})`,
                        line: { width: 2.5 }
                    };
                });

                const teamSelectionCountIntervals = {};

                checkedDrivers.forEach(drv => {
                    const team = drv.team;
                    if (teamSelectionCountIntervals[team] === undefined) {
                        teamSelectionCountIntervals[team] = 0;
                    }
                    const driverIndexInTeam = teamSelectionCountIntervals[team]++;

                    let color = teamColors[team] || "#fed500";
                    let lineStyle = "solid";

                    if (driverIndexInTeam > 0) {
                        color = teamColorsSec[team] || "#fed500";
                        lineStyle = "dash";
                    }

                    const driverLogs = filtered.filter(i => i.driver === drv.acronym);
                    // Sample timestamps chronologically
                    driverLogs.forEach(log => {
                        driverIntervals[drv.acronym].x.push(new Date(log.date));
                        driverIntervals[drv.acronym].y.push(parseGapToLeader(log.gap_to_leader));
                    });

                    driverIntervals[drv.acronym].line.color = color;
                    driverIntervals[drv.acronym].line.dash = lineStyle;
                });

                const traces = Object.values(driverIntervals).filter(t => t.x.length > 0);

                chartIntervalsDiv.innerHTML = '';
                Plotly.newPlot(chartIntervalsDiv, traces, {
                    height: 280,
                    margin: { t: 20, b: 35, l: 45, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { title: 'Linha de Tempo da Prova', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { 
                        title: 'Diferença para o Líder (segundos)', 
                        gridcolor: 'rgba(255,255,255,0.03)', 
                        autorange: 'reversed', // Inverted so the leader (0) stays at the top of the chart
                        zeroline: true,
                        zerolinecolor: 'rgba(255,255,255,0.1)'
                    },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.2 }
                }, { responsive: true });
                chartIntervalsDiv.classList.add("fade-in-chart");
            })
            .catch(err => {
                console.error("Erro ao carregar intervalos:", err);
                chartIntervalsDiv.innerHTML = '<div class="placeholder-text text-danger">Erro ao obter gaps.</div>';
            });

        // 4. Load Pit Stops Table
        fetch(`/api/pit_stops?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(pitstops => {
                const filtered = pitstops.filter(p => checkedAcronyms.includes(p.driver));
                if (filtered.length === 0) {
                    pitstopsTableContainer.innerHTML = '<p class="placeholder-text">Nenhum pit stop registrado para os pilotos selecionados.</p>';
                    return;
                }

                // Sort by pit duration (fastest physical swap first)
                filtered.sort((a, b) => (parseFloat(a.pit_duration) || 99) - (parseFloat(b.pit_duration) || 99));

                let html = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Piloto</th>
                                <th>Escuderia</th>
                                <th>Volta</th>
                                <th>Duração Troca (Pirelli)</th>
                                <th>Tempo no Pitlane</th>
                                <th>Total Parada</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                filtered.forEach(p => {
                    html += `
                        <tr>
                            <td class="fw-bold highlight-yellow">${p.driver}</td>
                            <td>${p.team}</td>
                            <td class="text-mono">${p.lap_number}</td>
                            <td class="text-mono fw-bold text-danger">${p.pit_duration ? p.pit_duration + 's' : '-'}</td>
                            <td class="text-mono">${p.lane_duration ? p.lane_duration + 's' : '-'}</td>
                            <td class="text-mono">${p.stop_duration ? p.stop_duration + 's' : '-'}</td>
                        </tr>
                    `;
                });

                html += '</tbody></table>';
                pitstopsTableContainer.innerHTML = html;
            })
            .catch(err => {
                console.error("Erro ao carregar pit stops:", err);
                pitstopsTableContainer.innerHTML = '<p class="placeholder-text text-danger">Erro ao processar dados de boxes.</p>';
            });
    }

    function loadEnvironmentalData(sessionKey) {
        if (!sessionKey) return;

        // 1. Fetch Weather Data (temperatures air vs track)
        fetch(`/api/weather?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(weather => {
                chartWeatherDiv.classList.remove("fade-in-chart");
                if (weather.length === 0) {
                    chartWeatherDiv.innerHTML = '<div class="placeholder-text">Dados climáticos indisponíveis para este GP.</div>';
                    return;
                }

                const timestamps = weather.map(w => w.date);
                const airTemps = weather.map(w => w.air_temperature);
                const trackTemps = weather.map(w => w.track_temperature);

                chartWeatherDiv.innerHTML = '';
                Plotly.newPlot(chartWeatherDiv, [
                    {
                        x: timestamps,
                        y: airTemps,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Temp. Ar (°C)',
                        line: { color: '#fed500', width: 2 }
                    },
                    {
                        x: timestamps,
                        y: trackTemps,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Temp. Asfalto (°C)',
                        line: { color: '#e50914', width: 2.5 }
                    }
                ], {
                    height: 280,
                    margin: { t: 20, b: 35, l: 45, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { title: 'Temperatura (°C)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.2 }
                }, { responsive: true });
                chartWeatherDiv.classList.add("fade-in-chart");
            })
            .catch(err => {
                console.error("Erro ao carregar clima:", err);
                chartWeatherDiv.innerHTML = '<div class="placeholder-text text-danger">Erro ao carregar clima.</div>';
            });

        // 2. Fetch FIA Race Control Events
        fetch(`/api/race_control?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(messages => {
                if (messages.length === 0) {
                    terminalLogDiv.innerHTML = '<p class="terminal-placeholder">Nenhuma mensagem do controle de prova registrada para esta corrida.</p>';
                    return;
                }

                terminalLogDiv.innerHTML = "";
                messages.forEach(msg => {
                    const line = document.createElement("div");
                    line.className = "terminal-line";

                    // Determine CSS class based on flag colors
                    const flag = msg.flag ? msg.flag.toUpperCase() : "";
                    if (flag === "YELLOW" || flag === "DOUBLE YELLOW") {
                        line.classList.add("flag-line-yellow");
                    } else if (flag === "RED") {
                        line.classList.add("flag-line-red");
                    } else if (flag === "GREEN") {
                        line.classList.add("flag-line-green");
                    } else if (flag === "BLUE") {
                        line.classList.add("flag-line-blue");
                    }

                    // Format Time (extract hours:minutes:seconds)
                    let timeStr = "";
                    if (msg.date) {
                        const dateObj = new Date(msg.date);
                        timeStr = dateObj.toTimeString().split(' ')[0];
                    }

                    const driverTag = msg.driver ? `<span class="terminal-driver">[${msg.driver}]</span>` : "";
                    line.innerHTML = `<span class="terminal-time">${timeStr}</span>${driverTag}<span class="terminal-msg">${msg.message}</span>`;
                    terminalLogDiv.appendChild(line);
                });

                // Scroll to the latest messages at the bottom
                terminalLogDiv.scrollTop = terminalLogDiv.scrollHeight;
            })
            .catch(err => {
                console.error("Erro ao carregar mensagens FIA:", err);
                terminalLogDiv.innerHTML = '<p class="terminal-placeholder text-danger">Erro ao buscar feeds da FIA.</p>';
            });
    }

    // Ouvinte dinâmico global para o redimensionamento fluido de todos os novos gráficos Plotly
    window.addEventListener("resize", function() {
        const chartsToResize = [
            chartSpeedDiv,
            chartRpmDiv,
            chartPedalsDiv,
            chartStintsDiv,
            chartIntervalsDiv,
            chartWeatherDiv,
            chartDuelMapDiv
        ];
        
        chartsToResize.forEach(div => {
            if (div && div.querySelector(".js-plotly-plot")) {
                Plotly.Plots.resize(div);
            }
        });
    });

    function updateDuelDashboard(sessionKey, checkedDrivers) {
        const duelPlaceholder = document.getElementById("duel-placeholder");
        const duelDashboard = document.getElementById("duel-dashboard");

        if (!duelPlaceholder || !duelDashboard) return;

        if (checkedDrivers.length !== 2) {
            duelPlaceholder.style.display = "block";
            duelDashboard.style.display = "none";
            return;
        }

        duelPlaceholder.style.display = "none";
        duelDashboard.style.display = "grid";

        const drv1 = checkedDrivers[0];
        const drv2 = checkedDrivers[1];

        // 1. Atualizar informações de cards lado a lado
        document.getElementById("d1-name").textContent = drv1.acronym;
        document.getElementById("d1-team").textContent = drv1.team;
        document.getElementById("d1-number").textContent = `#${drv1.number}`;

        document.getElementById("d2-name").textContent = drv2.acronym;
        document.getElementById("d2-team").textContent = drv2.team;
        document.getElementById("d2-number").textContent = `#${drv2.number}`;

        // Aplicar cores da escuderia nos cards
        const color1 = teamColors[drv1.team] || "#fed500";
        const color2 = teamColors[drv2.team] || "#fed500";
        
        document.getElementById("duel-driver-1").style.borderLeft = `5px solid ${color1}`;
        document.getElementById("duel-driver-2").style.borderRight = `5px solid ${color2}`;

        // 2. Fetch métricas agregadas do duelo
        fetch(`/api/duel/metrics?session_key=${sessionKey}&driver_1=${drv1.number}&driver_2=${drv2.number}`)
            .then(res => res.json())
            .then(metrics => {
                const m1 = metrics[drv1.number.toString()] || {};
                const m2 = metrics[drv2.number.toString()] || {};

                // 2.1 Update text values
                document.getElementById("d1-speed").textContent = `${m1.max_speed || 0} km/h`;
                document.getElementById("d2-speed").textContent = `${m2.max_speed || 0} km/h`;
                document.getElementById("d1-rpm").textContent = `${m1.max_rpm || 0} RPM`;
                document.getElementById("d2-rpm").textContent = `${m2.max_rpm || 0} RPM`;
                document.getElementById("d1-throttle").textContent = `${m1.full_throttle_pct || 0}%`;
                document.getElementById("d2-throttle").textContent = `${m2.full_throttle_pct || 0}%`;
                document.getElementById("d1-brake").textContent = `${m1.heavy_brake_pct || 0}%`;
                document.getElementById("d2-brake").textContent = `${m2.heavy_brake_pct || 0}%`;
                document.getElementById("d1-drs").textContent = `${m1.drs_pct || 0}%`;
                document.getElementById("d2-drs").textContent = `${m2.drs_pct || 0}%`;
                document.getElementById("d1-pit").textContent = m1.best_pit && m1.best_pit !== "-" ? `${m1.best_pit}s` : "-";
                document.getElementById("d2-pit").textContent = m2.best_pit && m2.best_pit !== "-" ? `${m2.best_pit}s` : "-";

                // 2.2 Update visual balance bars (50/50 comparison)
                updateMetricBar("speed", m1.max_speed, m2.max_speed);
                updateMetricBar("rpm", m1.max_rpm, m2.max_rpm);
                updateMetricBar("throttle", m1.full_throttle_pct, m2.full_throttle_pct);
                updateMetricBar("brake", m1.heavy_brake_pct, m2.heavy_brake_pct);
                updateMetricBar("drs", m1.drs_pct, m2.drs_pct);
            })
            .catch(err => {
                console.error("Erro ao carregar métricas de duelo:", err);
            });

        // 3. Fetch location data and plot interactive 2D Corner Map
        if (chartDuelMapDiv) {
            chartDuelMapDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando mapa de corner...</div>';
            
            Promise.all([
                fetch(`/api/duel/location?session_key=${sessionKey}&driver_number=${drv1.number}`).then(res => res.json()),
                fetch(`/api/duel/location?session_key=${sessionKey}&driver_number=${drv2.number}`).then(res => res.json())
            ]).then(([loc1, loc2]) => {
                chartDuelMapDiv.innerHTML = '';

                const traces = [];

                // Adicionar trajetória do Piloto 1 (linha cheia)
                if (loc1.length > 0) {
                    const xs = loc1.map(pt => pt.x);
                    const ys = loc1.map(pt => pt.y);
                    const speeds = loc1.map(pt => pt.speed);
                    const gears = loc1.map(pt => pt.gear);

                    traces.push({
                        x: xs,
                        y: ys,
                        mode: 'lines',
                        name: `${drv1.acronym} - Trajetória`,
                        line: {
                            width: 5,
                            color: color1,
                            shape: 'spline'
                        },
                        text: gears.map((g, idx) => `Velocidade: ${speeds[idx]} km/h<br>Marcha: M${g || 0}`),
                        hovertemplate: '%{name}<br>%{text}<extra></extra>'
                    });
                }

                // Adicionar trajetória do Piloto 2 (linha pontilhada)
                if (loc2.length > 0) {
                    const xs = loc2.map(pt => pt.x);
                    const ys = loc2.map(pt => pt.y);
                    const speeds = loc2.map(pt => pt.speed);
                    const gears = loc2.map(pt => pt.gear);

                    traces.push({
                        x: xs,
                        y: ys,
                        mode: 'lines',
                        name: `${drv2.acronym} - Trajetória`,
                        line: {
                            width: 3.5,
                            color: color2,
                            dash: 'dot',
                            shape: 'spline'
                        },
                        text: gears.map((g, idx) => `Velocidade: ${speeds[idx]} km/h<br>Marcha: M${g || 0}`),
                        hovertemplate: '%{name}<br>%{text}<extra></extra>'
                    });
                }

                if (traces.length === 0) {
                    chartDuelMapDiv.innerHTML = '<div class="placeholder-text">Sem dados de localização nesta sessão.</div>';
                    return;
                }

                Plotly.newPlot(chartDuelMapDiv, traces, {
                    height: 400,
                    margin: { t: 10, b: 10, l: 10, r: 10 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { 
                        showgrid: false, 
                        zeroline: false, 
                        showticklabels: false, 
                        scaleratio: 1, 
                        scaleanchor: 'y'
                    },
                    yaxis: { 
                        showgrid: false, 
                        zeroline: false, 
                        showticklabels: false
                    },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.05 }
                }, { responsive: true });
            }).catch(err => {
                console.error("Erro ao carregar trajetórias:", err);
                chartDuelMapDiv.innerHTML = '<div class="placeholder-text text-danger">Erro ao obter localização.</div>';
            });
        }
    }

    function updateMetricBar(metricName, val1, val2) {
        const d1Bar = document.getElementById(`d1-${metricName}-bar`);
        const d2Bar = document.getElementById(`d2-${metricName}-bar`);
        
        if (!d1Bar || !d2Bar) return;

        const v1 = parseFloat(val1) || 0;
        const v2 = parseFloat(val2) || 0;

        if (v1 === 0 && v2 === 0) {
            d1Bar.style.width = "50%";
            d2Bar.style.width = "50%";
            return;
        }

        const total = v1 + v2;
        const pct1 = (v1 / total) * 100;
        const pct2 = (v2 / total) * 100;

        d1Bar.style.width = `${pct1}%`;
        d2Bar.style.width = `${pct2}%`;
    }
});
