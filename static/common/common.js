function parseURL() {
    // URL SCHEME: <protocol>/<host>/<app>/<nsid>/<resource-id>/<option>
    const parts = window.location.href.split('/');
    return {
        host: window.location.origin,
        app: parts[3],
        nsid: parts[4],
        resource_id: parts[5],
        option: (parts[6]) ? parts[6] : 'view',
    };
}

const currentURL = parseURL();

function CancelURL() {
    let url = parseURL();
    return `${url.host}/${url.app}/${url.nsid}`
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
    return new Date(time).toLocaleString();
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
            stateClass = 'bg-yellow-100 text-yellow-800 dark:bg-gray-700 dark:text-yellow-300 border-yellow-300';
            break;
        case 'active':
            stateClass = 'bg-green-100 text-green-800 dark:bg-gray-700 dark:text-green-400 border-green-400';
            break;
        case 'stopped':
        case 'deleting':
        case 'error':
            stateClass = 'bg-red-100 text-red-800 dark:bg-gray-700 dark:text-red-400 border-red-400';
            break;
    }
    return $('<span/>', {
        class: `text-xs font-medium me-2 px-2.5 py-0.5 rounded border ${stateClass}`, text: capitalize(state),
    });
}
