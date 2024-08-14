let CurrentNamespace = localStorage.getItem('namespace');

(!CurrentNamespace) ? loadNamespace('default') : loadNamespace(CurrentNamespace);


let $NSModalTitle = $('#ns-modal-title');
let $NSModalName = $('#ns-modal-name');
let $sharingSpinner = $('#sharing-spinner');
let $checkedSvg = $('#role-selected-svg');
let $userSearch = $('#user-search');
let $userSearchDropdown = $('#user-search-dropdown');
let $userSearchResults = $('#user-search-results');
let userSearchSocket = null;

let NSUsers = [];

$userSearch.on('input', () => {
    handleSearchUsers()
});
$("#role-owner").on('click', () => {
    handleChangeRole('owner')
});
$("#role-manager").on('click', () => {
    handleChangeRole('manager')
});
$("#role-viewer").on('click', () => {
    handleChangeRole('viewer')
});


$('#CreateNamespace').on('click', () => {
    let namespace = $('NamespaceName').val();


    // $.ajax({
    //         url: '/api/namespace',
    //         type: 'POST',
    //         data: {name: namespace},
    //         success: (data) => {
    //             if (data.status === 'success') {
    //                 switchNamespace(namespace);
    //             }
    //         }
    //     }
    // );
});


function loadNamespace(namespace = 'default') {
    $.ajax({
            url: '/api/namespace/' + namespace,
            type: 'GET',
            success: (data) => {
                if (data.status === 'success') {
                    $('#dropdown-ns-button').text(data.name);
                    localStorage.setItem('namespace', data.nsid);
                    CurrentNamespace = data.nsid;
                }
            }
        }
    );
}

function handleRemoveUser() {
    console.log();
}

function handleAddUser(username) {
    console.log(username);
}

function handleSearchUsers() {
    let value = $userSearch.val();
    if (value.length === 0) {
        $userSearchDropdown.addClass("hidden");
    } else {
        if (userSearchSocket) {
            userSearchSocket.send(value);
        } else {
            alert("Session expired, try refreshing page. If issue persists, contact support.");
        }
    }

}

function handleChangeRole(role) {
    console.log(role);
}

function createUserListItem(username, name, email, avatar, roundedT, roundedB) {
    return $('<li>', {
        class: ('flex items-center p-1 hover:bg-gray-300 dark:hover:bg-gray-500')
            + (roundedT ? ' rounded-t-lg' : '') + (roundedB ? ' rounded-b-lg' : ''),
        click: () => {
            handleAddUser(username);
        }
    }).append(
        $('<img>', {class: 'w-10 h-10 rounded-full ml-1', src: avatar, alt: name})
    ).append(
        $('<div>', {
            class: 'ml-2.5 items-center'
        }).append(
            $('<div>', {
                class: 'text-black text-sm dark:text-white align-middle cursor-default mr-1', text: name
            })
        ).append(
            $('<div>', {
                class: 'text-xs font-normal text-gray-500 dark:text-gray-300 cursor-default', text: email
            })
        )
    );
}

function connectSearch(connect = true) {
    if (connect && !userSearchSocket) {
        try {
            userSearchSocket = new WebSocket('/api/user-search');
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
            $userSearchResults.append(createUserListItem(user.username, user.name, user.email, user.avatar, roundedT, roundedB));
        });
        $userSearchDropdown.removeClass("hidden");
    }
}
