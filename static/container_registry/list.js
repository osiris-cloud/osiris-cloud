$registryTable = $('#registry-table');

const currentURL = parseURL();

function createTableEntry(registry) {
    let newRow = $('<tr/>', {
        class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600',
        click: function () {
            window.location.href = `/container-registry/${currentURL.nsid}/${registry.crid}`;
        }
    });
    newRow.append(
        $('<th/>', {
            scope: 'row',
            class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white',
            text: registry.name,
        })
    ).append(
        $('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50',
            text: registry.created_at,
        })
    ).append(
        $('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50',
            text: registry.url,
        })
    );
    return newRow;
}

$.ajax({
    url: `/api/container-registry/${currentURL.nsid}`,
    success: (data) => {
        if (data.registries.length === 0) {
            showNoResource();
            return;
        }
        data.forEach((registry) => {
            $registryTable.append(createTableEntry(registry));
        });
        $('registry-table-container').removeClass('hidden');
    },
    error: (resp) => {
        Alert(resp.responseJSON.message || "Internal Server Error");
    },
});