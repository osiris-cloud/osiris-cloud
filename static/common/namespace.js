window.addEventListener('load', () => {
    const nsModal = FlowbiteInstances.getInstance('Modal', 'namespace-modal');
    const $nsModal = $('#namespace-modal');

    let roleDropdown;

    let nsModalClosable = true;

    const $namespaceCreate = $('#create-namespace');
    const $namespaceSettings = $('#namespace-settings');
    const $nsDelete = $('#namespace-delete');
    const $namespaceLlist = $('#namespace-list');
    const $nsListDropdown = $('#dropdown-ns-menu');
    const $nsSearch = $('#ns-search');

    const $nsModalTitle = $('#ns-modal-title');
    const $nsModalName = $('#ns-modal-name');
    const $setAsDefault = $('#set-as-default');
    const $setAsDefaultCon = $('#set-as-default-con');
    const $nsUserList = $('#ns-user-list');

    const $nsLoadSpinner = $('#ns-load-spinner');
    const $selectedSvg = $('#role-selected-svg');
    const $userSearch = $('#user-search');
    const $userSearchDropdown = $('#user-search-dropdown');
    const $userSearchResults = $('#user-search-results');
    const $nsModalSubmitButton = $('#ns-submit-button');

    let userSearchSocket = null;

    const $roleManager = $('#role-manager');
    const $roleViewer = $('#role-viewer');
    const $roleTransferOwner = $('#role-transfer-ownership');
    const $roleRemoveUser = $('#role-remove-user');

    let NSCXT = {}
    let Myself = {}
    let selectedUser = {};
    let createNS = false;
    let disableRoleDropdown = false;

    loadAllNamespaces();
    getSelf();

    window.popupModal._options.onShow = () => {
        setTimeout(() => {
            $popupModal.addClass('show');
        }, 10);
        nsModalClosable = false;
        roleDropdown?.hide();
        $nsListDropdown.addClass('hidden');
    }

    window.popupModal._options.onHide = () => {
        $popupModal.removeClass('show');
        setTimeout(() => {
            nsModalClosable = true;
        }, 50);
    }

    window.alertModal._options.onShow = function () {
        setTimeout(() => {
            $alertModal.addClass('show');
        }, 10);
        $nsListDropdown.addClass('hidden');
    };

    nsModal._options.onShow = () => {
        setTimeout(() => {
            $nsModal.addClass('show');
        }, 10);
        connectSearch();
        $nsListDropdown.addClass('hidden');
        $nsModalSubmitButton.prop('disabled', false);
    }

    nsModal._options.onHide = () => {
        $nsModal.removeClass('show');
        showNSSpinner(false);
        connectSearch(false);
        if (roleDropdown)
            roleDropdown.destroyAndRemoveInstance();
    }

    nsModal._options.closable = false;
    NSCXT = {}
    createNS = false;

    function loadNamespace(nsid = '') {
        if (!nsid)
            nsid = currentURL.nsid || localStorage.getItem('nsid');

        showNSSpinner();

        $.ajax({
            url: '/api/namespace/' + (nsid ? nsid : 'default'),
            type: 'GET',
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            contentType: 'application/json',
            success: (resp) => {
                NSCXT = resp.namespace;
                localStorage.setItem('nsid', NSCXT.nsid);
                loadNamespaceToModal()
                showNSSpinner(false);
            },
            error: (resp) => {
                Alert(resp.responseJSON.message || "Internal Server Error", () => {
                    window.location.href = `${currentURL.host}/${currentURL.app}/default`;
                }, {'ok': 'Go to Default'});
            }
        });
    }

    function clearNamespaceModal() {
        $nsModalName.val('');
        $nsModalName.attr('readonly', false);

        $setAsDefault.attr('disabled', false);
        $setAsDefaultCon.removeClass('hidden');
        $setAsDefault.prop('checked', false);

        $userSearch.val('');
        $userSearch.attr('readonly', false);
        $userSearchResults.empty();

        $nsUserList.empty();

        $nsModalSubmitButton.text('Create');
        $nsModalSubmitButton.attr('disabled', false).removeClass('disabled cursor-not-allowed');

        $roleTransferOwner.removeClass('hidden');
        disableRoleDropdown = false;

        $nsDelete.removeClass('disabled cursor-not-allowed');
        $nsDelete.attr('disabled', false);
    }

    function loadNamespaceToModal() {
        clearNamespaceModal();

        $nsModalName.val(NSCXT.name);
        $nsModalSubmitButton.text('Save');

        $nsUserList.append(createUserListItem({...NSCXT.owner, 'role': 'owner'}));

        if (NSCXT.users) {
            NSCXT.users.forEach((user) => {
                $nsUserList.append(createUserListItem(user));
            });
        }

        if (NSCXT['_role'] === 'viewer') {
            $nsModalName.attr('readonly', true);
            $userSearch.attr('readonly', true);
            disableRoleDropdown = true;
            $setAsDefaultCon.addClass('hidden');
            $nsModalSubmitButton.attr('disabled', true).addClass('disabled cursor-not-allowed');
            $nsDelete.addClass('disabled cursor-not-allowed');
            $nsDelete.attr('disabled', true);

        } else if (NSCXT['_role'] === 'manager') {
            $roleTransferOwner.addClass('hidden');
            $setAsDefaultCon.addClass('hidden');
            $nsDelete.addClass('disabled cursor-not-allowed');
            $nsDelete.attr('disabled', true);

        } else if (NSCXT['_role'] === 'owner') {
            $setAsDefault.attr('disabled', NSCXT.default);
            $setAsDefault.prop('checked', NSCXT.default);
        }

        if (createNS) {
            $roleTransferOwner.addClass('hidden');
        }
    }

    $namespaceCreate.on('click', () => {
        createNS = true;
        NSCXT = {};
        NSCXT.name = '';
        NSCXT.owner = Myself;
        NSCXT.default = false;
        NSCXT.users = [];

        $nsModalTitle.text('Create Namespace');
        $nsModalSubmitButton.text('Create');
        $roleTransferOwner.addClass('hidden');

        loadNamespaceToModal(); // Just to load the current user as owner

    });

    $namespaceSettings.on('click', false, () => {
        createNS = false;
        $nsModalTitle.text('Edit Namespace');

        loadNamespace();
    });

    $userSearch.on('input', () => {
        handleSearchUsers()
    });

    $roleManager.on('click', () => {
        handleChangeRole(selectedUser, 'manager')
    });

    $roleViewer.on('click', () => {
        handleChangeRole(selectedUser, 'viewer')
    });

    $roleTransferOwner.on('click', () => {
        handleChangeRole(selectedUser, 'owner');
    });

    $roleRemoveUser.on('click', () => {
        $(`#ns-list-user-${selectedUser.username}`).remove();
        NSCXT.users = NSCXT.users.filter(u => u.username !== selectedUser.username);
        roleDropdown.hide();
        selectedUser = {};
    });

    $nsModalSubmitButton.on('click', () => {
        let nsName = $nsModalName.val().trim();
        if (nsName.length === 0) {
            Alert('Namespace name cannot be empty');
            return;
        }

        let data = {
            'name': nsName,
            'users': NSCXT.users,
            'default': $setAsDefault.is(':checked')
        };

        if (!createNS) {
            data['owner'] = NSCXT.owner;
        }

        showNSSpinner();

        $nsModalSubmitButton.prop('disabled', true);

        $.ajax({
            url: '/api/namespace' + (createNS ? '' : '/' + currentURL.nsid),
            type: createNS ? 'PUT' : 'PATCH',
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: (resp) => {
                let ns = resp.namespace;
                $nsModalSubmitButton.prop('disabled', false);
                nsModal.hide();
                if (createNS)
                    Confirm('Namespace created. Do you want to switch it?', (ok) => {
                        if (ok) {
                            window.location.href = `${currentURL.host}/${currentURL.app}/${ns.nsid}`;
                        }
                    }, {'yes': 'Switch', 'no': 'Stay', 'icon': 'check'});
                else
                    Alert('Namespace Updated', () => {
                        NSCXT = ns;
                        $('#dropdown-ns-button').text(ns.name);
                    }, {'icon': 'check'});

                loadAllNamespaces();
                showNSSpinner(false);

            },
            error: (resp) => {
                Alert(resp.responseJSON.message || "Internal Server Error");
                $nsModalSubmitButton.prop('disabled', false);
                showNSSpinner(false);
            }
        });
    });

    $nsDelete.on('click', () => {
        Confirm(`Namespace "${$('#dropdown-ns-button').text().trim()}" and all resources within it will be deleted`, (ok) => {
            if (!ok) return;
            $.ajax({
                url: '/api/namespace/' + currentURL.nsid,
                type: 'DELETE',
                headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
                contentType: 'application/json',
                success: (resp) => {
                    Alert('Namespace Deleted', () => {
                        window.location.href = `${currentURL.host}/${currentURL.app}/default`;
                    }, {'icon': 'check'});
                },
                error: (resp) => {
                    Alert(resp.responseJSON.message || "Internal Server Error");
                }
            });
        });
    });

    function handleChangeRole(user, newRole = '') {
        if (disableRoleDropdown) return;

        selectedUser = {...user};

        if (newRole === '') {
            // Adjusts the role of the user in the dropdown
            $selectedSvg.prependTo(`#role-${user.role}`);
            roleDropdown.show(); // show the dropdown when they click on the role
        } else if (newRole === 'owner') {
            // Transfer ownership
            Confirm(`Are you sure you want to transfer ownership to ${user.first_name}?`, (ok) => {
                if (!ok) return;

                let oldOwner = {...NSCXT.owner, 'role': 'manager'};
                let newOwner = {...selectedUser, 'role': 'owner'};

                if (oldOwner.username === newOwner.username) return;

                // Remove the old owner and new owner from the list
                $(`#ns-list-user-${oldOwner.username}`).remove();
                $(`#ns-list-user-${newOwner.username}`).remove();

                // Recreate the list items for both old and new owners
                let $newOwner = createUserListItem(newOwner);
                let $oldOwner = createUserListItem(oldOwner);

                // Add the old owner and new owner to the list
                $nsUserList.prepend($oldOwner).fadeIn(300);
                $nsUserList.prepend($newOwner).fadeIn(300);

                // Update the owner reference
                NSCXT.owner = newOwner;

                // Remove the new owner from the nsUsers list
                NSCXT.users = NSCXT.users.filter(u => u.username !== newOwner.username);
                NSCXT.users.push(oldOwner);
            });

        } else {
            // Handle role change
            let nsUser = NSCXT.users.find(u => u.username === user.username);    // get the user reference from nsUsers
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
            id: `ns-list-user-${user.username}`,
            class: 'flex py-2 px-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700'
        });
        let $innerDiv = $('<div/>', {
            class: 'flex items-center justify-between w-full'
        });
        let $flexContainer = $('<div/>', {
            class: 'flex items-center justify-between'
        });
        let $avatar = $('<img/>', {
            class: 'w-10 h-10 rounded-full ml-0.5', src: user.avatar, alt: user.username
        });
        let $textContainer = $('<div/>', {
            class: 'ml-2.5 py-0.5'
        });
        let $name = $('<span/>', {
            class: 'text-black dark:text-white', text: user.first_name + ' ' + user.last_name
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
                roleDropdown = new Dropdown(targetEl, triggerEl, {placement: 'right-start'}, {id: 'role-dropdown'});

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
        if (createNS) {
            NSCXT.users = NSCXT.users || [];
            if (user.username === NSCXT.owner.username)
                return;
            if (NSCXT.users.find(u => u.username === user.username))
                return;
            NSCXT.users.push(user);

        } else {
            if (user.username === NSCXT.owner.username) // If they are the owner, skip
                return;
            if (NSCXT.users.find(u => u.username === user.username)) // If user is already in the list, skip
                return;
            NSCXT.users.push(user); // Add user to the list
        }

        $nsUserList.append(createUserListItem(user)).fadeIn(300);
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
                let url = parseURL();
                window.location.href = `/${url.app}/${nsid}`;
            });

        const textSmDiv = $('<div>')
            .addClass('text-sm');

        const mainText = $('<div>')
            .text(name + (nsid === currentURL.nsid ? ' (Current)' : ''));

        const subText = $('<div>')
            .addClass('text-xs font-normal text-gray-500 dark:text-gray-300')
            .text(owner);

        textSmDiv.append(mainText);
        textSmDiv.append(subText);
        listItem.append(textSmDiv);

        return listItem;
    }

    function createSearchUserListItem(username, first_name, last_name, email, avatar, roundedT, roundedB) {
        return $('<li>', {
            class: ('flex items-center p-1 bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600') + (roundedT ? ' rounded-t-lg' : '') + (roundedB ? ' rounded-b-lg' : ''),
            click: () => {
                $userSearchDropdown.addClass("hidden");
                $userSearch.val('');
                handleAddUser({username, first_name, last_name, email, avatar, 'role': 'viewer'});
            }
        }).append($('<img>', {class: 'w-10 h-10 rounded-full ml-1', src: avatar, alt: username})).append($('<div>', {
            class: 'ml-2.5 items-center'
        }).append($('<div>', {
            class: 'text-black text-sm dark:text-white align-middle cursor-default mr-1',
            text: first_name + ' ' + last_name
        })).append($('<div>', {
            class: 'text-xs font-normal text-gray-500 dark:text-gray-300 cursor-default', text: email
        })));
    }

    function connectSearch(connect = true) {
        if (connect && !userSearchSocket) {
            try {
                userSearchSocket = new WebSocket('/api/user/search');
                userSearchSocket.onopen = () => {
                    userSearchSocket.onmessage = handleSocketMessage;
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
                $userSearchResults.append(createSearchUserListItem(
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.email,
                    user.avatar,
                    roundedT,
                    roundedB
                ));
            });
            $userSearchDropdown.removeClass("hidden");
        }
    }

    function getSelf() {
        $.ajax({
            url: '/api/user/_self',
            data: {brief: true},
            type: 'GET',
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            contentType: 'application/json',
            success: (resp) => {
                Myself = resp.user;
            },
            error: (resp) => {
                Alert(resp.responseJSON.message || "Internal Server Error");
            },
        });
    }

    function showNSSpinner(show = true) {
        if (show) $nsLoadSpinner.removeClass('hidden'); else $nsLoadSpinner.addClass('hidden');
    }

    function loadAllNamespaces() {
        $.ajax({
            url: '/api/namespace',
            data: {brief: true},
            type: 'GET',
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            contentType: 'application/json',
            success: (resp) => {
                $namespaceLlist.empty();
                let $nsArray = [];
                resp.namespaces.forEach((ns) => {
                    let userName = ns.owner.first_name + ' ' + ns.owner.last_name;
                    if (ns.nsid === currentURL.nsid) {
                        $nsArray.unshift(createNSListItem(ns.name, userName, ns.nsid));
                        NSCXT = ns;
                        loadNamespaceToModal();
                    } else
                        $nsArray.push(createNSListItem(ns.name, userName, ns.nsid));
                });
                $namespaceLlist.append($nsArray);
            },
            error: (resp) => {
                Alert(resp.message || "Internal Server Error");
            },
        });
    }

    $(document).keydown((event) => {
        if (event.key === "Escape" || event.key === "Esc") {
            if (nsModalClosable) nsModal.hide();
        }
    });

    $nsSearch.on('input', function () {
        nsListSearch();
    });

    function nsListSearch() {
        let filter = $nsSearch.val().toUpperCase();
        $('#namespace-list li').each(function () {
            let name = $(this).find('.text-sm > div:first-child').text();
            let owner = $(this).find('.text-sm > div:nth-child(2)').text();
            let combinedText = (name + ' ' + owner).toUpperCase();
            if (combinedText.indexOf(filter) > -1)
                $(this).show();
            else
                $(this).hide();
        });
    }

});
