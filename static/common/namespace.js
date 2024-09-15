let nsModal;
let $nsModal = $('#namespace-modal');
let nsModalClosable = true;

let popupModal;
let $popupModal = $('#popup-modal');

let alertModal;
let $alertModal = $('#alert-modal');

let roleDropdown;

let $createNS = $('#create-namespace');
let $namespaceSettings = $('#namespace-settings');
let $namespaceLlist = $('#namespace-list');

let $nsModalTitle = $('#ns-modal-title');
let $nsModalName = $('#ns-modal-name');
let $setAsDefault = $('#set-as-default');
let $nsUserList = $('#ns-user-list');

let $sharingSpinner = $('#sharing-spinner');
let $selectedSvg = $('#role-selected-svg');
let $userSearch = $('#user-search');
let $userSearchDropdown = $('#user-search-dropdown');
let $userSearchResults = $('#user-search-results');
let userSearchSocket = null;
let $nsSubmitButton = $('#ns-submit-button');

let roleManager = $('#role-manager');
let roleViewer = $('#role-viewer');
let roleTransferOwner = $('#role-transfer-ownership');
let roleRemoveUser = $('#role-remove-user');

let nsUsers = [];
let selectedUser = {};
let nsOwner = {};
let userSelf = {};
let createNS = true;

loadNamespace();
loadAllNamespaces();
getSelf((user) => {
    userSelf = {
        ...user, 'name': user.first_name + ' ' + user.last_name, 'role': 'owner'
    }
});
window.addEventListener('load', function () {
    nsModal = FlowbiteInstances.getInstance('Modal', 'namespace-modal');
    nsModal._options.onShow = () => {
        setTimeout(() => {
            $nsModal.addClass('show');
        }, 10);
        connectSearch();
        $nsSubmitButton.prop('disabled', false);
    }
    nsModal._options.onHide = () => {
        $nsModal.removeClass('show');
        showShareSpinner(false);
        connectSearch(false);
        roleDropdown?.destroyAndRemoveInstance();
        $nsModalName.val('');
        $userSearch.val('');
        $nsUserList.empty();
        $setAsDefault.prop('checked', false);
        selectedUser = {};
        nsOwner = {};
        nsUsers = [];
    }
    nsModal._options.closable = false;

    popupModal = FlowbiteInstances.getInstance('Modal', 'popup-modal');
    popupModal._options.onShow = () => {
        setTimeout(() => {
            $popupModal.addClass('show');
        }, 10);
        nsModalClosable = false;
        roleDropdown?.hide();
    }
    popupModal._options.onHide = () => {
        $popupModal.removeClass('show');
        setTimeout(() => {
            nsModalClosable = true;
        }, 50);
    }

    alertModal = FlowbiteInstances.getInstance('Modal', 'alert-modal');
    alertModal._options.onShow = function () {
        setTimeout(() => {
            $alertModal.addClass('show');
        }, 10);
    };
    alertModal._options.onHide = function () {
        $alertModal.removeClass('show');
    }
});

function loadNamespace(nsid = '', apply = true, callback = null) {
    let currentNS = window.localStorage.getItem('nsid');
    if (!nsid && !currentNS) nsid = 'default';
    if (callback) showShareSpinner();
    $.ajax({
        url: '/api/namespace/' + (nsid ? nsid : currentNS),
        type: 'GET',
        success: (resp) => {
            if (resp.status === 'success') {
                nsUsers = resp.users;
                nsOwner = resp.owner;
                if (apply) {
                    $('#dropdown-ns-button').text(resp.name);
                    localStorage.setItem('nsid', resp.nsid);
                    window.namespace = resp.nsid;
                }
                if (!callback) return;
                callback(resp);
            } else if (resp.status === 'error') {
                loadNamespace('default', apply, callback);
            }
        },
    });
}

