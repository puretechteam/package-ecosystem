function showDetailPanel(pkg) {
    const panel = document.getElementById('detail-panel');
    panel.classList.remove('collapsed');

    document.getElementById('detail-name').textContent = pkg.id;

    const versionEl = document.getElementById('detail-version');
    versionEl.textContent = pkg.version || '-';
    versionEl.className = 'badge badge-version';

    const registryEl = document.getElementById('detail-registry');
    registryEl.textContent = pkg.registry === 'npm' ? 'npm' : pkg.registry === 'pypi' ? 'PyPI' : 'crates.io';
    registryEl.className = 'badge badge-registry-' + pkg.registry;

    const categoryEl = document.getElementById('detail-category');
    categoryEl.textContent = pkg.category.charAt(0).toUpperCase() + pkg.category.slice(1);
    categoryEl.className = 'badge badge-category';

    const licenseEl = document.getElementById('detail-license');
    licenseEl.textContent = pkg.license || 'Unknown';
    licenseEl.className = 'badge badge-license';

    document.getElementById('detail-downloads').textContent = formatDownloads(pkg.downloads);
    document.getElementById('detail-dependents').textContent = pkg.dependents_count.toLocaleString();
    document.getElementById('detail-maintainers').textContent = pkg.maintainers ? pkg.maintainers.join(', ') : '-';
    document.getElementById('detail-description').textContent = pkg.description || 'No description available';

    const depsList = document.getElementById('detail-dependencies');
    depsList.innerHTML = '';
    if (pkg.dependencies && pkg.dependencies.length > 0) {
        pkg.dependencies.forEach((dep) => {
            const li = document.createElement('li');
            li.textContent = dep;
            depsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'None';
        depsList.appendChild(li);
    }
}

function hideDetailPanel() {
    const panel = document.getElementById('detail-panel');
    panel.classList.add('collapsed');
}

function formatDownloads(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('detail-close').addEventListener('click', () => {
        hideDetailPanel();
        if (typeof App !== 'undefined' && App.selectedNode) {
            App.selectedNode = null;
        }
    });
});