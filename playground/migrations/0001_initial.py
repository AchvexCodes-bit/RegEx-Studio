# Generated for RegEx Studio user workspace.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="SavedPattern",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("pattern", models.CharField(max_length=512)),
                ("flags", models.CharField(blank=True, default="g", max_length=8)),
                ("replacement", models.CharField(blank=True, default="", max_length=512)),
                ("test_input", models.TextField(blank=True)),
                ("is_favorite", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_regex_patterns", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-updated_at", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="savedpattern",
            constraint=models.UniqueConstraint(fields=("owner", "name"), name="unique_saved_pattern_name_per_user"),
        ),
    ]
