const $registryName = $('#registry-name');
const $registrySlug = $('#registry-slug');
const $registrySlugAvailable = $('#registry-slug-availability');
const $registryCreate = $('#registry-create');

let slugAvailable = false;
let processedSlug = '';

$registrySlug.on('input', function () {
    $registrySlugAvailable.text('');
    slugAvailable = false;

    let slug = $(this).val()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '-')
        .replace(/-+/g, '-');

    $registrySlug.val(slug);

    if (slug.length < 3) {
        $registrySlugAvailable.text('Repo name must have at least 3 characters');
        $registrySlugAvailable.css("color", "red");
        slugAvailable = false;
        return;
    }

    if (slug.startsWith('-')) {
        $registrySlugAvailable.text('Repo name cannot start with a hyphen');
        $registrySlugAvailable.css("color", "red");
        slugAvailable = false;
        return;
    }

    if (slug.endsWith('-')) {
        $registrySlugAvailable.text('Repo name cannot end with a hyphen');
        $registrySlugAvailable.css("color", "red");
        slugAvailable = false;
        return;
    }

    slug = slug.trim().replace(/^-+|-+$/g, '');
    processedSlug = slug;

    $.ajax({
        url: '/api/container-registry/name-check',
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        data: {repo: slug},
        success: (data) => {
            if (data.available) {
                $registrySlugAvailable.text('Available');
                $registrySlugAvailable.css("color", "lawngreen");
                slugAvailable = true;
            } else {
                $registrySlugAvailable.text('Not available. Try another.');
                $registrySlugAvailable.css("color", "red");
                slugAvailable = false;
            }
        }
    });
});

$registryCreate.on('click', function () {
    let name = $registryName.val().trim();
    let slug = $registrySlug.val().trim();

    if (!name) {
        Alert('Name is required');
        return;
    }
    if (slug.startsWith('-') || slug.endsWith('-')) {
        Alert('Repo name cannot start or end with a hyphen');
        return;
    }
    if (processedSlug.length < 3 || processedSlug.length > 32) {
        Alert('Repo name must be between 3 and 32 characters');
        return;
    }
    if (!slugAvailable) {
        Alert('Repo name is not available. Please choose another');
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
            repo_name: processedSlug,
            public: $('#registry-public').is(':checked'),
        }),
        success: (data) => {
            Confirm('Registry created', (ok) => {
                    if (ok) {
                        window.location.href = `/container-registry/${currentURL.nsid}/${data.registry.crid}`;
                    } else {
                        window.location.href = `/container-registry/${currentURL.nsid}`;
                    }
                }, {yes: 'View Registry', no: 'List Registries', icon: 'check'}
            );
        }
    });

});
