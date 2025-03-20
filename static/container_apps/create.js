$(document).ready(() => {
    const tabsElement = document.getElementById('containers-tab');
    const tabElements = [
        {
            id: 'main',
            triggerEl: document.querySelector('#main-tab'),
            targetEl: document.querySelector('#main-container'),
        },
        {
            id: 'sidecar',
            triggerEl: document.querySelector('#sidecar-tab'),
            targetEl: document.querySelector('#sidecar-container'),
        },
        {
            id: 'init',
            triggerEl: document.querySelector('#init-tab'),
            targetEl: document.querySelector('#init-container'),
        },
    ];
    let firstLoad = true;
    const options = {
        defaultTabId: 'main',
        activeClasses:
            'dark:bg-primary-700 bg-primary-600 dark:text-white text-white dark:text-gray-200',
        inactiveClasses:
            'dark:bg-gray-700 dark:hover:bg-gray-600 hover:bg-gray-300 bg-gray-200',
        onShow: (e) => {
            if (firstLoad) {
                setTimeout(() => {
                    firstLoad = false;
                    loadRegistries();
                    loadSecrets();
                }, 800);
            } else {
                loadRegistries();
                loadSecrets();
            }
        },
    };
    const instanceOptions = {
        id: 'containers-tab',
        override: true
    };
    const tabs = new Tabs(tabsElement, tabElements, options, instanceOptions);
});

const CTYPES = ['main', 'sidecar', 'init'];
let REGISTRIES = [];
let SECRETS = {'opaque': [], 'dockerconfig': []};
const RESOURCE_DEFS = {
    'small': {'cpu': 0.25, 'memory': 0.5},
    'standard': {'cpu': 0.5, 'memory': 1},
    'medium': {'cpu': 1, 'memory': 2},
    'large': {'cpu': 2, 'memory': 4},
}

$('#connection-protocol').on('change', function () {
    if ($(this).val() !== 'http')
        $('div').filter('[data-hw-http="true"]').hide();
    else
        $('div').filter('[data-hw-http="true"]').show();
});

function loadRegistries() {
    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}`,
        method: 'GET',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            REGISTRIES = data.registries;
        }
    });
}

function loadRegistryList($select) {
    $select.children().not(':first').remove();

    REGISTRIES.forEach((registry) => {
        const $option = $('<option/>', {
            value: registry.crid,
            text: registry.name,
            class: "dark:bg-gray-700 p-1"
        });
        $select.append($option);
    });
}

function loadImageList(target, crid) {
    const $select = $(`#${target}-oc-img`);

    $select.children().not(':first').remove();

    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}/${crid}/stat`,
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            data.stats.forEach((stat) => {
                const imageName = stat['sub'];
                const tags = stat['tags'];
                for (const tag of tags) {
                    const $option = $('<option/>', {
                        value: getUrlByCrid(crid) + '/' + imageName + ':' + tag['name'],
                        text: imageName + ':' + tag['name'],
                        class: "dark:bg-gray-700 p-1"
                    });
                    $select.append($option);
                }
            });
        }
    });
}

function loadSecrets() {
    $.ajax({
        url: `/api/secret-store/${currentURL.nsid}`,
        method: 'GET',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            SECRETS.opaque = [];
            SECRETS.dockerconfig = [];

            for (const secret of data.secrets)
                SECRETS[secret.type].push(secret);
        }
    });
}

function loadSecretList($select, sType) {
    $select.children().not(':first').remove();

    SECRETS[sType].forEach((secret) => {
        const $option = $('<option/>', {
            value: secret.secretid,
            text: secret.name,
            class: "dark:bg-gray-700 p-1"
        });
        $select.append($option);
    });
}

// Handle registry and image list events
CTYPES.forEach(type => {
    $(`#${type}-oc-img-reg`)
        .on('focus', function () {
            loadRegistryList($(this));
        })
        .on('change', function () {
            loadImageList(type, $(this).val());
        });
});

// Handle environment secret events
CTYPES.forEach(type => {
    $(`#${type}-env-secret`).on('focus', function () {
        loadSecretList($(this), 'opaque');
    });
});

// Handle pull secret events
CTYPES.forEach(type => {
    $(`#${type}-oc-img-pull-secret`).on('focus', function () {
        loadSecretList($(this), 'dockerconfig');
    });
});

