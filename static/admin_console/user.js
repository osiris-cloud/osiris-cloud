const $userSearch = $('#user-search');
const $userSearchResults = $('#user-search-results');
let $userSearchDropdown = $('#user-search-dropdown');
$userSearch.on('keypress', (event) => {
    if (event.key === 'Enter') searchUsers();
});


function searchUsers() {
    let value = $userSearch.val();
    if (value.length === 0) {
        $userSearchDropdown.addClass("hidden");
    } else {
        $.ajax({
            type: "POST",
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            url: "/api/admin/gh-search",
            data: {
                query: value
            },
            success: (data) => {
                $userSearchResults.empty();
                let users = data.users;
                for (let i = 0; i < users.length; i++) {
                    let user = users[i];
                    $userSearchResults.append(createSearchUserItem(user.id, user.username, user.name, user.email, user.avatar, i === 0, i === users.length - 1));
                }
                $userSearchDropdown.removeClass("hidden");
            }
        });
    }
}

function createSearchUserItem(gh_id, username, name, email, avatar, roundedT, roundedB) {
    return $('<li>', {
        class: ('flex items-center p-1 hover:bg-gray-300 dark:hover:bg-gray-600') + (roundedT ? ' rounded-t-lg' : '') + (roundedB ? ' rounded-b-lg' : ''),
        click: () => {
            $userSearchDropdown.addClass("hidden");
            $userSearch.val('');
            previewUser(gh_id, username, name, email);
        }
    }).append($('<img>', {class: 'w-10 h-10 rounded-full ml-1', src: avatar, alt: name})).append($('<div>', {
        class: 'ml-2.5 items-center'
    }).append($('<div>', {
        class: 'text-black text-sm dark:text-white align-middle cursor-default mr-1', text: name || username
    })).append($('<div>', {
        class: 'text-xs font-normal text-gray-500 dark:text-gray-300 cursor-default', text: username
    })));
}


function previewUser(gh_id, username, name, email) {
    $('#gh-id').val(gh_id);
    $('#gh-username').val(username);
    $('#gh-first-name').val(name ? name.split(' ')[0] : '');
    $('#gh-last-name').val(name ? name.split(' ')[1] : '');
    $('#gh-email').val(email ? email : '');
}

$('#add-button').on('click', () => {
    let gh_id = $('#gh-id').val();
    let username = $('#gh-username').val();
    let firstName = $('#gh-first-name').val();
    let lastName = $('#gh-last-name').val();
    let email = $('#gh-email').val();
    let role = $('#cluster-role').val();
    addExtUser(gh_id, username, firstName, lastName, email, role);
});

function addExtUser(gh_id, username, firstName, lastName, email, role) {
    $.ajax({
        type: "PUT",
        url: "/api/admin/external-user",
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: "application/json",
        data: JSON.stringify({
            'gh_id': gh_id,
            'email': email,
            'gh_username': username,
            'first_name': firstName,
            'last_name': lastName,
            'role': role
        }),
        success: () => {
            alert("User added!");
            location.reload();
        },
        error: (resp) => {
            alert(resp.responseJSON.message || "An error occurred");
        }
    });
}
