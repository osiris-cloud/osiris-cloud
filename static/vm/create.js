const _vm_name = $('#vm-name');
const _os = $('#os');
const _size = $('#size');
const _disk = $('#disk');

// const _gh_import_modal = $('#gh-import-modal');
const _gh_import_modal_close = $('#gh-import-modal-close');
const _gh_username = $('#gh-username');
const _gh_ssh_key = $('#gh-ssh-key');
const _gh_import_key_button = $('#gh-import-key-button');

const _enable_ssh = $('#enable-ssh');
const _ssh_key = $('#ssh-key');
const _password_auth = $('#password-auth');
const _vm_username = $('#vm-username');
const _vm_password_1 = $('#vm-password-1');
const _vm_password_2 = $('#vm-password-2');

const _network_type = $('#network-type');

// const _tab_previous = $('#tab-previous');
// const _tab_next = $('#tab-next');
const _vm_create = $('#vm-create');

_os.change(function () {
    if (_os.val().includes('windows'))
        $('[data-linux="true"]').removeClass('grid-item').addClass('hidden');
    else {
        $('div[data-linux="true"]').removeClass('hidden').addClass('grid-item');
        $('p[data-linux="true"]').removeClass('hidden');
    }
});


_vm_create.click(function () {
    const name = _vm_name.val().trim();
    const os_val = _os.val();
    const size_val = _size.val();
    const disk_val = _disk.val();
    const ssh_key = _ssh_key.val().trim();
    const password_auth = _password_auth.is(':checked');
    const vm_username = _vm_username.val().trim();
    const vm_password_1 = _vm_password_1.val().trim();
    const vm_password_2 = _vm_password_2.val().trim();
    const network_type = _network_type.val();

    if (name === '' || name.length > 100) {
        alert('Please enter a valid name for the VM');
        return false;
    }
    if (os_val === '') {
        alert('Please select an OS');
        return false;
    }
    if (size_val === '') {
        alert('Please select a size');
        return false;
    }
    if (disk_val === '' || disk_val < 1) {
        alert('Please enter disk size between 4 and 50 GB');
        return false;
    }
    if (!os_val.includes('windows') && _enable_ssh.is(':checked')) {
        if (!ssh_key && !password_auth) {
            alert('Please enter an SSH key or enable ssh password authentication');
            return false;
        } else if (ssh_key && password_auth) {
            const rsaRegex = /^ssh-rsa\s+[A-Za-z0-9+/]+[=]{0,3}(\s+.+)?$/;
            const dsaRegex = /^ssh-dss\s+[A-Za-z0-9+/]+[=]{0,3}(\s+.+)?$/;
            const ecdsaRegex = /^ecdsa-[A-Za-z0-9-]+\s+[A-Za-z0-9+/]+[=]{0,3}(\s+.+)?$/;
            const ed25519Regex = /^ssh-ed25519\s+[A-Za-z0-9+/]+[=]{0,3}(\s+.+)?$/;

            if (!(rsaRegex.test(ssh_key) || dsaRegex.test(ssh_key) || ecdsaRegex.test(ssh_key) || ed25519Regex.test(ssh_key))) {
                alert('Invalid SSH key');
                return false;
            }
        }
    }
    if (vm_username === '') {
        alert('Please enter a username for the VM');
        return false;
    }
    if (vm_password_1 === '') {
        alert('Please enter a password for the VM');
        return false;
    }
    if (vm_password_1 !== vm_password_2) {
        alert('Passwords do not match');
        return false;
    }
    if (network_type === '') {
        alert('Please select a network type');
        return false;
    }

    if (_vm_create.text().trim() === 'Validate') {
        _vm_create.text('Validating...');
        setTimeout(() => {
            _vm_create.text('Create')
        }, 500);
        return true;
    }

    let vm_config = {
        'name': name,
        'os': os_val,
        'size': size_val,
        'disk': Number(disk_val),
        'vm_username': vm_username,
        'vm_password': vm_password_1,
        'network_type': network_type
    };

    if (_enable_ssh.is(':checked')) {
        vm_config['ssh_config'] = {
            'ssh_key': ssh_key,
            'password_auth': password_auth
        };
    }

    $.ajax({
        url: '/api/vm',
        type: 'POST',
        data: {
            'vm_spec': JSON.stringify(vm_config),
            'csrfmiddlewaretoken': document.querySelector('input[name="csrf-token"]').value,
        },
        success: function (response) {
            if (response.status === 200) {
                if (_vm_create.text().trim() === 'Validate') {
                    _vm_create.text('Create');
                } else {
                    alert('VM created successfully');
                    window.location.href = '/vm';
                }
            } else {
                alert(response.message);
            }
        }, error: function (xhr, status) {
            alert('An error occurred');
        }
    });
});


_gh_import_modal_close.click(function () {
    _gh_import_key_button.text('Get Key');
    _gh_username.val('');
    _gh_ssh_key.val('');
});

_gh_username.on('input', function () {
    _gh_ssh_key.val('');
    _gh_import_key_button.text('Get Key');
});

_enable_ssh.on('click', function () {
    if (_enable_ssh.is(':checked')) {
        _ssh_key.parent().removeClass('hidden').addClass('grid-item');
        _password_auth.parent().parent().removeClass('hidden').addClass('grid-item');
    } else {
        _ssh_key.parent().addClass('hidden').removeClass('grid-item');
        _password_auth.parent().parent().addClass('hidden').removeClass('grid-item');
    }
});

_gh_import_key_button.click(function () {
    const username = _gh_username.val();
    if (_gh_import_key_button.text().trim() === 'Get Key') {
        if (username === '') {
            alert('Please enter a GitHub username');
            return false;
        }
        $.ajax({
            url: `https://api.github.com/users/${username}/keys`, type: "GET", success: function (response) {
                if (response.status === 404) {
                    _gh_ssh_key.val('Invalid username');
                    return false;
                }
                if (response.length === 0) {
                    _gh_ssh_key.val('No keys found');
                    return false;
                }
                _gh_ssh_key.val(response[0].key);
                _gh_import_key_button.text('Continue');
            }, error: function (xhr, status) {
                _gh_ssh_key.val('Invalid username');
            }
        });
    } else {
        _ssh_key.val(_gh_ssh_key.val());
        _gh_import_modal_close.click();
    }
});


_vm_name.on('input', function () {
    _vm_create.text('Validate');
});
_os.on('input', function () {
    _vm_create.text('Validate');
});
_size.on('input', function () {
    _vm_create.text('Validate');
});
_disk.on('input', function () {
    _vm_create.text('Validate');
});
_ssh_key.on('input', function () {
    _vm_create.text('Validate');
});
_password_auth.on('input', function () {
    _vm_create.text('Validate');
});
_vm_username.on('input', function () {
    _vm_create.text('Validate');
});
_vm_password_1.on('input', function () {
    _vm_create.text('Validate');
});
_vm_password_2.on('input', function () {
    _vm_create.text('Validate');
});
_network_type.on('input', function () {
    _vm_create.text('Validate');
});