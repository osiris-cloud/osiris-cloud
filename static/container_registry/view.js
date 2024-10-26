const $imageTable = $('#registry-image-table');
const $imageTableContainer = $('#registry-image-table-container');

function copyToClip(value, defaultIconId, successIconId, tooltipId) {
    navigator.clipboard.writeText(value.trim());

    if (!defaultIconId || !successIconId || !tooltipId) return;

    $(`#${defaultIconId}`).addClass('hidden');
    $(`#${successIconId}`).removeClass('hidden');

    setTimeout(() => {
        $(`#${tooltipId}`).addClass('hidden');
    }, 100);

    setTimeout(() => {
        $(`#${defaultIconId}`).removeClass('hidden');
        $(`#${successIconId}`).addClass('hidden');
        $(`#${tooltipId}`).removeClass('hidden');
    }, 1000);
}

function createImageTableEntry(repo, tag) {
    const $row = $('<tr/>', {
        class: 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700',
    });
    $row.append($('<th/>', {
        scope: 'row', class: 'px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white', text: repo.repo,
    })).append($('<td/>', {
        class: 'px-6 py-4', text: tag.name,
    })).append($('<td/>', {
        class: 'px-6 py-4', text: formatBytes(tag.size),
    })).append($('<td/>', {
        class: 'px-6 py-4', text: tag.digest.replace('sha256:', ''),
    }));
    const $deleteButton = $('<button/>', {
        class: 'font-medium text-red-600 dark:text-red-500 hover:underline', text: 'Delete', click: () => {
            deleteImage(repo.repo, tag.name);
        }
    });
    $row.append($('<td/>', {class: 'px-6 py-4'}).append($deleteButton));
    return $row;
}

function loadRegistryInfo() {
    $.ajax({
        url: `/api/container-registry/${currentURL.nsid}/${currentURL.resource_id}/stat`,
        method: 'POST',
        headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
        success: (data) => {
            if (data.stats.length === 0) {
                $imageTableContainer.addClass('hidden');
                showNoResource();
            } else {
                let results = [];
                data.stats.forEach((repo) => {
                    repo.tags.forEach((stat) => {
                        results.push(createImageTableEntry(repo, stat));
                    });
                });
                $imageTable.empty();
                $imageTable.append(results);
                showNoResource(false);
                $imageTableContainer.removeClass('hidden');
            }
            showLoader(false);
        },
        error: (resp) => {
            Alert(resp.responseJSON.message || "Internal Server Error");
        },
    });
}


showLoader();

loadRegistryInfo();
//setInterval(loadRegistryInfo, 5000);


function deleteImage(repo, tag) {
    Confirm("Are you sure you want to delete this image?", (ok) => {
        if (!ok) return;
        $.ajax({
            url: `/api/container-registry/${currentURL.nsid}/${currentURL.resource_id}/delete`,
            method: 'POST',
            headers: {"X-CSRFToken": document.querySelector('input[name="csrf-token"]').value},
            contentType: 'application/json',
            data: JSON.stringify({'image': repo, tag}),
            success: (data) => {
                Alert(`Image "${repo}:${tag}" deleted`, {'icon': 'check'});
                loadRegistryInfo();
            },
            error: (resp) => {
                Alert(resp.responseJSON.message || "Internal Server Error");
                loadRegistryInfo();
            },
        });
    });
}
