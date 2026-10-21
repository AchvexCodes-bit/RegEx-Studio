from django.conf import settings
from django.db import models


class SavedPattern(models.Model):
    """A private, account-owned native-regex workspace item."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_regex_patterns",
    )
    name = models.CharField(max_length=80)
    pattern = models.CharField(max_length=512)
    flags = models.CharField(max_length=8, blank=True, default="g")
    replacement = models.CharField(max_length=512, blank=True, default="")
    test_input = models.TextField(blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "name"),
                name="unique_saved_pattern_name_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner})"
