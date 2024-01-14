document.addEventListener('DOMContentLoaded', (e) => {
    const filterModal = document.getElementById('filterModal');
    const filterBtn = document.getElementById('filterBtn');
    const applyFilter = document.getElementById('applyFilter');

    filterBtn.addEventListener('click', () => {
        filterModal.showModal();
    });

    applyFilter.addEventListener('click', (e) => {
        e.preventDefault();
        filterModal.close();
    });
});
