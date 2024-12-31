const $registryName = $('#registry-name');
const $registryEdit = $('#registry-edit');
const $registryPublic = $('#registry-public');

$registryEdit.on('click', function () {
    let name = $registryName.val().trim();

    if (!name) {
        Alert('Name is required');
        return;
    }

    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}/${currentURL.resource_id}`,
        method: 'PATCH',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            'name': name,
            'public': $registryPublic.prop('checked')
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
