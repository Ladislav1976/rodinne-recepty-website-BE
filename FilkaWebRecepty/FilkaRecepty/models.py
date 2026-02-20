import os
import shutil
import unicodedata
import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField, ProcessedImageField
from imagekit.processors import ResizeToFill, ResizeToFit
from PIL import Image


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


def get_user_upload_path(instance, filename):
    return "/".join(["profile_image", str(instance.upload_folder), filename])


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("User_edit", "User_edit"),
        ("Editor", "Editor"),
        ("Admin", "Admin"),
        ("User_readOnly", "User_readOnly"),
    )
    username = None
    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(
        _("role"), max_length=15, choices=ROLE_CHOICES, default="User_edit"
    )
    avatar = models.ImageField(
        _("profile picture"), upload_to=get_user_upload_path, blank=True, null=True
    )
    upload_folder = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def __unicode__(self):
        return self.email

    def avatar_tag(self):
        if self.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" />', self.avatar.url
            )
        return "-"

    avatar_tag.short_description = "Photo"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.avatar:
            img = Image.open(self.avatar.path)
            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)
                img.save(self.avatar.path, optimize=True, quality=85)


@receiver(post_delete, sender=CustomUser)
def auto_delete_avatar_on_delete(sender, instance, **kwargs):
    if instance.avatar and os.path.isfile(instance.avatar.path):
        instance.avatar.delete(save=False)

        folder = os.path.dirname(instance.avatar.path)
        if os.path.isdir(folder) and not os.listdir(folder):
            shutil.rmtree(folder)


@receiver(pre_save, sender=CustomUser)
def auto_delete_old_avatar_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_obj = sender.objects.get(pk=instance.pk)
        old_avatar = old_obj.avatar
    except sender.DoesNotExist:
        return False

    new_avatar = instance.avatar

    if old_avatar and old_avatar != new_avatar:
        if os.path.isfile(old_avatar.path):
            os.remove(old_avatar.path)

            folder = os.path.dirname(old_avatar.path)
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)


class TagGroups(models.Model):
    groupName = models.CharField(
        max_length=60,
        unique=True,
        error_messages={"unique": "Táto skupina už existuje."},
    )

    def __str__(self):
        return self.groupName


class FoodTags(models.Model):
    foodTag = models.CharField(
        max_length=60,
        unique=True,
        error_messages={"unique": "Toto označenie už v tejto skupine existuje."},
    )
    group = models.ForeignKey(
        TagGroups,
        related_name="food_tags",
        on_delete=models.PROTECT,
    )

    def delete(self, *args, **kwargs):
        # Skontrolujeme, či je tento tag v nejakom Food objekte
        if self.foodTags.exists():  # 'foodTags' je related_name z modelu Foods
            raise ValidationError(
                f"Tag '{self.foodTag}' nemôžete vymazať, lebo je priradený k receptu."
            )
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.group.groupName}: {self.foodTag}"


class Steps(models.Model):
    food = models.ForeignKey("Foods", on_delete=models.CASCADE, related_name="steps")
    step = models.CharField(max_length=1500, unique=False)
    position = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.step


class Unit(models.Model):
    unit = models.CharField(
        max_length=60,
        unique=True,
        error_messages={"unique": "Táto jednotka už existuje."},
    )

    def __str__(self):
        return self.unit


class Ingredient(models.Model):
    ingredient = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.ingredient


class Url(models.Model):
    food = models.ForeignKey("Foods", on_delete=models.CASCADE, related_name="urls")
    urlname = models.CharField(max_length=255)
    url = models.URLField(max_length=1000, unique=False)

    def __str__(self):
        return self.url


class Ingredients(models.Model):
    food = models.ForeignKey(
        "Foods", on_delete=models.CASCADE, related_name="ingredients"
    )
    units = models.ManyToManyField(Unit, related_name="units")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ingredientName = models.ManyToManyField(Ingredient, related_name="ingredientName")
    position = models.PositiveIntegerField(default=1)

    # ingreposition = models.DecimalField(max_digits=10, decimal_places=0)
    def __str__(self):
        return self.quantity


def get_upload_path(instance, filename):
    return "/".join(["image", str(instance.upload_folder), filename])


class ImageFood(models.Model):
    food = models.ForeignKey("Foods", on_delete=models.CASCADE, related_name="images")
    upload_folder = models.CharField(max_length=255)
    image = ProcessedImageField(
        upload_to=get_upload_path,
        processors=[
            ResizeToFit(None, 1000)
        ],  # Resize na výšku 1000px, šírka sa dopočíta
        format="JPEG",
        options={"quality": 80},
        blank=True,
        null=True,
    )
    # image = models.ImageField(
    #     blank=True, null=True, upload_to=get_upload_path, verbose_name="Food image"
    # )
    position = models.PositiveIntegerField(default=1)
    thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFill(400, 300)],
        format="WEBP",  # WebP je výrazne menší ako JPEG
        options={"quality": 70},
    )

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.image:
    #         img = Image.open(self.image.path)
    #         if img.height > 1000:
    #             fixed_height = 1000
    #             height_percent = fixed_height / float(img.size[1])
    #             width_size = int(float(img.size[0]) * float(height_percent))
    #             img = img.resize(
    #                 (width_size, fixed_height), PIL.Image.Resampling.LANCZOS
    #             )
    #             img.save(self.image.path, optimize=True, quality=80)

    def __str__(self):
        return self.upload_folder or f"Image for {self.food.name}"

    def __unicode__(self):
        return self.upload_folder

    def image_img(self):
        if self.image:
            return '<img src="%s" width="50" height="50" />' % self.image.url
        else:
            return "(Sin imagen)"

    image_img.short_description = "Thumb"
    image_img.allow_tags = True

    # def delete(self, *args, **kwargs):
    #     """Delete image file and clean up folder if empty"""
    #     if self.image and os.path.isfile(self.image.path):
    #         file_path = self.image.path
    #         folder = os.path.dirname(file_path)

    #         # delete the file
    #         os.remove(file_path)

    #         # if folder is now empty, remove it
    #         if not os.listdir(folder):
    #             shutil.rmtree(folder)

    #     super().delete(*args, **kwargs)


@receiver(post_delete, sender=ImageFood)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        file_path = instance.image.path
        folder = os.path.dirname(file_path)

        os.remove(file_path)

        if not os.listdir(folder):
            shutil.rmtree(folder)


def remove_accents(self, text):
    import unicodedata

    nfkd_form = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


class Foods(models.Model):
    name = models.CharField(max_length=60)
    date = models.DateTimeField()
    foodTags = models.ManyToManyField(FoodTags, related_name="foodTags")
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="foods")
    search_name = models.CharField(
        max_length=60, editable=False, db_index=True, blank=True
    )

    def __str__(self):
        return self.name

    def remove_accents(self, text):
        if not text:
            return ""
        nfkd_form = unicodedata.normalize("NFKD", text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def save(self, *args, **kwargs):
        # Pri každom uložení receptu si pripravíme "hľadací" text
        if self.name:
            self.search_name = self.remove_accents(self.name.lower())
        super().save(*args, **kwargs)


class PasswordReset(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    reset_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_when = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        #  return self.user
        return f"Password reset for {self.user.email} at {self.created_when}"
