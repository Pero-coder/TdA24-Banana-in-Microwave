document.addEventListener('DOMContentLoaded', (e) => {
    const filterModal = document.getElementById('filterModal');
    const filterBtn = document.getElementById('filterBtn');
    const applyFilter = document.getElementById('applyFilter');

    filterBtn.addEventListener('click', () => {
        filterModal.showModal();
    });

    $('#cost_min, #cost_max').on('input', function() {
        const min = parseInt($(this).attr('min'));
        const max = parseInt($(this).attr('max'));
        const value = parseInt($(this).val());

        if (value < min) {
            $(this).val(min);
        } else if (value > max) {
            $(this).val(max);
        }
    });

    applyFilter.addEventListener('click', (e) => {
        e.preventDefault();
        $('.lecturers').html(
            `<div 
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
