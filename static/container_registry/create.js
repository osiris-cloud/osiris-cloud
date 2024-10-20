const $registryName = $('#registry-name');
const $registrySlug = $('#registry-slug');
const $registrySlugPreview = $('#registry-slug-preview');
const $registryPassword = $('#registry-password');
const $registryCreate = $('#registry-create');

const currentURL = parseURL();

$registryCreate.on('click', function () {
    let name = $registryName.val().trim();
    let slug = $registrySlugPreview.val().trim();
    let password = $registryPassword.val().trim();
    if (!name) {
        Alert('Name is required');
        return;
    }
    if (slug.length < 3 || slug.length > 32) {
        Alert('URL Slug must be between 3 and 32 characters');
        return;
    }
    if (password.length < 8) {
        Alert('Password must be at least 8 characters');
        return;
    }

    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}`,
        method: 'PUT',
        data: JSON.stringify({
            name: name,
            slug: slug,
            password: password,
        }),
        success: (data) => {
            Confirm('Registry created', (ok) => {
                    if (ok) {
                        window.location.href = `/container-registry/${currentURL.nsid}/${data.crid}`;
                    } else {
                        window.location.href = `/container-registry/${currentURL.nsid}`;
                    }
                }, {ok: 'View Registry', cancel: 'List Registries', icon: 'check'}
            );
        }
    });
});

$registrySlug.on('input', function () {
    let slug = $registrySlug.val().trim().toLowerCase().replace(/[^a-z0-9]/g, '-');
    $registrySlugPreview.text(slug.replace(/^-+|-+$/g, '').replace(/-+/g, '-'));
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
