const $template = $('#secret-item');
const $secretsContainer = $('#secrets');
const $secretName = $('#secret-name');
const $saveButton = $('#secret-save-button');
const $addSecretBtn = $('#add-secret');
const $importSecretBtn = $('#import-secret');
const $buttonGroup = $('#button-group');
const $dockerconfigHeader = $('#dockerconfig-header');
const secretType = $secretsContainer.data('secret-type');

function setupDockerConfigSecret() {
    $secretsContainer.empty();
    $buttonGroup.hide();
    $dockerconfigHeader.show();
}

function setupOpaqueSecret() {
    $buttonGroup.show();
    $dockerconfigHeader.hide();
}

$addSecretBtn.on('click', function () {
    if (secretType !== 'dockerconfig') {
        const $newRow = $($template.html());
        $secretsContainer.append($newRow);
        $newRow.find('textarea').on('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }
});

$('#values').on('click', 'svg', function () {
    if (secretType !== 'dockerconfig') {
        $(this).closest('.flex.flex-col.md\\:flex-row').remove();
    }
});

function loadValues() {
    $.ajax({
        url: `/api/secret-store/${currentURL.nsid}/${currentURL.resource_id}/values`,
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            for (const [key, value] of Object.entries(data.values)) {
                const $newRow = $($template.html());
                const $textarea = $newRow.find('textarea');
                const $input = $newRow.find('input[type="text"]');

                if (secretType === 'dockerconfig') {
                    $input.val('.dockerconfigjson').prop('readonly', true);
                    $newRow.find('svg').hide();
                } else
                    $input.val(key);

                $textarea.val(value);

                $textarea.on('input', function () {
                    this.style.height = 'auto';
                    this.style.height = (this.scrollHeight) + 'px';
                });

                $secretsContainer.append($newRow);
            }
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        }
    });
}

$importSecretBtn.on('click', function () {
    if (secretType === 'dockerconfig') return;

    const fileInput = $('<input type="file" accept=".env" style="display: none">');

    fileInput.on('change', function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (e) {
            const content = e.target.result;
            const lines = content.split('\n');

            lines.forEach(line => {
                line = line.trim();
                if (!line || line.startsWith('#')) return;
                const match = line.match(/^([^=]+)=(.*)$/);
                if (match) {
                    const key = match[1].trim();
                    const value = match[2].trim();

                    const $newRow = $($template.html());
                    $newRow.find('input[type="text"]').val(key);
                    $newRow.find('textarea').val(value.replace(/(^"|"$)/g, ''));

                    $secretsContainer.append($newRow);

                    const $textarea = $newRow.find('textarea');
                    $textarea.on('input', function () {
                        this.style.height = 'auto';
                        this.style.height = (this.scrollHeight) + 'px';
                    });
                    $textarea.trigger('input');
                }
            });
        };
        reader.readAsText(file);
    });
    fileInput.trigger('click');
});

function getKeyValuePairs() {
    const pairs = {};

    $('#secrets .flex.flex-col.md\\:flex-row').each(function () {
        const $row = $(this);
        const key = $row.find('input[type="text"]').val().trim();
        const value = $row.find('textarea').val().trim();
        if (key) {
            pairs[key] = value;
        }
    });
    return pairs;
}

$saveButton.on('click', function () {
    const secretName = $secretName.val().trim()
    const values = getKeyValuePairs();

    if (secretName === '') {
        Alert('Secret name is required');
        return;
    }

    $.ajax({
        url: `/api/secret-store/${currentURL.nsid}/${currentURL.resource_id}`,
        method: 'PATCH',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        contentType: 'application/json',
        data: JSON.stringify({
            'name': secretName,
            'values': values
        }),
        success: (data) => {
            Alert('Secret updated', () => {
                window.location.href = `/secret-store/${currentURL.nsid}/${data.secret.secretid}`;
            }, {'icon': 'check'});
        }
    });
});

window.onload = function () {
    if (secretType === 'dockerconfig')
        setupDockerConfigSecret();
    else
        setupOpaqueSecret();

    loadValues();
}
