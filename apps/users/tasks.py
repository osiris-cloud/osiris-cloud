import requests
import logging

from celery import shared_task, chord, group

from core.settings import env

from ..infra.models import Namespace
from ..container_apps.models import ContainerApp
from ..container_registry.models import ContainerRegistry

from ..container_apps.tasks import delete_deployment
from ..container_registry.tasks import delete_registry


@shared_task(name='send_ns_transfer_email')
def notify_new_owner(owner_email, namespace_id, namespace_name, requester_username):
    subject = "Namespace Ownership Transfer"

    text = f"""
    <html>
    <body>
    <h1>Osiris Cloud</h1>
    <p>
    You have been assigned as the new owner of the namespace: {namespace_name} ({namespace_id}) by {requester_username}.
    </p>
    </body>
    </html>
    """

    response = requests.post(
        f"https://api.mailgun.net/v3/{env.mailgun_sender_domain}/messages",
        auth=("api", env.mailgun_api_key),
        data={"from": f"Osiris Cloud <{env.mailgun_sender_email}>",
              "to": owner_email,
              "subject": subject,
              "text": text
              }
    )

    if response.status_code != 200:
        logging.error(f"Failed to send email notification to {owner_email}")


@shared_task(name='finalize_namespace_deletion')
def finalize_namespace_deletion(results, nsid):
    """
    Callback task to delete namespace after all resources are deleted
    """
    try:
        ns = Namespace.objects.get(nsid=nsid)
        ns.delete()
        logging.info(f"Successfully deleted namespace {nsid} after all resources")
        return True
    except Exception as e:
        logging.exception(f"Failed to finalize namespace deletion {nsid}: {e}")
        raise


@shared_task(name='delete-namespace')
def delete_namespace(nsid):
    try:
        ns = Namespace.objects.get(nsid=nsid)

        # Delete all apps
        apps = ContainerApp.objects.filter(namespace=ns)
        deployment_tasks = [delete_deployment.s(app.appid) for app in apps]

        # Delete all registries
        registries = ContainerRegistry.objects.filter(namespace=ns)
        registry_tasks = [delete_registry.s(registry.crid) for registry in registries]

        if not apps and not registries:
            ns.delete()
            return True

        all_tasks = deployment_tasks + registry_tasks

        chord(all_tasks)(finalize_namespace_deletion.s(nsid))

        return True

    except Exception as e:
        logging.exception(f"Failed to delete namespace {nsid}: {e}")
        return False
