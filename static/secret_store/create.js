window.addEventListener('load', function () {
    const $template = $('#secret-item');
    const $secretsContainer = $('#secrets');
    const $createButton = $('#secret-create-button');
    const $secretName = $('#secret-name');
    const $secretType = $('#secret-type');
    const $addSecretBtn = $('#add-secret');
    const $importSecretBtn = $('#import-secret');
    const $buttonGroup = $('#button-group');
    const $dockerconfigHeader = $('#dockerconfig-header');

    function setupDockerConfigSecret() {
        $secretsContainer.children().not('template').remove();

        const $newRow = $($template.html());
        $newRow.find('input[type="text"]').val('.dockerconfigjson').prop('readonly', true);
        $newRow.find('svg').hide();

        $secretsContainer.append($newRow);
        $dockerconfigHeader.show();

        $newRow.find('textarea').on('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        $buttonGroup.hide();
    }

    function setupOpaqueSecret() {
        $secretsContainer.children().not('template').remove();
        $buttonGroup.show();
        $dockerconfigHeader.hide();
        $secretsContainer.find('svg').show();
    }

    $secretType.on('change', function () {
        if ($(this).val() === 'dockerconfig')
            setupDockerConfigSecret();
        else
            setupOpaqueSecret();
    });

    $addSecretBtn.on('click', function () {
        if ($secretType.val() !== 'dockerconfig') {
            const $newRow = $($template.html());
            $secretsContainer.append($newRow);
            $newRow.find('textarea').on('input', function () {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
        }
    });

    $('#values').on('click', 'svg', function () {
        if ($secretType.val() !== 'dockerconfig' || $('#secrets .flex.flex-col.md\\:flex-row').length > 1) {
            $(this).closest('.flex.flex-col.md\\:flex-row').remove();
        }
    });

    $importSecretBtn.on('click', function () {
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

    $createButton.on('click', function () {
        const secretName = $secretName.val().trim()
        const values = getKeyValuePairs();

        if (secretName === '') {
            Alert('Secret name is required');
            return;
        }

        $.ajax({
            url: `/api/secret-store/${currentURL.nsid}`,
            method: 'PUT',
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            contentType: 'application/json',
            data: JSON.stringify({
                'name': secretName,
                'type': $secretType.val(),
                'values': values
            }),
            success: (data) => {
                Confirm('Secret created', (ok) => {
                        if (ok) {
                            window.location.href = `/secret-store/${currentURL.nsid}/${data.secret.secretid}`;
                        } else {
                            window.location.href = `/secret-store/${currentURL.nsid}`;
                        }
                    }, {yes: 'View Secret', no: 'List Secrets', icon: 'check'}
                );
            }
        });
    });

    setTimeout(() => {
        $secretType.trigger('change');
    }, 50);

});
