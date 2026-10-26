from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProgress, Badge, UserBadge

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from .models import Station
        stations = Station.objects.filter(is_active=True)
        for station in stations:
            UserProgress.objects.create(user=instance, station=station)

@receiver(post_save, sender=UserProgress)
def check_badges_on_progress(sender, instance, created, **kwargs):
    if instance.completed:
        user = instance.user
        completed_stations = UserProgress.objects.filter(user=user, completed=True).count()
        total_stations = user.userprogress_set.count()
        
        if completed_stations >= total_stations * 0.5:
            badge, created = Badge.objects.get_or_create(
                name=_('عارف مهدوی'),
                defaults={
                    'description': _('برای تکمیل بیش از 50% ایستگاه‌ها'),
                    'points_required': 500
                }
            )
            UserBadge.objects.get_or_create(user=user, badge=badge)
# افزودن به انتهای signals.py
@receiver(post_save, sender=CustomUser)
def create_social_profile(sender, instance, created, **kwargs):
    if created:
        SocialProfile.objects.create(user=instance)

@receiver(post_delete, sender=Post)
def update_posts_count_on_delete(sender, instance, **kwargs):
    try:
        social_profile = SocialProfile.objects.get(user=instance.user)
        social_profile.posts_count = Post.objects.filter(user=instance.user, is_active=True).count()
        social_profile.save()
    except SocialProfile.DoesNotExist:
        pass

@receiver(post_delete, sender=Follow)
def update_follow_counts_on_delete(sender, instance, **kwargs):
    update_follow_counts(instance.follower, instance.following)