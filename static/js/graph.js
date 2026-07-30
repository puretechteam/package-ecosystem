const App = {
    data: null,
    registries: [],
    categories: new Set(),
    simulation: null,
    svg: null,
    g: null,
    zoom: null,
    nodes: [],
    links: [],
    selectedNode: null,
    currentRegistry: "all",
    currentCategory: "all",
    currentSearch: "",
    currentMinDownloads: 0,
    colorScale: null,
    sizeScale: null,
    dataSource: "bundled",
    isStale: false,
};

const categoryColors = {
    framework: "#e94560",
    library: "#0f3460",
    tool: "#16c79a",
    utility: "#f0a500",
    external: "#888",
};

const registryColors = {
    npm: "#e94560",
    pypi: "#16c79a",
    crates: "#f0a500",
};

function initGraph() {
    const container = document.getElementById("graph-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    App.svg = d3.select("#graph-svg");
    App.svg.attr("width", width).attr("height", height);

    App.zoom = d3.zoom()
        .scaleExtent([0.1, 8])
        .on("zoom", (event) => {
            App.g.attr("transform", event.transform);
        });

    App.svg.call(App.zoom);

    App.g = App.svg.append("g");

    App.g.append("g").attr("class", "links-group");
    App.g.append("g").attr("class", "nodes-group");
    App.g.append("g").attr("class", "labels-group");

    App.colorScale = d3.scaleOrdinal()
        .domain(Object.keys(categoryColors))
        .range(Object.values(categoryColors));

    fetchData();
}

async function fetchData() {
    const staleIndicator = document.getElementById("stale-indicator");
    const errorBanner = document.getElementById("error-banner");

    try {
        const [dataRes, registriesRes] = await Promise.all([
            fetch("/api/data"),
            fetch("/api/registries"),
        ]);

        if (!dataRes.ok || !registriesRes.ok) {
            throw new Error("API request failed");
        }

        App.data = await dataRes.json();
        App.registries = await registriesRes.json();
        App.dataSource = "live";
        App.isStale = false;
        if (staleIndicator) staleIndicator.classList.remove("visible");
        if (errorBanner) errorBanner.classList.remove("visible");
    } catch (err) {
        console.warn("Live data fetch failed, falling back to bundled data:", err);
        try {
            const fallbackRes = await fetch("/data/packages.json");
            if (fallbackRes.ok) {
                const bundledData = await fallbackRes.json();
                App.data = bundledData;
                App.dataSource = "bundled";
                App.isStale = true;
                if (staleIndicator) staleIndicator.classList.add("visible");
                if (errorBanner) errorBanner.classList.remove("visible");
            } else {
                throw new Error("Fallback also failed");
            }
        } catch (fallbackErr) {
            console.error("All data sources failed:", fallbackErr);
            App.data = {};
            App.registries = [];
            App.dataSource = "none";
            App.isStale = true;
            if (staleIndicator) staleIndicator.classList.add("visible");
            if (errorBanner) {
                errorBanner.textContent = "Unable to load data. Showing cached or empty state.";
                errorBanner.classList.add("visible");
            }
        }
    }

    populateFilters();
    buildGraph();
    updateStats();
}

function buildGraph() {
    hideEmptyState();

    if (!App.data || Object.keys(App.data).length === 0) {
        showEmptyState("No data available. Unable to load package information.");
        clearGraph();
        return;
    }

    const allPackages = [];
    const registryKeys = App.currentRegistry === "all"
        ? Object.keys(App.data)
        : [App.currentRegistry];

    registryKeys.forEach((reg) => {
        if (App.data[reg]) {
            App.data[reg].forEach((pkg) => {
                allPackages.push(pkg);
            });
        }
    });

    const filteredPackages = allPackages.filter((pkg) => {
        if (App.currentCategory !== "all" && pkg.category !== App.currentCategory) {
            return false;
        }
        if (App.currentSearch && !pkg.name.toLowerCase().includes(App.currentSearch.toLowerCase())) {
            return false;
        }
        if (App.currentMinDownloads > 0 && pkg.downloads < App.currentMinDownloads) {
            return false;
        }
        return true;
    });

    if (filteredPackages.length === 0) {
        showEmptyState("No packages match the current filters.");
        clearGraph();
        return;
    }

    const packageNames = new Set(filteredPackages.map((p) => p.name));

    App.nodes = filteredPackages.map((pkg) => ({
        id: pkg.name,
        version: pkg.version,
        registry: pkg.registry,
        category: pkg.category,
        downloads: pkg.downloads,
        description: pkg.description,
        license: pkg.license,
        dependents_count: pkg.dependents_count,
        maintainers: pkg.maintainers,
        dependencies: pkg.dependencies,
    }));

    App.links = [];
    const allPackageNames = new Set(
        filteredPackages.map((p) => p.name)
    );
    const placeholderNodes = [];
    filteredPackages.forEach((pkg) => {
        pkg.dependencies.forEach((dep) => {
            if (allPackageNames.has(dep)) {
                App.links.push({ source: pkg.name, target: dep });
            } else {
                if (!placeholderNodes.find((n) => n.id === dep)) {
                    placeholderNodes.push({
                        id: dep,
                        version: "external",
                        registry: "external",
                        category: "external",
                        downloads: 0,
                        description: "External dependency (not in bundled data)",
                        license: "",
                        dependents_count: 0,
                        maintainers: [],
                        dependencies: [],
                        external: true,
                    });
                }
                App.links.push({ source: pkg.name, target: dep });
            }
        });
    });
    App.nodes = App.nodes.concat(placeholderNodes);

    App.categories = new Set(filteredPackages.map((p) => p.category));

    updateStatusBar();
    updateStats();
    renderGraph();
    updateLegend();
}

function clearGraph() {
    const linksGroup = App.g.select(".links-group");
    const nodesGroup = App.g.select(".nodes-group");
    const labelsGroup = App.g.select(".labels-group");

    linksGroup.selectAll("*").remove();
    nodesGroup.selectAll("*").remove();
    labelsGroup.selectAll("*").remove();

    App.nodes = [];
    App.links = [];

    const emptyState = document.getElementById("graph-empty-state");
    if (emptyState) emptyState.classList.add("visible");

    updateStatusBar();
}

function showEmptyState(message) {
    const emptyState = document.getElementById("graph-empty-state");
    if (emptyState) {
        const msgEl = emptyState.querySelector(".graph-empty-state-text");
        if (msgEl) {
            msgEl.textContent = message || "No packages to display";
        }
        emptyState.classList.add("visible");
    }
}

function hideEmptyState() {
    const emptyState = document.getElementById("graph-empty-state");
    if (emptyState) {
        emptyState.classList.remove("visible");
    }
}

function renderGraph() {
    const container = document.getElementById("graph-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    hideEmptyState();

    if (App.nodes.length === 0) {
        clearGraph();
        return;
    }

    const maxDownloads = d3.max(App.nodes, (d) => d.downloads) || 1;
    App.sizeScale = d3.scaleSqrt()
        .domain([0, maxDownloads])
        .range([6, 30]);

    const linksGroup = App.g.select(".links-group");
    const nodesGroup = App.g.select(".nodes-group");
    const labelsGroup = App.g.select(".labels-group");

    linksGroup.selectAll("*").remove();
    nodesGroup.selectAll("*").remove();
    labelsGroup.selectAll("*").remove();

    if (App.simulation) {
        App.simulation.stop();
    }

    const link = linksGroup.selectAll("line")
        .data(App.links)
        .enter().append("line")
        .attr("class", "link")
        .attr("stroke-width", 1);

    const node = nodesGroup.selectAll("circle")
        .data(App.nodes)
        .enter().append("circle")
        .attr("class", "node-circle")
        .attr("r", (d) => App.sizeScale(d.downloads))
        .attr("fill", (d) => categoryColors[d.category] || "#666")
        .attr("stroke", (d) => {
            if (d.external) return "#555";
            const c = d3.color(categoryColors[d.category] || "#666");
            return c ? c.brighter(0.5).toString() : "#fff";
        })
        .attr("stroke-dasharray", (d) => d.external ? "3,3" : "none")
        .attr("stroke-width", (d) => d.external ? 2 : 1)
        .on("click", (event, d) => {
            event.stopPropagation();
            selectNode(d);
        })
        .on("mouseover", (event, d) => showTooltip(event, d))
        .on("mouseout", hideTooltip);

    const registryBadge = nodesGroup.selectAll("circle.registry-badge")
        .data(App.nodes)
        .enter().append("circle")
        .attr("class", "registry-badge")
        .attr("r", 4)
        .attr("fill", (d) => registryColors[d.registry] || "#666")
        .attr("stroke", (d) => {
            const c = d3.color(registryColors[d.registry] || "#666");
            return c ? c.brighter(0.3).toString() : "#fff";
        })
        .attr("stroke-width", 1);

    const label = labelsGroup.selectAll("text")
        .data(App.nodes)
        .enter().append("text")
        .attr("class", "node-label")
        .attr("dy", (d) => App.sizeScale(d.downloads) + 14)
        .attr("font-size", "10px")
        .attr("font-weight", "500")
        .attr("fill", "#e0e0e0")
        .attr("text-anchor", "middle")
        .attr("pointer-events", "none")
        .text((d) => d.id);

    App.simulation = d3.forceSimulation(App.nodes)
        .force("link", d3.forceLink(App.links).id((d) => d.id).distance(80))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius((d) => App.sizeScale(d.downloads) + 16))
        .on("tick", () => {
            link
                .attr("x1", (d) => d.source.x)
                .attr("y1", (d) => d.source.y)
                .attr("x2", (d) => d.target.x)
                .attr("y2", (d) => d.target.y);

            node
                .attr("cx", (d) => d.x)
                .attr("cy", (d) => d.y);

            registryBadge
                .attr("cx", (d) => d.x + App.sizeScale(d.downloads) + 5)
                .attr("cy", (d) => d.y + App.sizeScale(d.downloads) + 5);

            label
                .attr("x", (d) => d.x)
                .attr("y", (d) => d.y);
        });

    App.svg.on("click", () => deselectNode());
}

function selectNode(d) {
    App.selectedNode = d;
    showDetailPanel(d);

    App.g.selectAll(".node-circle")
        .classed("selected", (n) => n.id === d.id);

    App.g.selectAll(".registry-badge")
        .classed("dimmed", (n) => n.id !== d.id);

    App.g.selectAll(".link")
        .classed("highlighted", (l) => l.source.id === d.id || l.target.id === d.id);

    App.g.selectAll(".node-circle")
        .classed("dimmed", (n) => {
            if (n.id === d.id) return false;
            const isConnected = App.links.some(
                (l) => (l.source.id === d.id && l.target.id === n.id) ||
                       (l.target.id === d.id && l.source.id === n.id)
            );
            return !isConnected;
        });

    App.g.selectAll(".node-label")
        .classed("dimmed", (n) => {
            if (n.id === d.id) return false;
            const isConnected = App.links.some(
                (l) => (l.source.id === d.id && l.target.id === n.id) ||
                       (l.target.id === d.id && l.source.id === n.id)
            );
            return !isConnected;
        });
}

function deselectNode() {
    App.selectedNode = null;
    hideDetailPanel();

    App.g.selectAll(".node-circle")
        .classed("selected", false)
        .classed("dimmed", false);

    App.g.selectAll(".registry-badge")
        .classed("dimmed", false);

    App.g.selectAll(".link")
        .classed("highlighted", false);

    App.g.selectAll(".node-label")
        .classed("dimmed", false);
}

function showTooltip(event, d) {
    let tooltip = document.getElementById("tooltip");
    if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.id = "tooltip";
        tooltip.className = "node-tooltip";
        document.body.appendChild(tooltip);
    }
    const externalLabel = d.external ? " (external)" : "";
    tooltip.innerHTML = `<strong>${d.id}</strong>${externalLabel}<br>${d.category} &middot; ${formatDownloads(d.downloads)}`;
    tooltip.style.left = (event.pageX + 12) + "px";
    tooltip.style.top = (event.pageY - 10) + "px";
    tooltip.style.display = "block";
}

