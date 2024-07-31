let CurrentNamespace = localStorage.getItem('namespace');

window.addEventListener('DOMContentLoaded', () => {
        if (!CurrentNamespace) {
            switchNamespace();
        }
    }
);

let $NSModalTitle;
let $NSModalName;
let $sharingSpinner;
let $checkedSvg;
let $userSearch;
let $userSearchDropdown;
let userSearchWS;

window.addEventListener('DOMContentLoaded', () => {
    $NSModalTitle = $('#ns-modal-title');
    $NSModalName = $('#ns-modal-name');
    $sharingSpinner = $('#sharing-spinner');
    $checkedSvg = $('#role-selected-svg');
    $userSearch = $('#user-search');
    $userSearchDropdown = $('#user-search-dropdown');

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

});


window.addEventListener('DOMContentLoaded', () => {
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
});

function switchNamespace(namespace = 'default') {
    $.ajax({
            url: '/api/namespace/' + namespace,
            type: 'GET',
            success: (data) => {
                if (data.status === 'success') {
                    $('dropdown-ns-button').text(data.namespace.name);
                    localStorage.setItem('namespace', data.namespace.nsid);
                    CurrentNamespace = data.namespace.nsid;
                }
            }
        }
    );
}

function handleRemoveUser() {
    console.log();
}

function handleAddUser() {
    console.log();
}

function handleSearchUsers() {
    let value = $userSearch.val();
    if (value.length === 0) {
        $userSearchDropdown.addClass("hidden");
    } else {
        $userSearchDropdown.removeClass("hidden");
    }

}

function handleChangeRole(role) {
    console.log(role);
}

function createUserListItem(name, avatar) {
    const $li = $('<li></li>');
    const $div = $('<div></div>').addClass('flex items-center px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-600 dark:hover:text-white');
    const $img = $('<img>')
        .addClass('w-6 h-6 me-2 rounded-full')
        .attr('src', avatar)
        .attr('alt', '');
    const $name = $('<span></span>').text(name);
    $div.append($img).append($name);
    $li.append($div);
    return $li;
}

function connectSearch(connect = true) {
    if (connect && !userSearchWS) {
        userSearchWS = new WebSocket('/api/user-search');
        userSearchWS.onopen = () => {
            console.log('connected');
            userSearchWS.onmessage = handleSocketMessage;
        };

    } else if (userSearchWS && !connect) {
        console.log('closing');
        userSearchWS.close();
        userSearchWS = null;
    }
}

function handleSocketMessage(event) {
    console.log('Message from server:', event.data);
}
