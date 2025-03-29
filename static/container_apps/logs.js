window.addEventListener('load', function () {
    let inactiveTabsMap = new Map();
    let isInitializingLogView = false;
    let activeLogTabId = null;

    // {name, iref, cref, terminal, fitAddon, socket, pendingConnection, sessionTimeout, autoScrollEnabled, tailLines, showTimestamps, logContent}
    let logsTabsMap = new Map();

    const LOG_SESSION_TIMEOUT = 60000;
    const TAIL_LINE_OPTIONS = [50, 100, 200, 500, 1000];

    const logsModalEl = document.getElementById('logs-modal');
    const options = {
        onShow: () => {
            if (isInitializingLogView)
                return;

            setTimeout(() => {
                if (activeLogTabId && logsTabsMap.has(activeLogTabId)) {
                    const tabInfo = logsTabsMap.get(activeLogTabId);

                    if (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) {
                        activateLogTab(activeLogTabId, true);
                    } else {
                        activateLogTabUI(activeLogTabId);

                        if (tabInfo.sessionTimeout) {
                            clearTimeout(tabInfo.sessionTimeout);
                            tabInfo.sessionTimeout = null;
                        }

                        if (inactiveTabsMap.has(activeLogTabId)) {
                            inactiveTabsMap.delete(activeLogTabId);
                        }
                    }
                } else if (logsTabsMap.size > 0) {
                    const firstTabId = Array.from(logsTabsMap.keys())[0];
                    const tabInfo = logsTabsMap.get(firstTabId);

                    if (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) {
                        activateLogTab(firstTabId, true);
                    } else {
                        activateLogTabUI(firstTabId);
                        activeLogTabId = firstTabId;

                        if (tabInfo.sessionTimeout) {
                            clearTimeout(tabInfo.sessionTimeout);
                            tabInfo.sessionTimeout = null;
                        }

                        if (inactiveTabsMap.has(firstTabId)) {
                            inactiveTabsMap.delete(firstTabId);
                        }
                    }
                }
            }, 200);
        },
        onHide: () => {
            scheduleTimeoutsForAllTabs();
        }
    };
    const instanceOptions = {
        id: 'logs-modal',
        override: true,
    };

    const logsModal = new Modal(logsModalEl, options, instanceOptions);

    function scheduleTimeoutsForAllTabs() {
        logsTabsMap.forEach((tabInfo, tabId) => {
            if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
                scheduleInactiveLogTabTimeout(tabId);
            }
        });
    }

    function checkTabsScroll() {
        const $tabsContainer = $('#logs-tabs-container');
        const $tabsList = $('#logs-tabs');

        if ($tabsContainer.length && $tabsList.length) {
            const containerWidth = $tabsContainer.width();
            const tabsWidth = $tabsList[0].scrollWidth;
            const scrollLeft = $tabsContainer.scrollLeft();

            const hasOverflow = tabsWidth > containerWidth;
            const scrolledToStart = scrollLeft < 10;
            const scrolledToEnd = scrollLeft + containerWidth >= tabsWidth - 10;

            if (hasOverflow && !scrolledToStart) {
                $('#logs-scroll-left').fadeIn(200);
            } else {
                $('#logs-scroll-left').fadeOut(100);
            }

            if (hasOverflow && !scrolledToEnd) {
                $('#logs-scroll-right').fadeIn(200);
            } else {
                $('#logs-scroll-right').fadeOut(100);
            }
        }
    }

    // Function to strip timestamp from log message
    function stripTimestamp(logMessage) {
        // If the message is empty or only whitespace, return as is
        if (!logMessage.trim()) {
            return logMessage;
        }

        // Find the first space after the timestamp (ISO8601 format ends with Z followed by a space)
        const timestampEndPos = logMessage.indexOf('Z ');

        // If we found the timestamp end, return everything after it
        if (timestampEndPos > 0) {
            // +2 to skip the 'Z ' part
            return logMessage.substring(timestampEndPos + 2);
        }

        // If the line only contains a timestamp (ends with Z without trailing content)
        if (logMessage.trim().endsWith('Z')) {
            return '';
        }

        // If no timestamp format was found, return the original message
        return logMessage;
    }

    function initializeLogView(tabId, logElementId, tabInfo) {
        const $logElement = $(`#${logElementId}`);
        if ($logElement.length === 0) return null;

        $logElement.empty();

        const $toolbar = $('<div/>', {
            class: 'flex justify-between items-center p-2 bg-gray-800 text-white'
        });

        const $controlsLeft = $('<div/>', {
            class: 'flex items-center space-x-4'
        });

        const $tailLinesContainer = $('<div/>', {
            class: 'flex items-center'
        });

        const $tailLinesLabel = $('<label/>', {
            for: `taillines-${tabId}`,
            text: 'Tail',
            class: 'mr-2 text-sm font-medium text-gray-300'
        });

        const $tailLinesDropdown = $('<select/>', {
            id: `taillines-${tabId}`,
            class: 'bg-gray-700 text-white text-sm rounded border-gray-600 focus:ring-blue-500 focus:border-blue-500 p-1'
        });

        TAIL_LINE_OPTIONS.forEach(option => {
            $tailLinesDropdown.append($('<option/>', {
                value: option,
                text: option + ' lines',
                selected: option === tabInfo.tailLines
            }));
        });

        $tailLinesDropdown.on('change', function () {
            const newTailLines = parseInt($(this).val(), 10);
            tabInfo.tailLines = newTailLines;

            if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
                tabInfo.socket.send(JSON.stringify({
                    tail_lines: newTailLines
                }));

                tabInfo.terminal.clear();
                tabInfo.logContent = '';
                tabInfo.terminal.writeln('\x1b[33mRequesting logs with new tail value...\x1b[0m');
            }
        });

        $tailLinesContainer.append($tailLinesLabel, $tailLinesDropdown);

        // Auto-scroll checkbox
        const autoScrollCheckboxId = `autoscroll-${tabId}-${Date.now()}`;
        const $autoScrollCheckbox = $('<input/>', {
            type: 'checkbox',
            id: autoScrollCheckboxId,
            class: 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded-sm focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600',
            checked: true
        });

        $autoScrollCheckbox.on('change', function () {
            tabInfo.autoScrollEnabled = this.checked;
            if (this.checked && tabInfo.terminal) {
                setTimeout(() => tabInfo.terminal.scrollToBottom(), 0);
            }
        });

        const $autoScrollToggle = $('<div/>', {
            class: 'flex items-center'
        }).append(
            $autoScrollCheckbox,
            $('<label/>', {
                for: autoScrollCheckboxId,
                text: 'Auto scroll',
                class: 'ms-2 text-sm font-medium text-gray-300 cursor-pointer'
            }).on('click', function () {
                $autoScrollCheckbox.prop('checked', !$autoScrollCheckbox.prop('checked')).trigger('change');
                return false;
            })
        );

        // Timestamp checkbox
        const timestampCheckboxId = `timestamps-${tabId}-${Date.now()}`;
        const $timestampCheckbox = $('<input/>', {
            type: 'checkbox',
            id: timestampCheckboxId,
            class: 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded-sm focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600',
            checked: tabInfo.showTimestamps || false
        });

        $timestampCheckbox.on('change', function () {
            tabInfo.showTimestamps = this.checked;

            // Reprocess and display logs with or without timestamps
            if (tabInfo.terminal) {
                tabInfo.terminal.clear();

                // Split the raw logs by newline
                const rawLogs = tabInfo.logContent.split('\n');

                // Process each line according to the timestamp setting
                rawLogs.forEach(logLine => {
                    if (logLine.trim()) {
                        if (tabInfo.showTimestamps) {
                            tabInfo.terminal.writeln(logLine);
                        } else {
                            tabInfo.terminal.writeln(stripTimestamp(logLine));
                        }
                    }
                });

                if (tabInfo.autoScrollEnabled) {
                    setTimeout(() => tabInfo.terminal.scrollToBottom(), 0);
                }
            }
        });

        const $timestampToggle = $('<div/>', {
            class: 'flex items-center ml-4'
        }).append(
            $timestampCheckbox,
            $('<label/>', {
                for: timestampCheckboxId,
                text: 'Show timestamps',
                class: 'ms-2 text-sm font-medium text-gray-300 cursor-pointer'
            }).on('click', function () {
                $timestampCheckbox.prop('checked', !$timestampCheckbox.prop('checked')).trigger('change');
                return false;
            })
        );

        $controlsLeft.append($tailLinesContainer, $autoScrollToggle, $timestampToggle);

        const $controlsRight = $('<div/>', {
            class: 'flex items-center'
        });

        const $clearButton = $('<button/>', {
            class: 'px-3 py-1 bg-gray-700 text-sm rounded hover:bg-gray-600',
            text: 'Clear',
            click: function () {
                if (tabInfo.terminal) {
                    tabInfo.terminal.clear();
                    tabInfo.logContent = '';
                }
            }
        });

        const $downloadButton = $('<button/>', {
            class: 'px-3 py-1 bg-gray-700 text-sm rounded hover:bg-gray-600 ml-2',
            text: 'Download',
            click: function () {
                if (tabInfo.terminal) {
                    const logText = tabInfo.logContent || '';

                    const blob = new Blob([logText], {type: 'text/plain'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;

                    const now = new Date();
                    const dateStr = now.toISOString().replace(/[:.]/g, '-').substring(0, 19);
                    a.download = `${tabInfo.name.replace(/[^a-z0-9]/gi, '-').toLowerCase()}-logs-${dateStr}.txt`;

                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);

                    if (!tabInfo.downloadToast) {
                        tabInfo.downloadToast = $('<div/>', {
                            class: 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg z-50',
                            text: 'Download complete',
                            css: {display: 'none'}
                        }).appendTo('body');
                    }

                    tabInfo.downloadToast.fadeIn(300).delay(2000).fadeOut(300);
                }
            }
        });

        $controlsRight.append($clearButton, $downloadButton);
        $toolbar.append($controlsLeft, $controlsRight);

        const $terminalContainer = $('<div/>', {
            class: 'terminal-container relative',
            css: {'height': '400px'}
        });

        $logElement.append($toolbar, $terminalContainer);

        const initialRows = 24;
        const initialCols = 120;

        const fitAddon = new FitAddon();

        const terminal = new Terminal({
            cursorBlink: false,
            fontFamily: 'monospace',
            fontSize: 14,
            rows: initialRows,
            cols: initialCols,
            theme: {
                background: '#1a1a1a',
                foreground: '#f0f0f0'
            },
            allowTransparency: true,
            disableStdin: true,
            convertEol: true
        });

        tabInfo.fitAddon = fitAddon;
        tabInfo.terminal = terminal;
        tabInfo.lastDimensions = {cols: initialCols, rows: initialRows};
        tabInfo.logContent = '';

        terminal.loadAddon(fitAddon);

        try {
            const webglAddon = new WebglAddon();
            terminal.loadAddon(webglAddon);
        } catch (e) {
            console.warn('WebGL not supported, falling back to canvas renderer', e);
        }

        terminal.loadAddon(new WebLinksAddon());
        terminal.open($terminalContainer[0]);

        try {
            fitAddon.fit();
        } catch (e) {
            console.error('Error fitting terminal:', e);
        }

        const resizeObserver = new ResizeObserver(() => {
            if (tabInfo.resizeTimeout) {
                clearTimeout(tabInfo.resizeTimeout);
            }

            tabInfo.resizeTimeout = setTimeout(() => {
                if (tabInfo.terminal && tabInfo.fitAddon) {
                    try {
                        tabInfo.fitAddon.fit();
                        const dimensions = tabInfo.fitAddon.proposeDimensions();
                        if (dimensions && dimensions.cols && dimensions.rows) {
                            tabInfo.lastDimensions = {cols: dimensions.cols, rows: dimensions.rows};
                        }
                    } catch (e) {
                        console.error('Error resizing log terminal:', e);
                    }
                }
                tabInfo.resizeTimeout = null;
            }, 100);
        });

        resizeObserver.observe($terminalContainer[0]);
        tabInfo.resizeObserver = resizeObserver;

        return terminal;
    }

    function activateLogTab(tabId, shouldReconnect = false) {
        const tabInfo = logsTabsMap.get(tabId);
        if (!tabInfo) return;

        if (activeLogTabId && activeLogTabId !== tabId) {
            const previousActiveTab = logsTabsMap.get(activeLogTabId);
            if (previousActiveTab && previousActiveTab.socket &&
                previousActiveTab.socket.readyState === WebSocket.OPEN &&
                !previousActiveTab.sessionTimeout) {
                scheduleInactiveLogTabTimeout(activeLogTabId);
            }
        }

        activateLogTabUI(tabId);

        // Clear any pending timeout for the newly activated tab
        if (tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
            tabInfo.sessionTimeout = null;
        }

        // Remove from inactive tabs map
        if (inactiveTabsMap.has(tabId)) {
            inactiveTabsMap.delete(tabId);
        }

        // Handle terminal initialization or reconnection
        if (!tabInfo.terminal) {
            const logElementId = `log-view-${tabInfo.iref}-${tabInfo.cref}`;
            isInitializingLogView = true;

            const terminal = initializeLogView(tabId, logElementId, tabInfo);

            if (terminal) {
                connectLogWebSocket(tabId, tabInfo.iref, tabInfo.cref);
                isInitializingLogView = false;
            }
        } else if (shouldReconnect || !tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) {
            // Only reconnect if socket is closed, or forcing a reconnect
            if (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) {
                if (tabInfo.terminal) {
                    tabInfo.terminal.writeln('\x1b[33mConnecting...\x1b[0m');
                }
            }

            // If there's an active connection but forcing a reconnect
            if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN && shouldReconnect) {
                tabInfo.socket.close();
            }

            // Only connect if needed
            if (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN || shouldReconnect) {
                connectLogWebSocket(tabId, tabInfo.iref, tabInfo.cref);
            }
        }

        // Fit terminal to container
        if (tabInfo.terminal && tabInfo.fitAddon) {
            setTimeout(() => {
                try {
                    tabInfo.fitAddon.fit();
                } catch (e) {
                    console.error('Error fitting terminal on activation:', e);
                }
            }, 50);
        }

        activeLogTabId = tabId;
    }

    function activateLogTabUI(tabId) {
        // Deactivate all tabs
        $("#logs-tabs li button")
            .removeClass("text-blue-600 border-blue-600 active dark:text-blue-500 dark:border-blue-500")
            .addClass("text-gray-500 border-transparent hover:text-gray-600 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300");

        $("#logs-content > div").addClass("hidden");

        const $tabIdBtn = $(`#${tabId}-btn`);

        // Activate selected tab
        $tabIdBtn
            .removeClass("text-gray-500 border-transparent hover:text-gray-600 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300")
            .addClass("text-blue-600 border-blue-600 active dark:text-blue-500 dark:border-blue-500");

        $(`#${tabId.replace("log-tab", "log-content")}`).removeClass("hidden");

        const $tabsContainer = $('#logs-tabs-container');
        const $tabButton = $tabIdBtn;

        if ($tabButton.length && $tabsContainer.length) {
            const tabPos = $tabButton.position().left;
            const tabWidth = $tabButton.outerWidth();
            const containerWidth = $tabsContainer.width();
            const scrollLeft = $tabsContainer.scrollLeft();

            // Center the tab
            if (tabPos < 20 || tabPos + tabWidth > containerWidth - 20) {
                $tabsContainer.animate({
                    scrollLeft: scrollLeft + tabPos - (containerWidth / 2) + (tabWidth / 2)
                }, 200);
            }
        }

        activeLogTabId = tabId;

        setTimeout(checkTabsScroll, 250);
    }

    function connectLogWebSocket(tabId, iref, cref) {
        const tabInfo = logsTabsMap.get(tabId);
        if (!tabInfo || !tabInfo.terminal) return;

        // Cancel any pending connection attempts
        if (tabInfo.pendingConnection) {
            clearTimeout(tabInfo.pendingConnection);
            tabInfo.pendingConnection = null;
        }

        // Cancel any pending session timeouts
        if (tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
            tabInfo.sessionTimeout = null;
        }

        // If there's an existing socket, clean it up
        if (tabInfo.socket) {
            try {
                tabInfo.socket.close();
            } catch (e) {
                console.error('Error closing existing socket:', e);
            }
        }

        tabInfo.pendingConnection = setTimeout(() => {
            try {
                const socket = new WebSocket(`/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}/logs/${iref}/${cref}`);
                tabInfo.socket = socket;

                socket.onopen = () => {
                    if (tabInfo.tailLines) {
                        socket.send(JSON.stringify({
                            'tail_lines': tabInfo.tailLines
                        }));
                    }

                    tabInfo.terminal.writeln('\x1b[32mConnected\x1b[0m');
                };

                socket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.log !== undefined) {
                            const logLine = data.log;

                            // Always store the full log content with timestamps
                            tabInfo.logContent += logLine + '\n';

                            // Display according to timestamp preference
                            if (tabInfo.showTimestamps) {
                                tabInfo.terminal.writeln(logLine);
                            } else {
                                tabInfo.terminal.writeln(stripTimestamp(logLine));
                            }

                            if (tabInfo.autoScrollEnabled) {
                                setTimeout(() => {
                                    if (tabInfo.terminal) {
                                        tabInfo.terminal.scrollToBottom();
                                    }
                                }, 10);
                            }
                        } else if (data.status === 'error') {
                            tabInfo.terminal.writeln(`\x1b[31mError: ${data.message}\x1b[0m`);
                        }
                    } catch (e) {
                        if (typeof event.data === 'string') {
                            // Store the raw data
                            tabInfo.logContent += event.data;

                            // Display according to timestamp preference
                            if (tabInfo.showTimestamps) {
                                tabInfo.terminal.write(event.data);
                            } else {
                                tabInfo.terminal.write(stripTimestamp(event.data));
                            }

                            if (tabInfo.autoScrollEnabled) {
                                tabInfo.terminal.scrollToBottom();
                            }
                        }
                    }
                };

                socket.onclose = (event) => {
                    if (event.wasClean === false) {
                        tabInfo.terminal.writeln('\x1b[33mConnection closed\x1b[0m');
                    }

                    inactiveTabsMap.set(tabId, true);
                    tabInfo.socket = null;
                };

                socket.onerror = (error) => {
                    tabInfo.terminal.writeln(`\x1b[31mWebSocket error\x1b[0m`);
                    inactiveTabsMap.set(tabId, true);
                };

            } catch (e) {
                tabInfo.pendingConnection = null;
                tabInfo.terminal.writeln(`\x1b[31mFailed to connect to logs: ${e.message}\x1b[0m`);
                inactiveTabsMap.set(tabId, true);
            }
        }, 500);
    }

    function scheduleInactiveLogTabTimeout(tabId) {
        const tabInfo = logsTabsMap.get(tabId);
        if (!tabInfo) return;

        // Clear any existing timeout
        if (tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
            tabInfo.sessionTimeout = null;
        }

        // Only set timeout if the connection is active
        if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
            tabInfo.sessionTimeout = setTimeout(() => {
                const isModalVisible = logsModal && logsModal.isVisible && logsModal.isVisible();

                // Close the connection if:
                // 1. Modal is not visible OR
                // 2. Tab is not the active tab AND modal is visible

                if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN &&
                    (!isModalVisible || (isModalVisible && tabId !== activeLogTabId))) {

                    inactiveTabsMap.set(tabId, true);

                    tabInfo.socket.close();
                    tabInfo.socket = null;

                    if (tabInfo.terminal) {
                        tabInfo.terminal.clear();
                        tabInfo.logContent = '';
                        tabInfo.terminal.writeln('\x1b[33mConnection closed due to inactivity\x1b[0m');
                    }
                }
                tabInfo.sessionTimeout = null;
            }, LOG_SESSION_TIMEOUT);
        }
    }

    window.addLogsTab = function addLogsTab(name, iref, cref) {
        const tabId = `log-tab-${iref}-${cref}`;
        const contentId = `log-content-${iref}-${cref}`;

        if (logsTabsMap.has(tabId)) {
            activateLogTab(tabId, false);

            const tabInfo = logsTabsMap.get(tabId);
            if (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) {
                if (tabInfo.terminal) {
                    tabInfo.terminal.writeln('\x1b[33mConnecting...\x1b[0m');
                    connectLogWebSocket(tabId, iref, cref);
                }
            }

            logsModal.show();
            return;
        }

        logsTabsMap.set(tabId, {
            name,
            iref,
            cref,
            terminal: null,
            fitAddon: null,
            socket: null,
            pendingConnection: null,
            sessionTimeout: null,
            autoScrollEnabled: true,
            showTimestamps: false, // Timestamps off by default
            tailLines: 100,
            logContent: ''
        });

        const tabElement = $('<li/>', {
            class: 'mr-1',
            role: 'presentation'
        }).append(
            $('<button/>', {
                id: `${tabId}-btn`,
                class: 'inline-block py-2 px-3 border-b-2 rounded-t-lg',
                'data-tabs-target': `#${contentId}`,
                role: 'tab',
                text: name
            }).append(
                $('<span/>', {
                    class: 'ml-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
                    html: '&times;',
                    title: 'Close tab',
                    click: function (e) {
                        e.stopPropagation();
                        removeLogsTab(iref, cref);
                    }
                })
            ).click(function () {
                activateLogTab(tabId, false);
            })
        );

        const contentElement = $('<div/>', {
            id: contentId,
            class: 'hidden h-full',
            role: 'tabpanel',
            tabindex: '0',
        }).append(
            $('<div/>', {
                class: 'log-view-container h-full',
                id: `log-view-${iref}-${cref}`
            })
        );

        $('#logs-tabs').append(tabElement);
        $('#logs-content').append(contentElement);

        activateLogTab(tabId, false);
        logsModal.show();
    };

    function removeLogsTab(iref, cref) {
        const tabId = `log-tab-${iref}-${cref}`;

        if (!logsTabsMap.has(tabId))
            return;

        const tabInfo = logsTabsMap.get(tabId);

        if (tabInfo.pendingConnection) {
            clearTimeout(tabInfo.pendingConnection);
        }

        if (tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
        }

        if (tabInfo.resizeObserver) {
            tabInfo.resizeObserver.disconnect();
        }

        if (tabInfo.socket) {
            try {
                tabInfo.socket.close();
            } catch (e) {
                console.error('Error closing socket:', e);
            }
        }

        if (tabInfo.terminal) {
            try {
                tabInfo.terminal.dispose();
            } catch (error) {
                console.error(`Error disposing terminal: ${error.message}`);
            }
        }

        $(`#${tabId}-btn`).parent().remove();
        $(`#${tabId.replace("log-tab", "log-content")}`).remove();

        logsTabsMap.delete(tabId);
        inactiveTabsMap.delete(tabId);

        if (logsTabsMap.size > 0) {
            const nextTabId = Array.from(logsTabsMap.keys())[0];
            activateLogTab(nextTabId);
        } else {
            activeLogTabId = null;
            logsModal.hide();
        }
    }

    function closeAllLogViews() {
        logsTabsMap.forEach((tabInfo, tabId) => {
            if (tabInfo.sessionTimeout) {
                clearTimeout(tabInfo.sessionTimeout);
            }

            if (tabInfo.pendingConnection) {
                clearTimeout(tabInfo.pendingConnection);
            }

            if (tabInfo.resizeObserver) {
                tabInfo.resizeObserver.disconnect();
            }

            if (tabInfo.socket) {
                try {
                    tabInfo.socket.close();
                } catch (e) {
                    console.error('Error closing socket:', e);
                }
            }

            if (tabInfo.terminal) {
                try {
                    tabInfo.terminal.dispose();
                } catch (error) {
                    console.error(`Error disposing terminal: ${error.message}`);
                }
            }
        });

        logsTabsMap.clear();
        inactiveTabsMap.clear();
        activeLogTabId = null;
    }

    function resizeAllLogTerminals() {
        logsTabsMap.forEach((tabInfo, tabId) => {
            if (tabInfo.terminal && tabInfo.fitAddon) {
                try {
                    const fitAddon = tabInfo.fitAddon;
                    fitAddon.fit();
                    const dimensions = fitAddon.proposeDimensions();

                    if (dimensions && dimensions.cols && dimensions.rows) {
                        if (!tabInfo.lastDimensions ||
                            tabInfo.lastDimensions.cols !== dimensions.cols ||
                            tabInfo.lastDimensions.rows !== dimensions.rows) {

                            tabInfo.lastDimensions = {cols: dimensions.cols, rows: dimensions.rows};
                        }
                    }
                } catch (e) {
                    console.error('Error resizing log terminal:', e);
                }
            }
        });
    }

    let logsWindowResizeTimeout;

    $(window).on('resize', function () {
        if (logsWindowResizeTimeout) {
            clearTimeout(logsWindowResizeTimeout);
        }

        logsWindowResizeTimeout = setTimeout(() => {
            resizeAllLogTerminals();
            logsWindowResizeTimeout = null;
        }, 100);
    });

    $(window).on('beforeunload', function () {
        closeAllLogViews();
    });

    $('#logs-modal-close').on('click', function () {
        logsModal.hide();
    });

});