function hideTooltip() {
    const tooltip = document.getElementById("tooltip");
    if (tooltip) {
        tooltip.style.display = "none";
    }
}

function updateStatusBar() {
    document.getElementById("node-count").textContent = `${App.nodes.length} nodes`;
    document.getElementById("edge-count").textContent = `${App.links.length} edges`;
    document.getElementById("registry-count").textContent = `${App.registries.length} registries`;
}

function updateStats() {
    const statNodes = document.getElementById("stat-nodes");
    const statEdges = document.getElementById("stat-edges");
    const statRegistries = document.getElementById("stat-registries");
    const statPackages = document.getElementById("stat-packages");

    if (statNodes) statNodes.textContent = App.nodes.length;
    if (statEdges) statEdges.textContent = App.links.length;
    if (statRegistries) statRegistries.textContent = App.registries.length;
    if (statPackages && App.data) {
        const total = Object.values(App.data).reduce((sum, pkgs) => sum + pkgs.length, 0);
        statPackages.textContent = total;
    }
}

function formatDownloads(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
}

function handleRegistryChange(registry) {
    App.currentRegistry = registry;
    buildGraph();
    updateStats();
}

function handleCategoryChange(category) {
    App.currentCategory = category;
    buildGraph();
}

function handleSearch(query) {
    App.currentSearch = query;
    buildGraph();
}

