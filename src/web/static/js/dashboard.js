document.addEventListener("DOMContentLoaded", function() {
    // DOM Elements
    const sessionSelect = document.getElementById("select-session");
    const driverContainer = document.getElementById("driver-list-container");
    const infoBanner = document.getElementById("session-info-banner");
    const resolvedGPName = document.getElementById("resolved-gp-name");
    const resolvedSessionDetails = document.getElementById("resolved-session-details");

    // Charts containers
    const telemetryDiv = document.getElementById("chart-telemetry");
    const intervalsDiv = document.getElementById("chart-intervals");
    const pitstopsDiv = document.getElementById("chart-pitstops");

    // Colors mapping for drivers teams (Scuderia Ferrari inspired palette)
    const teamColors = {
        "Ferrari": "#e50914",
        "Mercedes": "#00a19c",
        "Red Bull Racing": "#0c1840",
        "Red Bull": "#0c1840",
        "McLaren": "#ff8700",
        "Aston Martin": "#229954",
        "Alpine": "#0090ff",
        "Williams": "#005aff",
        "RB": "#0000ff",
        "Sauber": "#52e252",
        "Haas F1 Team": "#ffffff",
        "Haas": "#ffffff"
    };

    let allSessions = [];
    let activeDrivers = [];

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
        if (!sessionKey) {
            infoBanner.style.display = "none";
            driverContainer.innerHTML = '<p class="placeholder-text">Selecione uma sessão primeiro.</p>';
            clearCharts();
            return;
        }

        // 1. Update session info banner
        const session = allSessions.find(s => s.session_key == sessionKey);
        if (session) {
            resolvedGPName.textContent = `GP do ${session.country_name} - ${session.circuit_short_name}`;
            resolvedSessionDetails.textContent = `Temporada ${session.year} | Sessão: ${session.session_name} (${session.session_type}) | Key: ${session.session_key}`;
            infoBanner.style.display = "flex";
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
        telemetryDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Selecione GP e Pilotos foco para visualizar telemetria...</div>';
        intervalsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Aguardando seleção de pilotos...</div>';
        pitstopsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Aguardando seleção de pilotos...</div>';
    }

    function updateCharts(sessionKey) {
        const checkedDrivers = getCheckedDrivers();
        if (checkedDrivers.length === 0) {
            clearCharts();
            return;
        }

        // Show loading in charts
        telemetryDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando telemetria analítica (offloading DuckDB)...</div>';
        intervalsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Calculando gaps de corrida...</div>';
        pitstopsDiv.innerHTML = '<div class="chart-loader"><i class="fa-solid fa-circle-notch fa-spin"></i> Filtrando registros de pit stop...</div>';

        // 1. Render Telemetry (Multiple Lines)
        const telemetryTraces = [];
        const telemetryPromises = checkedDrivers.map(drv => {
            return fetch(`/api/telemetry?session_key=${sessionKey}&driver_number=${drv.number}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length > 0) {
                        const xData = data.map((d, i) => i); // use sample indices to align starting timeline
                        const ySpeed = data.map(d => d.speed);
                        const color = teamColors[drv.team] || "#fed500"; // fallback Modena yellow

                        telemetryTraces.push({
                            x: xData,
                            y: ySpeed,
                            type: 'scatter',
                            mode: 'lines',
                            name: `${drv.acronym} (${drv.team})`,
                            line: { width: 2.5, color: color },
                            hoverinfo: 'name+y'
                        });
                    }
                });
        });

        Promise.all(telemetryPromises).then(() => {
            telemetryDiv.classList.remove("fade-in-chart");
            if (telemetryTraces.length === 0) {
                telemetryDiv.innerHTML = '<div class="placeholder-text">Nenhum registro de telemetria a 3.7Hz disponível para os pilotos selecionados nesta sessão.</div>';
            } else {
                telemetryDiv.innerHTML = ''; // Limpeza limpa prévia
                Plotly.newPlot(telemetryDiv, telemetryTraces, {
                    height: 320,
                    margin: { t: 30, b: 40, l: 50, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { title: 'Amostras de Telemetria (3.7Hz)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { title: 'Velocidade (km/h)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    template: 'plotly_dark',
                    legend: { orientation: 'h', y: -0.2 }
                }, { responsive: true });
                telemetryDiv.classList.add("fade-in-chart");
            }
        });

        // 2. Render Race Gaps / Intervals (Bar Chart of the latest record per driver)
        fetch(`/api/intervals?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(intervals => {
                const checkedAcronyms = checkedDrivers.map(d => d.acronym);
                // Filter intervals for checked drivers
                const filtered = intervals.filter(i => checkedAcronyms.includes(i.driver));

                if (filtered.length === 0) {
                    intervalsDiv.innerHTML = '<div class="placeholder-text">Sem dados de intervalos disponíveis para os pilotos selecionados.</div>';
                    return;
                }

                // Group by driver and find the latest gap record
                const latestGaps = {};
                filtered.forEach(item => {
                    latestGaps[item.driver] = item;
                });

                const plotDrivers = [];
                const plotGaps = [];
                const plotColors = [];

                checkedDrivers.forEach(drv => {
                    const item = latestGaps[drv.acronym];
                    if (item) {
                        plotDrivers.push(drv.acronym);
                        
                        // Parse gap string to number (clean up '+2.3s' or 'None' or 'LAP')
                        let gapVal = 0;
                        if (item.gap_to_leader) {
                            const clean = item.gap_to_leader.replace('+', '').replace('s', '').trim();
                            if (clean.toLowerCase() === 'leader') {
                                gapVal = 0;
                            } else if (clean.toLowerCase().includes('lap')) {
                                gapVal = 40; // visual representation of laps behind
                            } else {
                                gapVal = parseFloat(clean) || 0;
                            }
                        }
                        
                        plotGaps.push(gapVal);
                        plotColors.push(teamColors[drv.team] || "#fed500");
                    }
                });

                const gapTrace = {
                    x: plotDrivers,
                    y: plotGaps,
                    type: 'bar',
                    marker: { color: plotColors },
                    text: plotGaps.map(g => g === 0 ? "Líder" : (g === 40 ? "+ Laps" : `+${g.toFixed(3)}s`)),
                    textposition: 'auto'
                };

                intervalsDiv.classList.remove("fade-in-chart");
                intervalsDiv.innerHTML = ''; // Limpeza atômica prévia
                Plotly.newPlot(intervalsDiv, [gapTrace], {
                    height: 320,
                    margin: { t: 30, b: 40, l: 50, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { title: 'Piloto', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { title: 'Gap para o Líder (segundos)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    template: 'plotly_dark'
                }, { responsive: true });
                intervalsDiv.classList.add("fade-in-chart");
            })
            .catch(err => {
                console.error("Erro ao carregar intervalos:", err);
                intervalsDiv.innerHTML = '<div class="placeholder-text text-danger">Erro ao obter gaps.</div>';
            });

        // 3. Render Pit Stop Durations (Grouped Bar Chart by driver per lap)
        fetch(`/api/pit_stops?session_key=${sessionKey}`)
            .then(res => res.json())
            .then(pitstops => {
                const checkedAcronyms = checkedDrivers.map(d => d.acronym);
                const filtered = pitstops.filter(p => checkedAcronyms.includes(p.driver));

                if (filtered.length === 0) {
                    pitstopsDiv.innerHTML = '<div class="placeholder-text">Nenhum pit stop registrado para os pilotos selecionados.</div>';
                    return;
                }

                // Group pitstops by driver to create traces
                const driverTraces = {};
                checkedDrivers.forEach(drv => {
                    driverTraces[drv.acronym] = {
                        x: [],
                        y: [],
                        type: 'bar',
                        name: drv.acronym,
                        marker: { color: teamColors[drv.team] || "#fed500" }
                    };
                });

                filtered.forEach(pit => {
                    if (driverTraces[pit.driver]) {
                        driverTraces[pit.driver].x.push(`Volta ${pit.lap_number}`);
                        driverTraces[pit.driver].y.push(parseFloat(pit.stop_duration) || 0);
                    }
                });

                const traces = Object.values(driverTraces).filter(t => t.x.length > 0);

                if (traces.length === 0) {
                    pitstopsDiv.innerHTML = '<div class="placeholder-text">Sem paradas de boxes ativas.</div>';
                    return;
                }

                pitstopsDiv.classList.remove("fade-in-chart");
                pitstopsDiv.innerHTML = ''; // Limpeza atômica prévia
                Plotly.newPlot(pitstopsDiv, traces, {
                    height: 320,
                    margin: { t: 30, b: 40, l: 50, r: 15 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e0e6ed', family: 'Inter, sans-serif' },
                    xaxis: { title: 'Volta do Pit Stop', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    yaxis: { title: 'Duração da Parada (segundos)', gridcolor: 'rgba(255,255,255,0.03)', zeroline: false },
                    template: 'plotly_dark',
                    barmode: 'group'
                }, { responsive: true });
                pitstopsDiv.classList.add("fade-in-chart");
            })
            .catch(err => {
                console.error("Erro ao carregar pit stops:", err);
                pitstopsDiv.innerHTML = '<div class="placeholder-text text-danger">Erro ao obter dados de boxes.</div>';
            });
    }

    // Ouvinte dinâmico global para o redimensionamento fluido dos gráficos Plotly
    window.addEventListener("resize", function() {
        const activeCharts = [telemetryDiv, intervalsDiv, pitstopsDiv];
        activeCharts.forEach(div => {
            if (div.querySelector(".js-plotly-plot")) {
                Plotly.Plots.resize(div);
            }
        });
    });
});
