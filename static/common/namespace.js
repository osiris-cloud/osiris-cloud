let CurrentNamespace = localStorage.getItem('namespace');

window.addEventListener('DOMContentLoaded', () => {
        if (!CurrentNamespace) {
            switchNamespace();
        }
    }
);



window.addEventListener('DOMContentLoaded', () => {
    $('#CreateNamespace').on('click', () => {
        let namespace = $('NamespaceName').val();




        // $.ajax({
        //         url: '/api/namespace',
        //         type: 'POST',
        //         data: {name: namespace},
        //         success: (data) => {
        //             if (data.status === 'success') {
        //                 switchNamespace(namespace);
        //             }
        //         }
        //     }
        // );
    });
});

function switchNamespace(namespace = 'default') {
    $.ajax({
            url: '/api/namespace/' + namespace,
            type: 'GET',
            success: (data) => {
                if (data.status === 'success') {
                    $('dropdown-ns-button').text(data.namespace.name);
                    localStorage.setItem('namespace', data.namespace.nsid);
                    CurrentNamespace = data.namespace.nsid;
                }
            }
        }
    );
}


const NSModalTitle = $('#ns-modal-title');
const NSmodalName = $('#ns-modal-name');
const sharingSpinner = $('#sharing-spinner');
