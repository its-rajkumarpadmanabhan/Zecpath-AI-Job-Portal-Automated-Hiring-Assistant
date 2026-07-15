from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Employer, Candidate


@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.role == "recruiter":
        Employer.objects.get_or_create(user=instance)
    elif instance.role == "candidate":
        Candidate.objects.get_or_create(user=instance)