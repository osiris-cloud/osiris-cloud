window.addEventListener('load', function () {
    let isInitializingTerminal = false; // Flag to prevent concurrent connections
    let activeTabId = null;
    let consoleTabsMap = new Map(); // {name, iref, cref, terminal, fitAddon, socket, pendingConnection, sessionTimeout, resizeObserver, resizeTimeout}
    const SESSION_TIMEOUT = 60000;

    const consoleModalEl = document.getElementById('console-modal');
    const options = {
        closable: false,
        onHide: () => {
            pauseAllTerminals();
        },
        onShow: () => {
            if (isInitializingTerminal)
                return;

            setTimeout(() => {
                if (activeTabId && consoleTabsMap.has(activeTabId)) {
                    activateTab(activeTabId);
                } else if (consoleTabsMap.size > 0) {
                    const firstTabId = Array.from(consoleTabsMap.keys())[0];
                    activateTab(firstTabId);
                }
            }, 200);
        }
    };
    const instanceOptions = {
        id: 'console-modal',
        override: true,
    };
    let consoleModal = new Modal(consoleModalEl, options, instanceOptions);

    // Function to handle terminal resize
    function handleTerminalResize(tabInfo) {
        if (!tabInfo || !tabInfo.terminal || !tabInfo.fitAddon) return;

        try {
            tabInfo.fitAddon.fit();
            const dimensions = tabInfo.fitAddon.proposeDimensions();

            if (dimensions && dimensions.cols && dimensions.rows &&
                (!tabInfo.lastDimensions ||
                    tabInfo.lastDimensions.cols !== dimensions.cols ||
                    tabInfo.lastDimensions.rows !== dimensions.rows)) {

                tabInfo.lastDimensions = {cols: dimensions.cols, rows: dimensions.rows};

                if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
                    tabInfo.socket.send(`resize:${dimensions.cols}:${dimensions.rows}`);
                }
            }
        } catch (e) {
            console.error('Error during terminal resize:', e);
        }
    }

    // Helper function to send terminal dimensions
    function sendTerminalDimensions(tabInfo) {
        if (!tabInfo || !tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) return;

        if (tabInfo.lastDimensions) {
            tabInfo.socket.send(`resize:${tabInfo.lastDimensions.cols}:${tabInfo.lastDimensions.rows}`);
        } else if (tabInfo.fitAddon) {
            try {
                tabInfo.fitAddon.fit();
                const dimensions = tabInfo.fitAddon.proposeDimensions();
                if (dimensions && dimensions.cols && dimensions.rows) {
                    tabInfo.lastDimensions = {cols: dimensions.cols, rows: dimensions.rows};
                    tabInfo.socket.send(`resize:${dimensions.cols}:${dimensions.rows}`);
                }
            } catch (e) {
                console.error('Error calculating terminal dimensions:', e);
            }
        }
    }

    function initializeTerminal(tabId, terminalElementId, tabInfo) {
        const $terminalElement = $(`#${terminalElementId}`);
        if ($terminalElement.length === 0) return null;

        $terminalElement.empty();

        const initialRows = 24;
        const initialCols = 120;

        const fitAddon = new FitAddon();

        const terminal = new Terminal({
            cursorBlink: true,
            fontFamily: 'monospace',
            cursorWidth: 1,
            cursorStyle: 'bar',
            fontSize: 14,
            rows: initialRows,
            cols: initialCols,
            theme: {
                background: '#1a1a1a',
                foreground: '#f0f0f0'
            },
            allowTransparency: true,
        });

        tabInfo.fitAddon = fitAddon;
        tabInfo.terminal = terminal;
        tabInfo.lastDimensions = {cols: initialCols, rows: initialRows};
        tabInfo.isNewTerminal = true;

        terminal.loadAddon(fitAddon);
        terminal.loadAddon(new ClipboardAddon());

        try {
            const webglAddon = new WebglAddon();
            terminal.loadAddon(webglAddon);
        } catch (e) {
            console.warn('WebGL not supported, falling back to canvas renderer', e);
        }

        terminal.loadAddon(new WebLinksAddon());
        terminal.open($terminalElement[0]);

        try {
            fitAddon.fit();
            // Store the initial dimensions after fitting
            const dimensions = fitAddon.proposeDimensions();
            if (dimensions && dimensions.cols && dimensions.rows) {
                tabInfo.lastDimensions = {cols: dimensions.cols, rows: dimensions.rows};
            }
        } catch (e) {
            console.error('Error fitting terminal:', e);
        }

        return terminal;
    }

    function activateTab(tabId, shouldReconnect = true) {
        // If there was a previously active tab, set a timeout to close its connection if it stays inactive
        if (activeTabId && activeTabId !== tabId && consoleTabsMap.has(activeTabId)) {
            scheduleInactiveTabTimeout(activeTabId);
        }

        // Clear any pending timeout for the tab we're activating
        const tabInfo = consoleTabsMap.get(tabId);
        if (tabInfo && tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
            tabInfo.sessionTimeout = null;
        }

        activateTabUI(tabId);

        if (!tabInfo) return;

        if (!tabInfo.terminal) {
            const terminalElementId = `terminal-${tabInfo.iref}-${tabInfo.cref}`;
            isInitializingTerminal = true;

            const terminal = initializeTerminal(tabId, terminalElementId, tabInfo);

            if (terminal) {
                // After initialization, resize the terminal again to ensure accurate dimensions
                setTimeout(() => {
                    try {
                        if (tabInfo.fitAddon) {
                            tabInfo.fitAddon.fit();
                            const dimensions = tabInfo.fitAddon.proposeDimensions();
                            if (dimensions && dimensions.cols && dimensions.rows) {
                                tabInfo.lastDimensions = {cols: dimensions.cols, rows: dimensions.rows};
                            }
                        }
                    } catch (e) {
                        console.error('Error resizing terminal after initialization:', e);
                    }
                }, 0);

                terminal.write('\x1b[33mConnecting... \x1b[0m\r\n');
                connectTerminalWebSocket(tabId, tabInfo.iref, tabInfo.cref);
                isInitializingTerminal = false;
            }
        } else if (shouldReconnect && (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN)) {
            if (tabInfo.hadSocketBefore) {
                tabInfo.terminal.write('\x1b[33mReconnecting... \x1b[0m\r\n');
            }
            connectTerminalWebSocket(tabId, tabInfo.iref, tabInfo.cref);
        }
    }

    function scheduleInactiveTabTimeout(tabId) {
        const tabInfo = consoleTabsMap.get(tabId);
        if (!tabInfo) return;

        if (tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
            tabInfo.sessionTimeout = null;
        }

        // Only set timeout if the connection is active
        if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
            tabInfo.sessionTimeout = setTimeout(() => {
                if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
                    tabInfo.socket.close(1000, 'inactivity');
                    if (tabInfo.terminal) {
                        tabInfo.terminal.writeln('\x1b[33mSession closed due to inactivity\x1b[0m');
                    }
                }
                tabInfo.sessionTimeout = null;
            }, SESSION_TIMEOUT);
        }
    }

    function activateTabUI(tabId) {
        // Deactivate all tabs
        $("#console-tabs li button")
            .removeClass("text-blue-600 border-blue-600 active dark:text-blue-500 dark:border-blue-500")
            .addClass("text-gray-500 border-transparent hover:text-gray-600 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300");

        $("#console-content > div").addClass("hidden");

        // Activate selected tab
        $(`#${tabId}-btn`)
            .removeClass("text-gray-500 border-transparent hover:text-gray-600 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300")
            .addClass("text-blue-600 border-blue-600 active dark:text-blue-500 dark:border-blue-500");

        $(`#${tabId.replace("tab", "content")}`).removeClass("hidden");

        activeTabId = tabId;
    }

    function connectTerminalWebSocket(tabId, iref, cref) {
        const tabInfo = consoleTabsMap.get(tabId);
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

        tabInfo.pendingConnection = setTimeout(() => {
            try {
                const socket = new WebSocket(`/api/container-apps/${currentURL.nsid}/${currentURL.resource_id}/shell/${iref}/${cref}`);

                socket.onopen = () => {
                    tabInfo.pendingConnection = null;

                    if (tabInfo.socket && tabInfo.socket !== socket) {
                        tabInfo.socket.close();
                    }

                    tabInfo.terminal.write('\x1b[32mConnected\x1b[0m\r\n');

                    tabInfo.socket = socket;
                    tabInfo.hadSocketBefore = true;

                    tabInfo.terminal.onData(data => {
                        if (socket && socket.readyState === WebSocket.OPEN) {
                            const encodedData = btoa(data); // Encode the command with Base64 before sending
                            socket.send(encodedData);
                        }
                    });

                    // Always send the resize command when connection is established
                    sendTerminalDimensions(tabInfo);
                };

                socket.onmessage = (event) => {
                    const text = event.data;
                    try {
                        if (text.startsWith('stdout:')) {
                            const encodedData = text.substring(7); // Remove 'stdout:' prefix
                            const decodedData = atob(encodedData);
                            tabInfo.terminal.write(decodedData);

                            if (!tabInfo.initialDataReceived && !tabInfo.initialResizeSent) {
                                tabInfo.initialDataReceived = true;
                                tabInfo.initialResizeSent = true;

                                setTimeout(() => {
                                    sendTerminalDimensions(tabInfo);
                                }, 100);
                            }
                            return;
                        }

                        if (text.startsWith('stderr:')) {
                            const encodedData = text.substring(7); // Remove 'stderr:' prefix
                            const decodedData = atob(encodedData);
                            tabInfo.terminal.write(decodedData);
                            return;
                        }

                        if (text.startsWith('msg:')) {
                            const message = text.substring(4); // Remove 'msg:' prefix
                            tabInfo.terminal.writeln(`\r\n\x1b[31m${message}\x1b[0m`);
                            return;
                        }

                        tabInfo.terminal.write(text);
                    } catch (e) {
                        tabInfo.terminal.write(text);
                    }
                };

                socket.onerror = (error) => {
                    tabInfo.pendingConnection = null;
                    tabInfo.terminal.writeln(`\r\n\x1b[31mConnection error\x1b[0m`);
                };

                socket.onclose = (event) => {
                    tabInfo.pendingConnection = null;

                    // Check if the close event was due to inactivity (we'll set a custom reason code)
                    const isInactivityClose = event.reason === 'inactivity';

                    // Only show "Connection closed" if it wasn't due to inactivity
                    if (!isInactivityClose) {
                        tabInfo.terminal.writeln(`\x1b[33mConnection closed${event.reason ? ': ' + event.reason : ''}\x1b[0m`);
                    }

                    if (tabInfo.socket === socket)
                        tabInfo.socket = null;
                };
            } catch (e) {
                tabInfo.pendingConnection = null;
                tabInfo.terminal.writeln(`\r\n\x1b[31mFailed to create connection: ${e.message}\x1b[0m`);
            }
        }, 500);
    }


    window.addConsoleTab = function addConsoleTab(name, iref, cref) {
        const tabId = `tab-${iref}-${cref}`;
        const contentId = `content-${iref}-${cref}`;

        if (consoleTabsMap.has(tabId)) {
            activateTab(tabId);

            const tabInfo = consoleTabsMap.get(tabId);
            if (!tabInfo.socket || tabInfo.socket.readyState !== WebSocket.OPEN) {
                if (tabInfo.terminal) {
                    if (tabInfo.hadSocketBefore) {
                        tabInfo.terminal.write('\x1b[33mReconnecting... \x1b[0m\r\n');
                    }
                    connectTerminalWebSocket(tabId, iref, cref);
                }
            }
            consoleModal.show();
            return;
        }

        consoleTabsMap.set(tabId, {
            name,
            iref,
            cref,
            terminal: null,
            fitAddon: null,
            socket: null,
            pendingConnection: null,
            sessionTimeout: null,
            lastDimensions: null,
            hadSocketBefore: false
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
                    click: function (e) {
                        e.stopPropagation();
                        removeConsoleTab(iref, cref);
                    }
                })
            ).click(function () {
                activateTab(tabId);
            })
        );

        const contentElement = $('<div/>', {
            id: contentId,
            class: 'hidden h-full',
            role: 'tabpanel',
        }).append(
            $('<div/>', {
                class: 'terminal-container h-full',
                id: `terminal-${iref}-${cref}`
            })
        );

        $('#console-tabs').append(tabElement);
        $('#console-content').append(contentElement);

        activateTab(tabId);
        consoleModal.show();
    };

    function removeConsoleTab(iref, cref) {
        const tabId = `tab-${iref}-${cref}`;

        if (!consoleTabsMap.has(tabId))
            return;

        const tabInfo = consoleTabsMap.get(tabId);

        if (tabInfo.pendingConnection) {
            clearTimeout(tabInfo.pendingConnection);
        }

        if (tabInfo.sessionTimeout) {
            clearTimeout(tabInfo.sessionTimeout);
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
        $(`#${tabId.replace("tab", "content")}`).remove();

        consoleTabsMap.delete(tabId);

        if (consoleTabsMap.size > 0) {
            const nextTabId = Array.from(consoleTabsMap.keys())[0];
            activateTab(nextTabId);
        } else {
            activeTabId = null;
            consoleModal.hide();
        }
    }

    function pauseAllTerminals() {
        consoleTabsMap.forEach((tabInfo, tabId) => {
            if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
                if (tabInfo.sessionTimeout) {
                    clearTimeout(tabInfo.sessionTimeout);
                }

                tabInfo.sessionTimeout = setTimeout(() => {
                    if (tabInfo.socket && tabInfo.socket.readyState === WebSocket.OPEN) {
                        // Mark this connection as being closed due to inactivity
                        if (tabInfo.terminal) {
                            tabInfo.terminal.writeln('\r\n\x1b[33mSession closed due to inactivity\x1b[0m');
                        }
                        tabInfo.socket.close(1000, 'inactivity');
                    }

                    tabInfo.sessionTimeout = null;
                }, SESSION_TIMEOUT);
            }
        });
    }

    function closeAllTerminals() {
        consoleTabsMap.forEach((tabInfo, tabId) => {
            if (tabInfo.sessionTimeout) {
                clearTimeout(tabInfo.sessionTimeout);
            }

            if (tabInfo.pendingConnection) {
                clearTimeout(tabInfo.pendingConnection);
            }

            if (tabInfo.socket) {
                tabInfo.socket.close();
            }

            if (tabInfo.terminal) {
                tabInfo.terminal.dispose();
            }
        });

        consoleTabsMap.clear();
        activeTabId = null;
    }

    function resizeAllTerminals() {
        consoleTabsMap.forEach((tabInfo, tabId) => {
            handleTerminalResize(tabInfo);
        });
    }

    let windowResizeTimeout;

    $(window).on('resize', function () {
        if (windowResizeTimeout) {
            clearTimeout(windowResizeTimeout);
        }

        windowResizeTimeout = setTimeout(() => {
            resizeAllTerminals();
            windowResizeTimeout = null;
        }, 100);
    });

    $(window).on('beforeunload', function () {
        closeAllTerminals();
    });
});
