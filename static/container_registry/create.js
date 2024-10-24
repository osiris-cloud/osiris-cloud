const $registryName = $('#registry-name');
const $registrySlug = $('#registry-slug');
const $registrySlugAvailable = $('#registry-slug-availability');
const $registryPassword = $('#registry-password');
const $registryCreate = $('#registry-create');

let slugAvailable = false;
let processedSlug = '';

$registrySlug.on('input', function () {
    $registrySlugAvailable.text('');
    slugAvailable = false;

    let slug = $registrySlug.val()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '-')
        .replace(/-+/g, '-');

    $registrySlug.val(slug);

    if (slug.length < 3)
        return;

    slug = slug.trim().replace(/^-+|-+$/g, '');
    processedSlug = slug;

    $.ajax({
        url: '/api/container-registry/name-check',
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        data: {slug: slug},
        success: (data) => {
            if (data.available) {
                $registrySlugAvailable.text('Available');
                $registrySlugAvailable.css("color", "lawngreen");
                slugAvailable = true;
            } else {
                $registrySlugAvailable.text('Not available');
                $registrySlugAvailable.css("color", "firebrick");
            }
        }
    });
});

$registryCreate.on('click', function () {
    let name = $registryName.val().trim();
    let password = $registryPassword.val().trim();
    let slug = $registrySlug.val().trim();

    if (!name) {
        Alert('Name is required');
        return;
    }
    if (slug.startsWith('-') || slug.endsWith('-')) {
        Alert('Slug cannot start or end with a hyphen');
        return;
    }
    if (processedSlug.length < 3 || processedSlug.length > 32) {
        Alert('URL Slug must be between 3 and 32 characters');
        return;
    }
    if (!slugAvailable) {
        Alert('Slug is not available. Please choose another');
        return;
    }
    if (password.length < 8) {
        Alert('Password must be at least 8 characters');
        return;
    }

    if ($registryCreate.text().trim() === 'Validate') {
        $registryCreate.text('Validating...');
        setTimeout(() => {
            $registryCreate.text('Create')
        }, 500);
        return;
    }

    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}`,
        method: 'PUT',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            name: name,
            slug: processedSlug,
            password: password,
        }),
        success: (data) => {
            Confirm('Registry created', (ok) => {
                    if (ok) {
                        window.location.href = `/container-registry/${currentURL.nsid}/${data.crid}`;
                    } else {
                        window.location.href = `/container-registry/${currentURL.nsid}`;
                    }
                }, {yes: 'View Registry', no: 'List Registries', icon: 'check'}
            );
        }
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
