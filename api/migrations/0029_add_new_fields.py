from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0028_uploadedfile'),  # Replace with your last applied migration
    ]

    operations = [
        migrations.AddField(
            model_name='IdeaOfTheDay',
            name='drop_date',
            field=models.DateField(null=True),  # Temporary nullable
        ),
        migrations.AddField(
            model_name='IdeaOfTheDay',
            name='domain_list',
            field=models.CharField(max_length=50, null=True),  # Temporary nullable
        ),
    ]