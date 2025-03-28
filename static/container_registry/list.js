window.addEventListener('load', function () {
    const $registryTable = $('#registry-table');
    const $registryTableContainer = $('#registry-table-container');

    function createTableEntry(registry) {
        let $row = $('<tr/>', {
            class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600',
            click: function () {
                if (registry.state !== 'deleting')
                    window.location.href = `/container-registry/${currentURL.nsid}/${registry.crid}`;
            }
        });
        $row.append($('<th/>', {
            scope: 'row',
            class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white',
            text: registry.name,
        })).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50', text: (registry.public) ? 'Public' : 'Private',
        }))
            .append($('<td/>', {
                class: 'px-6 py-4 dark:text-gray-50', text: normalizeTime(registry.created_at, true),
            }))
            .append($('<td/>', {
                class: 'px-6 py-4 dark:text-gray-50', text: normalizeTime(registry.last_pushed_at, true),
            }))
            .append($('<td/>', {
                    class: 'px-6 py-4 dark:text-gray-50'
                }).append($('<code/>', {
                    text: registry.url
                }))
            );
        return $row;
    }

    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}`,
        method: 'GET',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            if (data.registries.length === 0) {
                showNoResource();
            } else {
                data.registries.forEach((registry) => {
                    $registryTable.append(createTableEntry(registry));
                });
                $registryTableContainer.removeClass('hidden');
            }
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });

});
