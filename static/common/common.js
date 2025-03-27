let $popupModal = $('#popup-modal');
let $alertModal = $('#alert-modal');

window.addEventListener('load', function () {
    if ($('#popup-modal').length > 0)
        window.popupModal = FlowbiteInstances.getInstance('Modal', 'popup-modal');
    if ($('#alert-modal').length > 0)
        window.alertModal = FlowbiteInstances.getInstance('Modal', 'alert-modal');
    if (window.popupModal) {
        popupModal._options.closable = false;
        popupModal._options.onShow = () => {
            setTimeout(() => {
                $popupModal.addClass('show');
            }, 10);
        }
        popupModal._options.onHide = () => {
            $popupModal.removeClass('show');
        }
    }
    if (window.alertModal) {
        alertModal._options.closable = false;
        alertModal._options.onShow = function () {
            setTimeout(() => {
                $alertModal.addClass('show');
            }, 10);
        };
        alertModal._options.onHide = function () {
            $alertModal.removeClass('show');
        }
    }
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
        nsid: parts[4] ? parts[4] : window.localStorage.getItem('nsid'),
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

function normalizeTime(time, pretty = false) {
    if (!time) return 'None';
    const date = new Date(time);
    const now = new Date();
    const diffMs = now - date;
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = diffMs / (1000 * 60 * 60);

    if (pretty && diffHours < 24) {
        if (diffMinutes < 1) return 'Just now';
        if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
        const hours = Math.floor(diffHours);
        const decimalPart = diffHours - hours;
        if (decimalPart > 0) {
            const roundedHours = Math.round(diffHours * 10) / 10;
            return `${roundedHours} hours ago`;
        }
        return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    }

    return date.toLocaleString(undefined, {
        year: "2-digit",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true
    });
}

function timeIsSimilar(time1, time2) {
    const date1 = new Date(time1);
    const date2 = new Date(time2);
    const diffInMs = Math.abs(date1.getTime() - date2.getTime());
    return diffInMs <= 500;
}

function capitalize(string) {
    return string && String(string[0]).toUpperCase() + String(string).slice(1);
}

function formatBytes(a, b = 2) {
    if (!+a) return "0 Bytes";
    const c = 0 > b ? 0 : b, d = Math.floor(Math.log(a) / Math.log(1024));
    return `${parseFloat((a / Math.pow(1024, d)).toFixed(c))} ${["Bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"][d]}`
}

function createStateBadge(state, border=true) {
    const colorSchemes = {
        blue: {
            base: 'bg-blue-100 text-blue-800',
            dark: border ? 'dark:bg-gray-700 dark:text-blue-300' : 'dark:bg-blue-900 dark:text-blue-300',
            border: 'border-blue-300'
        },
        yellow: {
            base: 'bg-yellow-100 text-yellow-800',
            dark: border ? 'dark:bg-gray-700 dark:text-yellow-300' : 'dark:bg-yellow-900 dark:text-yellow-300',
            border: 'border-yellow-300'
        },
        green: {
            base: 'bg-green-100 text-green-800',
            dark: border ? 'dark:bg-gray-700 dark:text-green-400' : 'dark:bg-green-900 dark:text-green-300',
            border: 'border-green-400'
        },
        red: {
            base: 'bg-red-100 text-red-800',
            dark: border ? 'dark:bg-gray-700 dark:text-red-400' : 'dark:bg-red-900 dark:text-red-300',
            border: 'border-red-400'
        },
        gray: {
            base: 'bg-gray-100 text-gray-800',
            dark: 'dark:bg-gray-700 dark:text-gray-300',
            border: 'border-gray-300'
        }
    };

    let colorScheme;
    switch (state) {
        case 'creating':
        case 'updating':
        case 'pending':
            colorScheme = colorSchemes.yellow;
            break;
        case 'active':
        case 'success':
        case 'running':
        case 'created':
            colorScheme = colorSchemes.green;
            break;
        case 'stopped':
        case 'deleting':
        case 'terminating':
        case 'error':
        case 'crash':
        case 'zombie':
            colorScheme = colorSchemes.red;
            break;
        default:
            colorScheme = colorSchemes.gray;
    }

    const baseClasses = 'text-xs font-medium me-2 px-2.5 py-0.5';
    const roundedClass = border ? 'rounded' : 'rounded-sm';
    const borderClass = border ? `border ${colorScheme.border}` : '';
    const stateClass = `${colorScheme.base} ${colorScheme.dark}`;

    return $('<span/>', {
        class: `${baseClasses} ${roundedClass} ${borderClass} ${stateClass}`.trim(),
        text: capitalize(state)
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

function Alert(message, callback = null, options = {}, allow_html = false) {
    if (!options.ok) options.ok = 'OK';
    if (!options.icon) options.icon = 'info';
    let $ok = $("#alert-ok");
    $ok.text(options.ok);

    if (allow_html)
        $("#alert-message").html(message);
     else
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

function copyToClip(value, defaultIconId, successIconId, tooltipId) {
    navigator.clipboard.writeText(value.trim());

    if (!defaultIconId || !successIconId || !tooltipId) return;

    $(`#${defaultIconId}`).addClass('hidden');
    $(`#${successIconId}`).removeClass('hidden');

    setTimeout(() => {
        $(`#${tooltipId}`).addClass('hidden');
    }, 100);

    setTimeout(() => {
        $(`#${defaultIconId}`).removeClass('hidden');
        $(`#${successIconId}`).addClass('hidden');
        $(`#${tooltipId}`).removeClass('hidden');
    }, 1000);
}
