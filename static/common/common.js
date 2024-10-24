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
