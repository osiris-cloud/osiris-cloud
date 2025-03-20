const $instancesList = $('#instances-list');
const $detailsPanel = $('#instance-details');
const $instanceHeading = $('#instance-heading');
const $instancePlaceholder = $('#instance-details-placeholder');
const $containerAlerts = $('#container-alerts');
const $containerAlertTemplate = $('#container-alert-template');
const $containersTable = $('#containers-table');
const $appHeading = $("#app-name-heading");

let selectedInstance = null;
let instancesCache = {};

let CPU_LIMIT = 0; // Cores
let MEMORY_LIMIT = 0; // MB

$(document).ready(function () {
    window.appSocket = initSocketConnection();
    setInterval(updateAllTimeDisplays, 10000);
});

function updateAllTimeDisplays() {
    $('[data-started_at]').each(function () {
        const $timeElement = $(this);
        const timestamp = $timeElement.attr('data-started_at');

        if (timestamp && timestamp !== '') {
            $timeElement.text(normalizeTime(timestamp, true));
        }
    });
}

function initSocketConnection() {
    const socket = new WebSocket(`/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}`);
    let errClose = false;

    socket.addEventListener('open', (event) => {
        socket.send(JSON.stringify({'watch': 'instances'}));
        socket.send(JSON.stringify({'watch': 'stat'}));
        socket.send(JSON.stringify({'watch': 'events'}));
        socket.send(JSON.stringify({'watch': 'usage'}));

        $instancesList.empty();
        $instancePlaceholder.find('p').text('Click on an instance to view details');
    });

    socket.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'error') {
            errClose = true;
            return Alert(data.message || "Internal Server Error", () => {
                window.location.href = `${currentURL.host}/${currentURL.app}/${currentURL.nsid}`;
            });
        }

        if (data.stat !== undefined) {
            const stat = data.stat;
            CPU_LIMIT = stat.cpu_limit;
            MEMORY_LIMIT = stat.memory_limit;

            $appHeading.find('span').remove();
            $appHeading.append(createStateBadge(stat.app_state))
            updateStatChart(stat.running, stat.pending, stat.desired);
        }

        if (data.instance !== undefined) {
            handleInstanceEvent(data.instance);
        }

        if (data.events !== undefined) {
            updateEvents(data.events);
        }

        if (data.usage !== undefined) {
            const cpu = {
                'limit': CPU_LIMIT,
                'current': data.usage.cpu
            }
            const memory = {
                'limit': MEMORY_LIMIT,
                'current': data.usage.memory
            }
            updateUsageGauges({cpu, memory});
            updateNetworkStats(data.usage.request_bytes, data.usage.response_bytes, data.usage.request_count);
        }

    });

    socket.addEventListener('close', (event) => {
        if (errClose) return;
        Confirm("Server disconnected. Please reload the page to reconnect", (ok) => {
            if (ok)
                window.location.reload();
        }, {yes: "Reload", no: "Cancel"});
    });

    socket.addEventListener('error', (error) => {
        console.error('WebSocket error:', error);
    });

    return socket;
}

function renumberInstances() {
    const irefs = [];

    $('.instance-container').each(function () {
        irefs.push($(this).data('iref'));
    });

    irefs.forEach((iref, index) => {
        if (instancesCache[iref]) {
            const newName = `Instance ${index + 1}`;
            instancesCache[iref].name = newName;
            $(`#instance-name-${iref}`).text(newName);

            if (selectedInstance && selectedInstance.iref === iref) {
                $instanceHeading.text(newName);
            }
        }
    });
}

function handleInstanceEvent(instanceEvent) {
    const event = instanceEvent.event;
    const data = instanceEvent.data;
    const iref = data.iref;

    switch (event) {
        case 'add':
            instancesCache[iref] = {
                ...data,
                name: 'Instance'
            };

            const newInstance = createInstanceElement('Instance', iref, data.state);
            newInstance.click(() => {
                $('.instance-container').removeClass('selected');
                newInstance.addClass('selected');
                showInstanceDetails(instancesCache[iref]);
            });

            newInstance.attr('data-iref', iref);

            $instancesList.append(newInstance);
            renumberInstances();

            if (Object.keys(instancesCache).length === 1 && !selectedInstance) {
                $instancePlaceholder.removeClass('hidden');
                $detailsPanel.addClass('hidden');
            }
            break;

        case 'modify':
            const existingElement = $(`.instance-container[data-iref="${iref}"]`);
            if (instancesCache[iref]) {
                const currentName = instancesCache[iref].name;

                instancesCache[iref] = {
                    ...data,
                    name: currentName
                };

                if (existingElement.length) {
                    const $flexContainer = $(`#flex-container-${iref}`);
                    $flexContainer.html('');
                    $flexContainer.append(
                        $('<span/>', {
                            class: 'font-medium',
                            text: currentName,
                            id: `instance-name-${iref}`
                        }),
                        createStateBadge(data.state, false)
                    );
                } else {
                    const newEl = createInstanceElement(currentName, iref, data.state);
                    newEl.click(() => {
                        $('.instance-container').removeClass('selected');
                        newEl.addClass('selected');
                        showInstanceDetails(instancesCache[iref]);
                    });
                    newEl.attr('data-iref', iref);
                    $instancesList.append(newEl);
                    renumberInstances();
                }
            }
            break;

        case 'delete':
            const instanceElement = $(`.instance-container[data-iref="${iref}"]`);

            if (instanceElement.length) {
                instanceElement.fadeOut(300, function () {
                    $(this).remove();
                    renumberInstances();
                });
            }

            delete instancesCache[iref];

            if (selectedInstance && iref === selectedInstance.iref) {
                selectedInstance = null;
                $detailsPanel.addClass('hidden');
                $instancePlaceholder.removeClass('hidden');
            }

            if (Object.keys(instancesCache).length === 0) {
                $instancePlaceholder.removeClass('hidden');
                $detailsPanel.addClass('hidden');
            }
            break;
    }

    if (selectedInstance && (iref === selectedInstance.iref) && event !== 'delete') {
        showInstanceDetails(instancesCache[iref]);
    }
}

