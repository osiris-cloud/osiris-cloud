const $registryName = $('#registry-name');
const $registryPassword = $('#registry-password');
const $registryEdit = $('#registry-edit');

$registryEdit.on('click', function () {
    let name = $registryName.val().trim();
    let password = $registryPassword.val().trim();

    if (!name) {
        Alert('Name is required');
        return;
    }

    if (password.length < 8) {
        Alert('Password must be at least 8 characters');
        return;
    }

    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}/${currentURL.resource_id}`,
        method: 'PATCH',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            name: name,
            password: password,
        }),
        success: (data) => {
            Alert('Changes Saved', (ok) => {
                    window.location.href = `/container-registry/${currentURL.nsid}/${currentURL.resource_id}`;
                }, {icon: 'check'}
            );
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
});

$('#generate-password').on('click', () => {
    let psw = window.crypto.getRandomValues(new BigUint64Array(4))
        .reduce((prev, curr, index) => (
                !index ? prev : prev.toString(36)) +
            (index % 2 ? curr.toString(36).toUpperCase() :
                curr.toString(36))).split('')
        .sort(() => 128 - window.crypto.getRandomValues(new Uint8Array(1))[0]).join('');
    $registryPassword.val(psw.slice(0, 32));
});