function isValidIPOrSubnet(value) {
    if (value.includes('-')) {
        const [startIP, endIP] = value.split('-');
        return isValidIP(startIP) && isValidIP(endIP) && isValidIPRange(startIP, endIP);
    }

    const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
    if (!cidrRegex.test(value)) return false;

    const parts = value.split('.');
    const ipParts = parts[3].split('/');
    const isValidRange = parts.slice(0, 3).every(part => parseInt(part) >= 0 && parseInt(part) <= 255);
    const isValidLastPart = parseInt(ipParts[0]) >= 0 && parseInt(ipParts[0]) <= 255;
    const isValidSubnet = ipParts[1] ? parseInt(ipParts[1]) >= 0 && parseInt(ipParts[1]) <= 32 : true;

    return isValidRange && isValidLastPart && isValidSubnet;
}

function isValidIP(ip) {
    const parts = ip.split('.');
    if (parts.length !== 4) return false;
    return parts.every(part => {
        const num = parseInt(part);
        return num >= 0 && num <= 255 && part === num.toString(); // Ensures no leading zeros
    });
}

function isValidIPRange(startIP, endIP) {
    const start = ipToNumber(startIP);
    const end = ipToNumber(endIP);
    return start !== null && end !== null && start <= end;
}

function ipToNumber(ip) {
    const parts = ip.split('.');
    if (parts.length !== 4) return null;

    return parts.reduce((acc, part) => {
        const num = parseInt(part);
        if (isNaN(num) || num < 0 || num > 255) return null;
        return (acc << 8) + num;
    }, 0);
}

function getUrlByCrid(crid) {
    const registry = REGISTRIES.find(reg => reg.crid === crid);
    return registry ? registry.url : null;
}


function getContainerSpec(type) {
    if (type !== 'main') {
        const $containerToggle = $(`#${type}-container-toggle`);
        const isEnabled = $containerToggle.length ? $containerToggle.prop('checked') : false;

        if (!isEnabled)
            return {};
    }

    const containerSpec = {};
    containerSpec['type'] = type;

    const isOsirisCloud = $(`#${type}-img-src-oc`).hasClass('bg-blue-700');

    if (isOsirisCloud) {
        containerSpec['image'] = $(`#${type}-oc-img`).val();

    } else {
        const imageUrl = $(`#${type}-img-url`).val().trim();
        const pullSecret = $(`#${type}-oc-img-pull-secret`).val().trim();

        containerSpec['image'] = imageUrl;

        if (pullSecret)
            containerSpec['pull_secret'] = pullSecret;
    }

    const envSecret = $(`#${type}-env-secret`).val();
    if (envSecret)
        containerSpec['env_secret'] = envSecret;

    const command = $(`#${type}-cmd`).val().trim();
    const args = $(`#${type}-args`).val().trim();

    if (command)
        containerSpec['command'] = command;

    if (args)
        containerSpec['args'] = args.split(' ').filter(arg => arg.length > 0);

    if (type === 'main') {
        const port = $('#main-container-port').val();
        const protocol = $('#main-container-proto').val();
        containerSpec['port'] = !isNaN(port) ? Number(port) : null;
        containerSpec['port_protocol'] = protocol;
    }

    let size = $(`#${type}-size`).val();

    containerSpec['cpu'] = RESOURCE_DEFS[size].cpu;
    containerSpec['memory'] = RESOURCE_DEFS[size].memory;

    return containerSpec;
}

