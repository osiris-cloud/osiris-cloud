$appTable = $('#app-table');
$appTableContainer = $('#app-table-container');


function createTableEntry(app) {
    let $row = $('<tr/>', {
        class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600',
        click: function () {
            window.location.href = `/container-apps/${currentURL.nsid}/${app.appid}`;
        }
    });
    $row.append($('<th/>', {
        scope: 'row',
        class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white',
        text: app.name,
    })).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50',
        }).append(
            createStateBadge(app.state))
    ).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50', text: normalizeTime(app.created_at, true),
        })
    ).append($('<td/>', {
        class: 'px-6 py-4 dark:text-gray-50 cursor-pointer', text: app.url +
            ((app.connection_port === 443) ? '' : ':' + app.port),
        click: function (e) {
            e.stopPropagation();
            window.open(`${app.url}:${app.connection_port}`, '_blank');
        }
    }));
    return $row;
}

$(document).ready(function () {
    showLoader(true);
    loadAppList();
    setInterval(() => {
        loadAppList();
    }, 5000);
});

function loadAppList() {
    $.ajax({
        url: `/api/container-apps/${currentURL.nsid}`,
        method: 'GET',
        data: {'brief': true},
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            showLoader(false);
            if (data.apps.length === 0) {
                showNoResource();
            } else {
                $appTable.empty();
                data.apps.forEach((registry) => {
                    $appTable.append(createTableEntry(registry));
                });
                $appTableContainer.removeClass('hidden');
            }
        },
        error: (resp) => {
            showLoader(false);
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
}
