# Generated by Django 5.2.1 on 2025-06-15 05:18

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('health_and_wellness', 'Health_And_Wellness'), ('tech', 'Tech')], max_length=50, unique=True)),
                ('display_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='NameCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='NameTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='NewsLetter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='PlanModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('free', 'Free'), ('paid', 'Paid'), ('freemium', 'Freemium')], max_length=20, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Support',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=50)),
                ('message', models.TextField()),
                ('email', models.EmailField(max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Name',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=20)),
                ('extension', models.CharField(choices=[('all_extensions', 'All_extensions'), ('com', 'Com'), ('co', 'Co'), ('io', 'Io'), ('ai', 'Ai')], default='all_extensions', max_length=20)),
                ('domain_list', models.CharField(choices=[('all_list', 'All_list'), ('pending_delete', 'Pending_delete'), ('deleted', 'Deleted'), ('marketplace', 'Marketplace')], default='deleted', max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('available', 'Available'), ('taken', 'Taken')], default='available', max_length=20, unique=True)),
                ('length', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)])),
                ('syllables', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)])),
                ('competition', models.CharField(max_length=50)),
                ('difficulty', models.CharField(max_length=50)),
                ('is_top_rated', models.BooleanField(default=False)),
                ('drop_date', models.DateField(default=django.utils.timezone.now, help_text='Default to current time if not specified')),
                ('drop_time', models.DateTimeField(default=django.utils.timezone.now, help_text='Default to current time if not specified')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ManyToManyField(related_name='category', to='api.namecategory')),
                ('tag', models.ManyToManyField(related_name='tag', to='api.nametag')),
            ],
        ),
        migrations.CreateModel(
            name='UseCases',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('case_title', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=200)),
                ('difficulty', models.CharField(choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('hard', 'Hard')], max_length=20, unique=True)),
                ('competition', models.CharField(choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('hard', 'Hard')], max_length=20, unique=True)),
                ('Target_market', models.CharField(max_length=20, unique=True)),
                ('Revenue_potential', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], max_length=20)),
                ('Recommendation', models.CharField(max_length=20)),
                ('domain', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='case_name', to='api.name')),
            ],
        ),
        migrations.AddField(
            model_name='name',
            name='use_cases',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='use_case', to='api.usecases'),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_logged_in', models.BooleanField(default=False)),
                ('payment_status', models.CharField(default='unpaid', max_length=20)),
                ('subscription_expiry', models.DateField(blank=True, null=True)),
                ('access_tier', models.CharField(default='free', max_length=20)),
                ('isPaid', models.BooleanField(default='False')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