function handleTimeSlider(value) {
    const thresholds = [0, 1000000, 5000000, 10000000, 20000000, 50000000];
    const idx = parseInt(value);
    App.currentMinDownloads = thresholds[idx] || 0;
    buildGraph();
}

function resetFilters() {
    App.currentRegistry = "all";
    App.currentCategory = "all";
    App.currentSearch = "";
    App.currentMinDownloads = 0;

    document.getElementById("registry-select").value = "all";
    document.getElementById("category-select").value = "all";
    document.getElementById("search-input").value = "";
    document.getElementById("time-slider").value = 0;
    document.getElementById("time-label").textContent = "All";

    buildGraph();
}

function updateLegend() {
    const legendPanel = document.getElementById("legend-panel");
    if (!legendPanel) return;

    const categories = ["framework", "library", "tool", "utility"];
    const categoryLabels = { framework: "Framework", library: "Library", tool: "Tool", utility: "Utility" };
    const registries = App.registries.length > 0 ? App.registries : ["npm", "pypi", "crates"];
    const registryLabels = { npm: "npm", pypi: "PyPI", crates: "crates.io" };

    let html = '<h3>Legend</h3>';

    html += '<div class="legend-section"><div class="legend-section-title">Categories</div>';
    categories.forEach((cat) => {
        const color = categoryColors[cat] || "#666";
        html += `<div class="legend-item"><span class="legend-dot" style="background:${color}"></span>${categoryLabels[cat] || cat}</div>`;
    });
    html += '</div>';

    html += '<div class="legend-section"><div class="legend-section-title">Registries</div>';
    registries.forEach((reg) => {
        const color = registryColors[reg] || "#666";
        html += `<div class="legend-item"><span class="legend-dot registry-dot" style="background:${color}"></span>${registryLabels[reg] || reg}</div>`;
    });
    html += '</div>';

    legendPanel.innerHTML = html;
}

function zoomIn() {
    App.svg.transition().duration(300).call(App.zoom.scaleBy, 1.5);
}

function zoomOut() {
    App.svg.transition().duration(300).call(App.zoom.scaleBy, 0.67);
}

function zoomReset() {
    App.svg.transition().duration(300).call(App.zoom.transform, d3.zoomIdentity);
}

window.addEventListener("resize", () => {
    const container = document.getElementById("graph-container");
    const width = container.clientWidth;
    const height = container.clientHeight;
    App.svg.attr("width", width).attr("height", height);
    if (App.simulation) {
        App.simulation.force("center", d3.forceCenter(width / 2, height / 2));
        App.simulation.alpha(0.3).restart();
    }
});

document.addEventListener("DOMContentLoaded", initGraph);