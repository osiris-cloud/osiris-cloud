const $secretValues = $('#secret-values');
const $template = $('#secret-item');
const $downloadButton = $('#download-secret-button');
const $deleteButton = $('#delete-secret-button');

const secretType = $secretValues.data('secret-type');
let VALUES = {};

function loadValues() {
    $.ajax({
        url: `/api/secret-store/${currentURL.nsid}/${currentURL.resource_id}/values`,
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            $secretValues.empty();

            if (Object.keys(data.values).length === 0) {
                $secretValues.addClass('hidden');
                $downloadButton.addClass('hidden');
                showNoResource();
            } else {
                VALUES = data.values;

                if(secretType === 'dockerconfig')
                    $downloadButton.addClass('hidden');
                else
                    $downloadButton.removeClass('hidden');

                for (const [key, value] of Object.entries(data.values)) {
                    const $newRow = $($template.html());
                    const $maskedValue = $newRow.find('.masked-value');
                    const $textarea = $newRow.find('textarea');

                    $maskedValue.addClass('dark:text-gray-400');

                    $newRow.find('input[type="text"]').val(key);
                    $textarea.val(value);

                    if (!value || value.trim() === '') {
                        $maskedValue.text('Empty value');
                        $maskedValue.addClass('cursor-default').removeClass('cursor-pointer');
                    } else {
                        $maskedValue.text('••••••');
                        $maskedValue.addClass('cursor-pointer');

                        $maskedValue.hover(
                            function () {
                                $(this).text('Click to reveal');
                            },
                            function () {
                                $(this).text('••••••');
                            }
                        );

                        $maskedValue.on('click', function () {
                            if ($textarea.is(':hidden')) {
                                $textarea.removeClass('hidden');
                                $maskedValue.addClass('hidden');
                            }
                        });
                    }

                    $secretValues.append($newRow);
                }
                showNoResource(false);
                $secretValues.removeClass('hidden');
            }
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
}

function downloadAsFile() {
    let content = `# Secret ID: ${currentURL.resource_id}\n\n`;

    Object.entries(VALUES).forEach(([key, value]) => {
        content += `${key}="${value}"\n`;
    });

    const blob = new Blob([content], {type: 'text/plain'});
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentURL.resource_id + '.env';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function deleteSecret() {
    $.ajax({
        url: `/api/secret-store/${currentURL.nsid}/${currentURL.resource_id}`,
        method: 'DELETE',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: () => {
            Alert('Secret deleted', () => {
                window.location.href = `/secret-store/${currentURL.nsid}`
            }, {'icon': 'check'});
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
}

$deleteButton.on('click', function () {
    Confirm('Are you sure you want to delete this secret?', (ok) => {
        if (ok)
            deleteSecret()
    }, {'yes': 'Delete'});
});

$downloadButton.on('click', downloadAsFile);

window.onload = function () {
    loadValues();
}