$('#create-app-button').on('click', function () {
    const appName = $('#app-name').val().trim();
    const restartPolicy = $('#restart-policy').val();
    const connectionProtocol = $('#connection-protocol').val();
    const mainContainer = getContainerSpec('main');
    const sidecarContainer = getContainerSpec('sidecar');
    const initContainer = getContainerSpec('init');
    const volumes = getVolumeData();
    const scalingEnabled = $('#autoscale-toggle').is(':checked');
    const updateStrategy = $('#update-strategy').val();
    let scaling = {
        'min_replicas': Number($('#min-replica').val())
    }

    if (scalingEnabled)
        scaling = {
            ...scaling,
            'max_replicas': Number($('#max-replica').val()),
            'scaleup_stb_window': Number($('#scaleup-stb-window').val()),
            'scaledown_stb_window': Number($('#scaledown-stb-window').val()),
            'scalers': getScalers(),
        }

    const firewall = {
        'precedence': $('#fw-precedence').val(),
        'allow': getAllowRules().map(rule => rule.trim()),
        'deny': getDenyRules().map(rule => rule.trim()),
        'nyu_only': $('#nyu-net-only').prop('checked'),
    }

    if (!appName) {
        Alert('App name is required');
        return;
    }

    if (!processedSlug) {
        Alert('Please enter a slug');
        return;
    }

    if (!slugAvailable) {
        Alert('Slug is not available. Please try another');
        return;
    }

    for (const container of [mainContainer, sidecarContainer, initContainer]) {
        if (Object.keys(container).length === 0)
            continue;
        if (!container.image) {
            Alert(`Image is required for ${container.type} container`);
            return;
        }
    }

    if (!mainContainer.port)
        Alert('Please specify the port for main container');

    for (const [i, volume] of volumes.entries()) {
        if (volume.type === 'secret' && !volume.secretid) {
            Alert(`Please select a secret for volume ${i + 1}`);
            return;
        }
        if (!volume.name) {
            Alert(`Name is required for volume ${i + 1}`);
            return;
        }
        if (!volume.size && !(volume.type === 'secret' || volume.type === 'temp')) {
            Alert(`Size is required for volume ${i + 1}`);
            return;
        }
        if (!volume.mount_path) {
            Alert(`Mount path is required for volume ${i + 1}`);
            return;
        }
    }

    if (scaling.min_replicas >= scaling.max_replicas) {
        Alert('Max replicas must be greater than min replicas');
        return;
    }

    if (scalingEnabled && scaling.scalers.length === 0) {
        Alert('At least one scaler is required when autoscaling is enabled');
        return;
    }

    for (const rule of firewall.deny) {
        if (!rule) continue;
        if (!isValidIPOrSubnet(rule))
            Alert(`Invalid IP or subnet in deny rule: "${rule}"`);
    }
    for (const rule of firewall.allow) {
        if (!rule) continue;
        if (!isValidIPOrSubnet(rule))
            Alert(`Invalid IP or subnet in allow rule: "${rule}"`);
    }


    if ($(this).text().trim() === 'Validate') {
        $(this).text('Validating...');
        setTimeout(() => {
            $(this).text('Create');
        }, 200);
        return;
    }

    $.ajax({
        url: `/api/container-apps/${currentURL.nsid}`,
        method: 'PUT',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            'name': appName,
            'slug': processedSlug,
            'connection_protocol': connectionProtocol,
            'restart_policy': restartPolicy,
            'update_strategy': updateStrategy,
            'main': mainContainer,
            'sidecar': sidecarContainer,
            'init': initContainer,
            'volumes': volumes,
            'scaling': scaling,
            'firewall': firewall,
        }),
        success: (data) => {
            Confirm('App deployed', (ok) => {
                if (ok) {
                    window.location.href = `/container-apps/${currentURL.nsid}/${data.app.appid}`;
                }
            }, {'yes': 'View app', 'no': 'Go back', 'icon': 'check'});
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });

});


const $appSlug = $('#app-slug');
const $appSlugAvailable = $('#app-slug-availability');
let slugAvailable = false;
let processedSlug = '';
$appSlug.on('input', function () {
    $appSlugAvailable.text('');
    slugAvailable = false;

    let slug = $(this).val()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '-')
        .replace(/-+/g, '-');

    $appSlug.val(slug);

    if (slug.length < 3) {
        $appSlugAvailable.text('Subdomain must have at least 3 characters');
        $appSlugAvailable.css("color", "red");
        slugAvailable = false;
        return;
    }

    if (slug.startsWith('-')) {
        $appSlugAvailable.text('Subdomain cannot start with a hyphen');
        $appSlugAvailable.css("color", "red");
        slugAvailable = false;
        return;
    }

    if (slug.endsWith('-')) {
        $appSlugAvailable.text('Subdomain cannot end with a hyphen');
        $appSlugAvailable.css("color", "red");
        slugAvailable = false;
        return;
    }

    slug = slug.trim().replace(/^-+|-+$/g, '');
    processedSlug = slug;

    $.ajax({
        url: '/api/container-apps/name-check',
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        data: {'slug': slug},
        success: (data) => {
            if (data.available) {
                $appSlugAvailable.text('Available');
                $appSlugAvailable.css("color", "lawngreen");
                slugAvailable = true;
            } else {
                $appSlugAvailable.text('Not available. Try another.');
                $appSlugAvailable.css("color", "red");
                slugAvailable = false;
            }
        }
    });
});