$createNS.on('click', () => {
    createNS = true;
    $nsModalTitle.text('Create Namespace');
    $nsSubmitButton.text('Create');
    roleTransferOwner.addClass('hidden');
    $nsUserList.append(createUserListItem(userSelf));
});
$namespaceSettings.on('click', () => {
    createNS = false;
    $nsModalTitle.text('Edit Namespace');
    loadNamespace(window.namespace, false, (resp) => {
        $nsModalName.val(resp.name);
        $nsSubmitButton.text('Save');
        roleTransferOwner.removeClass('hidden');
        $nsUserList.append(createUserListItem({...resp.owner, 'role': 'owner'}));
        resp.users.forEach((user) => {
            $nsUserList.append(createUserListItem(user));
        });
        $setAsDefault.prop('checked', resp.default);
        showShareSpinner(false);
    });
});
$userSearch.on('input', () => {
    handleSearchUsers()
});
roleManager.on('click', () => {
    handleChangeRole(selectedUser, 'manager')
});
roleViewer.on('click', () => {
    handleChangeRole(selectedUser, 'viewer')
});
roleTransferOwner.on('click', () => {
    handleChangeRole(selectedUser, 'owner');
});
roleRemoveUser.on('click', () => {
    $(`#ns-list-user-${selectedUser.username}`).remove();
    nsUsers = nsUsers.filter(u => u.username !== selectedUser.username);
    roleDropdown.hide();
    selectedUser = {};
});
$nsSubmitButton.on('click', () => {
    let nsName = $nsModalName.val();
    if (nsName.length === 0) {
        Alert('Namespace name cannot be empty');
        return;
    }
    let data = {
        'name': nsName.trim(),
        'users': nsUsers,
        'default': $setAsDefault.is(':checked')
    };

    if (!createNS) {
        data['owner'] = {...nsOwner};
    }

    showShareSpinner();

    $nsSubmitButton.prop('disabled', true);

    $.ajax({
        url: '/api/namespace' + (createNS ? '' : '/' + window.namespace),
        type: createNS ? 'POST': 'PATCH',
        data: {
            'csrfmiddlewaretoken': document.querySelector('input[name="csrf-token"]').value,
            'data': JSON.stringify(data),
        },
        success: (resp) => {
            $nsSubmitButton.prop('disabled', false);
            if (resp.status === 'success') {
                nsModal.hide();
                Confirm('Namespace created. Do you want to switch to the new namespace?', (ok) => {
                    if (ok) {
                        window.localStorage.setItem('nsid', resp.nsid);
                        window.location.reload();
                    }
                });
                loadAllNamespaces();
            } else {
                Alert('An error occurred while creating the namespace. Please try again.');
            }
        },
        error: () => {
            Alert('Something went wrong on our end. This has been logged and we are working on it.');
        }
    });
});


function handleChangeRole(user, newRole = '') {
    selectedUser = {...user};

    if (newRole === '') {
        // Adjusts the role of the user in the dropdown
        $selectedSvg.prependTo(`#role-${user.role}`);
        roleDropdown.show(); // show the dropdown when they click on the role
    } else if (newRole === 'owner') {
        // Transfer ownership
        Confirm(`Are you sure you want to transfer ownership to ${user.name.split(' ')[0]}?`, (ok) => {
            if (!ok) return;

            let oldOwner = {...nsOwner, 'role': 'manager'};
            let newOwner = {...selectedUser, 'role': 'owner'};

            if (oldOwner.username === newOwner.username) return;

            // Remove the old owner and new owner from the list
            $(`#ns-list-user-${oldOwner.username}`).remove();
            $(`#ns-list-user-${newOwner.username}`).remove();

            // Recreate the list items for both old and new owners
            let $newOwner = createUserListItem(newOwner);
            let $oldOwner = createUserListItem(oldOwner);

            // Add the old owner and new owner to the list
            $nsUserList.prepend($oldOwner);
            $nsUserList.prepend($newOwner);

            // Update the owner reference
            nsOwner = newOwner;

            // Remove the new owner from the nsUsers list
            nsUsers = nsUsers.filter(u => u.username !== newOwner.username);
            nsUsers.push(oldOwner);
        });
    } else {
        // Handle role change
        let nsUser = nsUsers.find(u => u.username === user.username);    // get the user reference from nsUsers
        $selectedSvg.prependTo(`#role-${newRole}`);                      // update the checkmark
        // When they change the role in dropdown, update the role in the list
        roleDropdown.hide();
        $(`#role-dropdown-${nsUser.username} > span`).text(capitalize(newRole));
        nsUser.role = newRole;
    }
}

