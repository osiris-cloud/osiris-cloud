window.addEventListener('load', function () {
    window.popupModal = FlowbiteInstances.getInstance('Modal', 'popup-modal');
    window.alertModal = FlowbiteInstances.getInstance('Modal', 'alert-modal');
});

function parseURL() {
    // URL SCHEME: <protocol>/<host>/<app>/<nsid>/<resource-id>/<option>
    const parts = window.location.href.split('/');
    let resourceId = parts[5];
    if (resourceId === 'create' || resourceId === 'edit')
        resourceId = undefined;
    return {
        host: window.location.origin,
        app: parts[3],
        nsid: parts[4] ? parts[4] : window.localStorage.getItem('namespace'),
        resource_id: resourceId,
        option: (parts[6]) ? parts[6] : 'view',
    };
}

const currentURL = parseURL();

function cancelURL() {
    return `${currentURL.host}/${currentURL.app}/${currentURL.nsid}` + (currentURL.resource_id ? `/${currentURL.resource_id}` : '');
}

function showLoader(show = true) {
    if (show) {
        $('#loader').removeClass('hidden');
    } else {
        $('#loader').addClass('hidden');
    }
}

function showNoResource(show = true) {
    if (show) {
        $('#no-resource').removeClass('hidden');
    } else {
        $('#no-resource').addClass('hidden');
    }
}

function normalizeTime(time) {
    const date = new Date(time);
    return date.toLocaleString(undefined, {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true
    });
}

function capitalize(string) {
    return string && String(string[0]).toUpperCase() + String(string).slice(1);
}

function formatBytes(a, b = 2) {
    if (!+a) return "0 Bytes";
    const c = 0 > b ? 0 : b, d = Math.floor(Math.log(a) / Math.log(1024));
    return `${parseFloat((a / Math.pow(1024, d)).toFixed(c))} ${["Bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"][d]}`
}

function createStateBadge(state) {
    let stateClass = '';
    switch (state) {
        case 'creating':
        case 'updating':
            stateClass = 'bg-yellow-100 text-yellow-800 dark:bg-gray-700 dark:text-yellow-300 border-yellow-300';
            break;
        case 'active':
            stateClass = 'bg-green-100 text-green-800 dark:bg-gray-700 dark:text-green-400 border-green-400';
            break;
        case 'stopped':
        case 'deleting':
        case 'error':
        case 'zombie':
            stateClass = 'bg-red-100 text-red-800 dark:bg-gray-700 dark:text-red-400 border-red-400';
            break;
    }
    return $('<span/>', {
        class: `text-xs font-medium me-2 px-2.5 py-0.5 rounded border ${stateClass}`, text: capitalize(state),
    });
}

function Confirm(message, callback, options = {}) {
    if (!options.yes) options.yes = 'Confirm';
    if (!options.no) options.no = 'Cancel';
    if (!options.icon) options.icon = 'info';

    let confirm = $("#popup-confirm");
    let deny = $("#popup-deny");

    $("#popup-message").text(message);

    if (options.icon === 'info') {
        $('#popup-icon-info').removeClass('hidden');
        $('#popup-icon-check').addClass('hidden');
    } else if (options.icon === 'check') {
        $('#popup-icon-info').addClass('hidden');
        $('#popup-icon-check').removeClass('hidden');
    }

    confirm.text(options.yes);
    deny.text(options.no);

    popupModal.show();

    confirm.unbind().click(() => {
        popupModal.hide();
        callback(true);
    });

    deny.unbind().click(() => {
        popupModal.hide();
        callback(false);
    });
}

function Alert(message, callback = null, options = {}) {
    if (!options.ok) options.ok = 'OK';
    if (!options.icon) options.icon = 'info';
    let $ok = $("#alert-ok");
    $ok.text(options.ok);

    $("#alert-message").text(message);

    if (options.icon === 'info') {
        $('#alert-icon-info').removeClass('hidden');
        $('#alert-icon-check').addClass('hidden');
    } else if (options.icon === 'check') {
        $('#alert-icon-info').addClass('hidden');
        $('#alert-icon-check').removeClass('hidden');
    }

    alertModal.show();

    $ok.unbind().click(() => {
        alertModal.hide();
        if (callback) callback();
    });
}