function createInstanceElement(name, iref, state) {
    const $flexContainer = $('<div/>', {
        class: 'flex items-center justify-between',
        id: `flex-container-${iref}`
    }).append(
        $('<span/>', {
            class: 'font-medium',
            text: name,
            id: `instance-name-${iref}`
        }),
        createStateBadge(state, false)
    );

    return $('<div/>', {
        class: 'instance-container cursor-pointer p-3 rounded-lg border dark:border-gray-500 mb-2',
        id: `instance-${iref}`
    }).append($flexContainer);
}

function showInstanceDetails(instance) {
    selectedInstance = instance;

    $instanceHeading.text(instance.name);

    $instancePlaceholder.addClass('hidden');
    $detailsPanel.removeClass('hidden');

    $containerAlerts.empty();
    $containersTable.empty();

    // Main container
    const mainContainer = {
        ...instance.main,
        cref: 'main'
    };

    $containersTable.append(CreateContainerRow('Main', mainContainer));
    if (mainContainer.message)
        addContainerMessage("[Main] " + mainContainer.message);

    // Sidecar container
    if (instance.sidecar && Object.keys(instance.sidecar).length > 0) {
        const sidecarContainer = {
            ...instance.sidecar,
            cref: 'sidecar'
        };
        $containersTable.append(CreateContainerRow('Sidecar', sidecarContainer));
        if (sidecarContainer.message)
            addContainerMessage("[Sidecar] " + sidecarContainer.message);
    }

    // Init container
    if (instance.init && Object.keys(instance.init).length > 0) {
        const initContainer = {
            ...instance.init,
            cref: 'init'
        };

        $containersTable.append(CreateContainerRow('Init', initContainer));
        if (initContainer.message)
            addContainerMessage("[Init] " + initContainer.message);
    }
}

function addContainerMessage(messages) {
    const messageArray = Array.isArray(messages) ? messages : [messages];
    messageArray.forEach(message => {
        const $alert = $($containerAlertTemplate.html());
        $alert.find('span').text(message);
        $alert.hide()
            .appendTo($containerAlerts)
            .fadeIn(300);
    });
}

function CreateContainerRow(cType, container) {
    let $row = $('<tr/>', {
        class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700',
        id: `${selectedInstance.iref}-${container.cref}`
    });

    const $stateBadge = createStateBadge(container.state, false);

    $row.append($('<th/>', {
        scope: 'row',
        class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white',
        text: cType + (container.port ? ` -> ${container.port}/${container.port_protocol}` : ''),
    })).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50 state-cell',
        }).append($stateBadge)
    ).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50', text: container.image,
        })
    ).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50', text: container.restarts,
        })
    ).append($('<td/>', {
            class: 'px-6 py-4 dark:text-gray-50',
            text: normalizeTime(container.started_at, true),
            'data-started_at': container.started_at
        })
    );
    const $logsButton = $('<button/>', {
        class: 'font-medium text-gray-600 dark:text-gray-300 dark:hover:text-white', text: 'Logs', click: () => {
            viewLogs(selectedInstance.iref, container.cref);
        }
    });
    const $shellButton = $('<button/>', {
        class: 'font-medium text-gray-600 dark:text-gray-300 dark:hover:text-white', text: 'Shell', click: () => {
            connectShell(selectedInstance.iref, container.cref);
        }
    });
    $row.append($('<td/>', {class: 'px-6 py-4 flex gap-x-2 items-center'}).append($logsButton, $shellButton));
    return $row;
}

function viewLogs(iref, cref) {
    addLogsTab(`${selectedInstance.name}: ${capitalize(cref)}`, iref, cref);
}

function connectShell(iref, cref) {
    addConsoleTab(`${selectedInstance.name}: ${capitalize(cref)}`, iref, cref);
}

function deleteApp() {
    Confirm("Are you sure you want to delete this app?", (ok) => {
        if (ok) {
            $.ajax({
                url: `/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}`,
                type: 'DELETE',
                headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
                success: (data) => {
                    Alert("App deleted", () => {
                        window.location.href = `${currentURL.host}/${currentURL.app}/${currentURL.nsid}`;
                    });
                },
                error: (resp) => {
                    Alert(resp.responseJSON.message || "Internal Server Error");
                }
            });
        }
    });
}

$('#delete-app').click(deleteApp);

function restartApp() {
    Confirm("Do you want to restart all instances?", (ok) => {
        if (ok) {
            $.ajax({
                url: `/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}/restart`,
                type: 'POST',
                headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
                error: (resp) => {
                    Alert(resp.responseJSON.message || "Internal Server Error");
                }
            });
        }
    });
}

$('#restart-app').click(function(){
    restartApp();
    $(this).attr('disabled', true);
    $(this).addClass('cursor-not-allowed');
    setTimeout(() => {
        $(this).removeAttr('disabled');
        $(this).removeClass('cursor-not-allowed');
    }, 5000);
});