function createUserListItem(user) {
    if ($(`#ns-list-user-${user.username}`).length) return;

    let $listItem = $('<li/>', {
        id: `ns-list-user-${user.username}`, class: 'flex py-2 px-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700'
    });
    let $innerDiv = $('<div/>', {
        class: 'flex items-center justify-between w-full'
    });
    let $flexContainer = $('<div/>', {
        class: 'flex items-center justify-between'
    });
    let $avatar = $('<img/>', {
        class: 'w-10 h-10 rounded-full ml-0.5', src: user.avatar, alt: user.name
    });
    let $textContainer = $('<div/>', {
        class: 'ml-2.5 py-0.5'
    });
    let $name = $('<span/>', {
        class: 'text-black dark:text-white', text: user.name
    });
    let $email = $('<p/>', {
        class: 'text-xs font-normal text-gray-500 dark:text-gray-300', text: user.email
    });
    $textContainer.append($name, $email);
    $flexContainer.append($avatar, $textContainer);

    let $roleButton = $('<div/>', {
        id: `role-dropdown-${user.username}`,
        class: 'text-gray-500 dark:text-gray-300 bg-transparent font-medium rounded text-xs px-2.5 py-2 text-center ' + 'inline-flex items-center focus:outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-100' + (user.role !== 'owner' ? ' dark:hover:bg-gray-800 hover:bg-gray-3000' : ''),
    });

    $roleButton.off('click');

    if (user.role !== 'owner') {
        // Add role change event listener to the role button
        $roleButton.on('click', () => {

            if (selectedUser.username === user.username) return;

            let targetEl = document.getElementById(`role-dropdown`);
            let triggerEl = document.getElementById(`role-dropdown-${user.username}`);

            if (roleDropdown) {
                if (roleDropdown.isVisible()) {
                    roleDropdown._targetEl.classList.add('hidden'); // Hide the dropdown if it's already visible for the same user
                    return;
                }
                roleDropdown.destroyAndRemoveInstance(); // Destroy the dropdown if it's different user
            }

            // Create a new dropdown for the user
            roleDropdown = new Dropdown(targetEl, triggerEl, {
                placement: 'right-start',
            });

            handleChangeRole(user);
        });
    }

    let $roleText = $('<span/>', {
        class: 'text-gray-500 dark:text-gray-300', text: capitalize(user.role)
    });

    if (user.role === "owner") {
        $roleButton.append($roleText);
    } else {
        let $svg = $('<div/>').html(`
        <svg class="w-2.5 h-2.5 ms-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 10 6">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 4 4 4-4"></path>
        </svg>
        `);
        $roleButton.append($roleText, $svg);
    }

    $innerDiv.append($flexContainer, $roleButton);
    $listItem.append($innerDiv);
    return $listItem;
}

function handleAddUser(user) {
    if (user.username === nsOwner.username) // If they are the owner, skip
        return;
    if (nsUsers.find(u => u.username === user.username)) // If user is already in the list, skip
        return;
    nsUsers.push(user); // Add user to the list
    $nsUserList.append(createUserListItem(user));
}

function handleSearchUsers() {
    let value = $userSearch.val();
    if (value.length === 0) {
        $userSearchDropdown.addClass("hidden");
    } else {
        if (userSearchSocket) {
            userSearchSocket.send(value);
        } else {
            Alert("Session expired, try refreshing page. If issue persists, contact support.");
        }
    }

}

