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
    loadAppValues();
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

    const $size = $(`#${type}-size`);
    let size = $size.val();

    if (size === 'custom') {
        containerSpec['cpu'] = Number($size.find(':selected').data('cpu'));
        containerSpec['memory'] = Number($size.find(':selected').data('memory'));
    } else {
        containerSpec['cpu'] = RESOURCE_DEFS[size].cpu;
        containerSpec['memory'] = RESOURCE_DEFS[size].memory;
    }

    return containerSpec;
}

function putContainerSpec(type, values) {
    if (type !== 'main' && $(`#${type}-container-toggle`).length) {
        const isEnabled = Object.keys(values).length > 0;
        $(`#${type}-container-toggle`).prop('checked', isEnabled);
        if (isEnabled) {
            $(`#${type}-container-content`).show();
        } else {
            $(`#${type}-container-content`).hide();
            return;
        }
    }

    if (values.native_image) {
        $(`#${type}-img-src-oc`).removeClass('text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700')
            .addClass('bg-blue-700 text-white');
        $(`#${type}-img-src-ext`).removeClass('bg-blue-700 text-white')
            .addClass('text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700');

        $(`#${type}-oc-img-reg-con`).show();
        $(`#${type}-oc-img-con`).show();
        $(`#${type}-img-url-con`).hide();
        $(`#${type}-oc-img-pull-secret-con`).hide();
        $(`#${type}-oc-img`).val(values.image);

    } else {
        $(`#${type}-img-src-ext`).removeClass('text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700')
            .addClass('bg-blue-700 text-white');
        $(`#${type}-img-src-oc`).removeClass('bg-blue-700 text-white')
            .addClass('text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700');

        $(`#${type}-oc-img-reg-con`).hide();
        $(`#${type}-oc-img-con`).hide();
        $(`#${type}-img-url-con`).show();
        $(`#${type}-oc-img-pull-secret-con`).show();
        $(`#${type}-img-url`).val(values.image);

        if (values.pull_secret) {
            $(`#${type}-oc-img-pull-secret`).val(values.pull_secret);
        } else {
            $(`#${type}-oc-img-pull-secret`).val('');
        }
    }

    if (values.env_secret) {
        $(`#${type}-env-secret`).val(values.env_secret);
    } else {
        $(`#${type}-env-secret`).val('');
    }

    if (values.command) {
        $(`#${type}-cmd`).val(values.command);
    } else {
        $(`#${type}-cmd`).val('');
    }

    if (values.args && Array.isArray(values.args)) {
        $(`#${type}-args`).val(values.args.join(' '));
    } else {
        $(`#${type}-args`).val('');
    }

    if (type === 'main') {
        if (values.port) {
            $('#main-container-port').val(values.port);
        } else {
            $('#main-container-port').val('');
        }

        if (values.port_protocol) {
            $('#main-container-proto').val(values.port_protocol);
        }
    }

    let selectedSize = null;
    for (const [size, resources] of Object.entries(RESOURCE_DEFS)) {
        if (resources.cpu === values.cpu && resources.memory === values.memory) {
            selectedSize = size;
            break;
        }
    }

    if (selectedSize) {
        $(`#${type}-size`).val(selectedSize);
    } else {
        const customOption = `Custom (${values.cpu} CPU, ${values.memory} GiB RAM)`;

        $(`#${type}-size option[value="custom"]`).remove();

        $(`#${type}-size`).append(
            $('<option>', {
                value: 'custom',
                class: 'dark:bg-gray-700',
                text: customOption,
                selected: true,
                data: {cpu: values.cpu, memory: values.memory}
            })
        );
    }
}

$('#save-app-button').on('click', function () {
    const appName = $('#app-name').val().trim();
    const mainContainer = getContainerSpec('main');
    const sidecarContainer = getContainerSpec('sidecar');
    const initContainer = getContainerSpec('init');
    const volumes = getVolumeData();
    const scalingEnabled = $('#autoscale-toggle').is(':checked');
    const updateStrategy = $('#update-strategy').val();
    let scaling = {
        'min_replicas': Number($('#min-replica').val())
    }

    const ingressHosts = getIngressHosts();
    let domains = [];
    let alertDomain = false;

    for (host of ingressHosts) {
        if (host.status === 'pending')
            alertDomain = true;
        domains.push(host.domain);
    }

    if (alertDomain)
        Alert('Some domains are still pending verification and TLS may not work till they are propagated');

    const ingress = {
        'hosts': domains,
        'pass_tls': $('#tls-passthrough').is(':checked'),
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

    $.ajax({
        url: `/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}`,
        method: 'PATCH',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            'name': appName,
            'update_strategy': updateStrategy,
            'main': mainContainer,
            'sidecar': sidecarContainer,
            'init': initContainer,
            'volumes': volumes,
            'scaling': scaling,
            'firewall': firewall,
            'ingress': ingress,
        }),
        success: (data) => {
            Confirm('App Updated', (ok) => {
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

window.APP = {}

function loadAppValues() {
    $.ajax({
        url: `/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}`,
        method: 'GET',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        success: (data) => {
            window.APP = data.app;

            putContainerSpec('main', APP.main);
            if (APP.sidecar)
                putContainerSpec('sidecar', APP.sidecar);
            if (APP.init)
                putContainerSpec('init', APP.init);

            const appUrl = new URL(APP.url).hostname;
            $('.domain-record-value').text(appUrl);

            putVolumeData(APP.volumes);
            putScalers(APP.scaling.scalers);
            putAllowRules(APP.firewall.allow);
            putDenyRules(APP.firewall.deny);
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
}

