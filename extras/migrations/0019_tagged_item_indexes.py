# Generated by Django 5.0.9 on 2024-09-07 10:51

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("extras", "0018_move_objectchange")]

    operations = [
        migrations.RenameIndex(
            model_name="taggeditem",
            new_name="extras_tagg_content_717743_idx",
            old_fields=("content_type", "object_id"),
        )
    ]