function copyToClip(value, defaultIconId, successIconId, tooltipId) {
    navigator.clipboard.writeText(value.trim());

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

