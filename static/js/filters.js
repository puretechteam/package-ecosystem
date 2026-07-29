function populateFilters() {
    const registrySelect = document.getElementById('registry-select');
    registrySelect.innerHTML = '<option value="all">All</option>';
    App.registries.forEach((reg) => {
        const option = document.createElement('option');
        option.value = reg;
        option.textContent = reg === 'npm' ? 'npm' : reg === 'pypi' ? 'PyPI' : 'crates.io';
        registrySelect.appendChild(option);
    });

    const categorySelect = document.getElementById('category-select');
    categorySelect.innerHTML = '<option value="all">All</option>';
    const categories = ['framework', 'library', 'tool', 'utility'];
    categories.forEach((cat) => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
        categorySelect.appendChild(option);
    });

    const timeSlider = document.getElementById('time-slider');
    timeSlider.addEventListener('input', () => {
        const labels = ['All', '1M+', '5M+', '10M+', '20M+', '50M+'];
        const idx = parseInt(timeSlider.value);
        document.getElementById('time-label').textContent = labels[idx] || 'All';
    });

    registrySelect.addEventListener('change', () => {
        handleRegistryChange(registrySelect.value);
    });

    categorySelect.addEventListener('change', () => {
        handleCategoryChange(categorySelect.value);
    });

    document.getElementById('search-input').addEventListener('input', () => {
        handleSearch(document.getElementById('search-input').value);
    });

    document.getElementById('reset-btn').addEventListener('click', resetFilters);

    document.getElementById('zoom-in').addEventListener('click', zoomIn);
    document.getElementById('zoom-out').addEventListener('click', zoomOut);
    document.getElementById('zoom-reset').addEventListener('click', zoomReset);
}