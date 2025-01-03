$secretsTable = $('#secrets-table');
$secretsTableContainer = $('#secrets-table-container');


function createTableEntry(secret) {
    let $row = $('<tr/>', {
        class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600',
        click: function () {
            window.location.href = `/secret-store/${currentURL.nsid}/${secret.secretid}`;
        }
    });
    $row.append($('<th/>', {
        scope: 'row',
        class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white',
        text: secret.name,
    })).append($('<td/>', {
        class: 'px-6 py-4 dark:text-gray-50', text: capitalize(secret.type),
    })).append($('<td/>', {
        class: 'px-6 py-4 dark:text-gray-50', text: normalizeTime(secret.created_at, true),
    })).append($('<td/>', {
        class: 'px-6 py-4 dark:text-gray-50',
        text: timeIsSimilar(secret.created_at, secret.updated_at) ? 'Never' : normalizeTime(secret.updated_at, true),
    }));
    return $row;
}

function loadSecrets() {
    $.ajax({
        url: `/api/secret-store/${currentURL.nsid}`,
        method: 'GET',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            if (data.secrets.length === 0) {
                showNoResource();
            } else {
                $secretsTable.empty();
                data.secrets.forEach((registry) => {
                    $secretsTable.append(createTableEntry(registry));
                });
                $secretsTableContainer.removeClass('hidden');
                showNoResource(false);
            }
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
}

window.onload = function () {
    loadSecrets();
    setInterval(loadSecrets, 30000);
}
