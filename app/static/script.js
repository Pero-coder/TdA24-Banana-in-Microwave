document.addEventListener('DOMContentLoaded', (e) => {
    const filterModal = document.getElementById('filterModal');
    const filterBtn = document.getElementById('filterBtn');
    const applyFilter = document.getElementById('applyFilter');

    filterBtn.addEventListener('click', () => {
        filterModal.showModal();
    });

    applyFilter.addEventListener('click', (e) => {
        e.preventDefault();
        $('#lecturers').html(
            `<div class="lecturer-card" 
                hx-get="/api/filter?${$('#filterModalForm').serialize()}"
                hx-trigger="revealed"
                hx-swap="afterend">
            </div>`
        );
        
        filterModal.close();

        // Re-trigger htmx processing
        htmx.process(document.body);
    });
});
