from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_alter_notification_type"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="notification",
            name="idx_notification_type",
        ),
        migrations.RemoveIndex(
            model_name="notification",
            name="idx_user_read_created",
        ),
        migrations.DeleteModel(
            name="Notification",
        ),
    ]
