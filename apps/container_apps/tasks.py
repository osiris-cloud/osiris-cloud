from celery import shared_task


@shared_task(name='create_deployment')
def create_deployment() -> None:
    pass


@shared_task(name='patch_deployment')
def patch_deployment() -> None:
    pass


@shared_task(name='delete_deployment')
def delete_deployment() -> None:
    pass

