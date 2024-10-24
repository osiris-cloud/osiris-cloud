function copyToClip(value) {
    navigator.clipboard.writeText(value);
}

function changeIcon(e) {
    showSuccess(e);
    setTimeout(resetToDefault, 2000);
}
function showSuccess(e) {
    e.currentTarget.classList.add('hidden');
    $successIcon.classList.remove('hidden');
    $defaultTooltipMessage.classList.add('hidden');
    $successTooltipMessage.classList.remove('hidden');

}

const resetToDefault = () => {
    $defaultIcon.classList.remove('hidden');
    $successIcon.classList.add('hidden');
    $defaultTooltipMessage.classList.remove('hidden');
    $successTooltipMessage.classList.add('hidden');
}