function createNSListItem(name, owner, nsid) {
    const listItem = $('<li></li>')
        .addClass('flex p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-600')
        .on('click', function () {
            window.localStorage.setItem('nsid', nsid);
            window.location.reload();
        });

    const textSmDiv = $('<div></div>')
        .addClass('text-sm');

    const mainText = $('<div></div>')
        .text(name + (nsid === localStorage.getItem('nsid') ? ' (Current)' : ''));

    const subText = $('<div></div>')
        .addClass('text-xs font-normal text-gray-500 dark:text-gray-300')
        .text(owner);

    textSmDiv.append(mainText);
    textSmDiv.append(subText);
    listItem.append(textSmDiv);

    return listItem;
}

function createSearchUserListItem(username, name, email, avatar, roundedT, roundedB) {
    return $('<li>', {
        class: ('flex items-center p-1 hover:bg-gray-300 dark:hover:bg-gray-600') + (roundedT ? ' rounded-t-lg' : '') + (roundedB ? ' rounded-b-lg' : ''),
        click: () => {
            $userSearchDropdown.addClass("hidden");
            $userSearch.val('');
            handleAddUser({username, name, email, avatar, 'role': 'viewer'});
        }
    }).append($('<img>', {class: 'w-10 h-10 rounded-full ml-1', src: avatar, alt: name})).append($('<div>', {
        class: 'ml-2.5 items-center'
    }).append($('<div>', {
        class: 'text-black text-sm dark:text-white align-middle cursor-default mr-1', text: name
    })).append($('<div>', {
        class: 'text-xs font-normal text-gray-500 dark:text-gray-300 cursor-default', text: email
    })));
}

function connectSearch(connect = true) {
    if (connect && !userSearchSocket) {
        try {
            userSearchSocket = new WebSocket('/api/user-search');
            userSearchSocket.onopen = () => {
                userSearchSocket.onmessage = handleSocketMessage;
                showShareSpinner(false);
            };
            userSearchSocket.onclose = () => {
                userSearchSocket = null;
            };
        } catch (e) {
            console.log(e);
        }

    } else if (userSearchSocket && !connect) {
        userSearchSocket.close();
        userSearchSocket = null;
    }
}

function handleSocketMessage(event) {
    const data = JSON.parse(event.data);
    if (data.users) {
        if (data.users.length === 0) {
            $userSearchDropdown.addClass("hidden");
            return;
        }
        $userSearchResults.empty();
        data.users.forEach((user, index) => {
            let roundedT = index === 0;
            let roundedB = index === data.users.length - 1;
            $userSearchResults.append(createSearchUserListItem(user.username, user.name, user.email, user.avatar, roundedT, roundedB));
        });
        $userSearchDropdown.removeClass("hidden");
    }
}

function getSelf(callback) {
    $.ajax({
        url: '/api/user',
        type: 'GET',
        success: (resp) => {
            if (resp.status === 'success') {
                callback(resp);
            } else {
                Alert('Session expired. Please try refreshing page. If issue persists, contact support.');
            }
        }
    });
}

function capitalize(string) {
    return string[0].toUpperCase() + string.slice(1);
}

function Confirm(message, callback, options = {'yes': 'Confirm', 'no': 'Cancel', 'icon': 'info'}) {
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

function Alert(message, callback = null, options = {'ok': 'OK', 'icon': 'info'}) {
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

function showShareSpinner(show = true) {
    if (show) $sharingSpinner.removeClass('hidden'); else $sharingSpinner.addClass('hidden');
}

function loadAllNamespaces() {
    $.ajax({
        url: '/api/namespace',
        type: 'GET',
        success: (resp) => {
            if (resp.status === 'success') {
                $namespaceLlist.empty();
                resp.namespaces.forEach((ns) => {
                    $namespaceLlist.append(createNSListItem(ns.name, ns.owner.name, ns.nsid));
                });
            }
        }
    });
}

$(document).keydown((event) => {
    if (event.key === "Escape" || event.key === "Esc") {
        if (nsModalClosable) nsModal.hide();
    }
});
