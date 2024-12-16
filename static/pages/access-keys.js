let accessModal;
let $accessKeyModal = $('#access-key-modal');
let $keyName = $('#access-key-name');
let $keyScopes = $('#key-scopes');
let $keyWrite = $('#access-key-write');
let $keyExpiration = $('#key-expiration');
let $keySubmitButton = $('#access-key-submit')

let $keysTable = $('#keys-table');
let $keysTableBody = $keysTable.find('tbody');
window.addEventListener('load', function () {
    accessModal = FlowbiteInstances.getInstance('Modal', 'access-key-modal');
    accessModal._options.onShow = function () {
        setTimeout(() => {
            $accessKeyModal.addClass('show');
        }, 10);
        $keyName.val('');
        $keyScopes.val('');
        $keyWrite.prop('checked', false);
        $keySubmitButton.prop('disabled', false);
        $keySubmitButton.text('Generate key');
    };
    accessModal._options.onHide = function () {
        $accessKeyModal.removeClass('show');
    }
    showLoader();
    loadAccessKeys();
    loadAccessScopes();
});

$keySubmitButton.click(() => {
    if ($keyName.val().length === 0) {
        Alert('Key name cannot be empty');
        return;
    }
    if ($keyScopes.val().length === 0) {
        Alert('Scope cannot be empty');
        return;
    }
    let keyExpiration = null
    if ($keyExpiration.val() !== 'null') {
        const currentDate = new Date();
        currentDate.setDate(currentDate.getDate() + Number($keyExpiration.val()));
        keyExpiration = currentDate.toISOString();
    }

    $(this).prop('disabled', true);
    $(this).text('Creating Key...');

    $.ajax({
        url: `/api/access-key`,
        method: 'PUT',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            name: $keyName.val(),
            scopes: $keyScopes.val(),
            can_write: $keyWrite.is(':checked'),
            expiration: keyExpiration
        }),
        success: (resp) => {
            accessModal.hide();

            let msg = 'Here is your key. For security reasons, this will not be shown again';
            msg += tooltipHTML;
            msg += `<code id="key-token"
                          class="mt-2 block text-sm font-mono bg-gray-100 dark:bg-gray-800 p-1 rounded w-80 mx-auto">
                      ${resp.key}
                    </code>`;

            Alert(msg, () => {
                loadAccessKeys();
            }, {'icon': 'check'});

            $('#key-token').unbind('click').click(() => {
                copyToClip(resp.key);
                $('#key-tooltip').removeClass('invisible');
                setTimeout(() => {
                    $('#key-tooltip').addClass('invisible');
                });
            });
            new Tooltip(document.getElementById("key-tooltip"), document.getElementById("key-token"));
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
});

function createKeyTableEntry(data) {
    let $row = $('<tr/>', {
        class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600'
    });
    $row.append($('<th/>', {
        scope: 'row', class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white', text: data.name
    }));
    $row.append($('<td/>', {
        class: 'px-6 py-4', text: normalizeTime(data.created_at)
    }));
    $row.append($('<td/>', {
        class: 'px-6 py-4', text: normalizeTime(data.expiration)
    }));
    $row.append($('<td/>', {
        class: 'px-6 py-4', text: normalizeTime(data.last_used)
    }));

    let scopes = data.scopes.map(scope => scope.replace('-', ' ').split(' ').map(word => capitalize(word)).join(' '));
    let $scopes = scopes.map(scope => $('<div/>', {text: scope}));

    $row.append($('<td/>', {
        class: 'px-6 py-4',
    }).append($scopes));
    $row.append($('<td/>', {
        class: 'px-6 py-4', text: "Read" + (data.can_write ? ', Write' : '')
    }));
    let $deleteCell = $('<td/>', {
        class: 'px-6 py-4'
    });
    let $deleteButton = $('<button/>', {
        class: 'font-medium text-red-600 dark:text-red-500 dark:hover:text-red-600', text: 'Delete', click: () => {
            deleteKey(data.keyid, data.name);
        }
    });
    $deleteCell.append($deleteButton);
    $row.append($deleteCell);
    return $row;
}

function deleteKey(keyid, keyname) {
    Confirm(`Are you sure you want to delete the key "${keyname}" ?`, (confirm) => {
        if (!confirm) return;

        $.ajax({
            url: '/api/access-key/' + keyid,
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            type: 'DELETE',
            success: () => {
                Alert('Key Deleted', () => {
                    loadAccessKeys();
                });
            },
            error: (resp) => {
                Alert(resp.responseJSON.message || "Internal Server Error");
            }
        });
    });
}

function loadAccessKeys() {
    $keysTableBody.empty();
    $.ajax({
        url: '/api/access-key', type: 'GET', success: function (data) {
            if (data.keys.length === 0) {
                $keysTable.addClass('hidden');
                showNoResource();
            } else {
                showNoResource(false);
                $keysTable.removeClass('hidden');
                data.keys.forEach(function (key) {
                    $keysTableBody.append(createKeyTableEntry(key));
                });
            }
            showLoader(false);
        }, error: function (resp) {
            Alert(resp.responseJSON.message || "Internal Server Error");
        }
    });
}

function loadAccessScopes() {
    $.ajax({
        url: '/api/access-key-scopes',
        type: 'GET',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: function (data) {
            data.scopes.forEach((scope) => {
                let scopeReadable = scope.replace('-', ' ').split(' ').map(word => capitalize(word)).join(' ');
                $('#key-scopes').append(`<option value="${scope}">${scopeReadable}</option>`);
            });
        }
    });
}

const tooltipHTML = `<div id="key-tooltip" role="tooltip" class="absolute z-10 invisible inline-block px-3 py-2
                          text-sm font-medium text-white transition-opacity duration-300 bg-gray-900 rounded-lg shadow-sm 
                          opacity-0 tooltip dark:bg-gray-700"><span>Click to Copy</span><div class="tooltip-arrow" 
                          data-popper-arrow></div></div>`
