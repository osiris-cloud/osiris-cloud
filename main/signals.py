from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    print("signal User created")
    if created:
        # profile = Profile.objects.create(user=instance)
        # if instance.is_superuser:
        #     profile.role = "admin"
        #     profile.save()
        pass
