window.onload = () => {
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
    const options = {
        defaultTabId: 'main',
        activeClasses:
            'dark:bg-primary-700 bg-primary-600 dark:text-white text-white dark:text-gray-200',
        inactiveClasses:
            'dark:bg-gray-700 dark:hover:bg-gray-600 hover:bg-gray-300 bg-gray-200',
        onShow: (e) => {
            let activeTabId = e._activeTab.id;
            console.log(activeTabId);
            loadImageList();
        },
    };
    const instanceOptions = {
        id: 'containers-tab',
        override: true
    };
    const tabs = new Tabs(tabsElement, tabElements, options, instanceOptions);
}

function loadImageList() {
    console.log('Load images');
}

function loadRegistryList() {
    console.log('Load registries');
}

function loadSecretList() {
    console.log('Load secrets');
}
