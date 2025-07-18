# Generated by Django 5.2.1 on 2025-06-15 14:10

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UseCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('case_title', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=200)),
                ('difficulty', models.CharField(choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('hard', 'Hard')], max_length=20)),
                ('competition', models.CharField(choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('hard', 'Hard')], max_length=20)),
                ('target_market', models.CharField(max_length=20)),
                ('revenue_potential', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], max_length=20)),
                ('order', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3)])),
            ],
        ),
        migrations.DeleteModel(
            name='Category',
        ),
        migrations.DeleteModel(
            name='Favorite',
        ),
        migrations.DeleteModel(
            name='NewsLetter',
        ),
        migrations.DeleteModel(
            name='PlanModel',
        ),
        migrations.DeleteModel(
            name='Support',
        ),
        migrations.DeleteModel(
            name='Tag',
        ),
        migrations.RenameField(
            model_name='name',
            old_name='domain',
            new_name='domain_name',
        ),
        migrations.AddField(
            model_name='name',
            name='is_favorite',
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveField(
            model_name='name',
            name='category',
        ),
        migrations.AlterField(
            model_name='name',
            name='competition',
            field=models.CharField(blank=True, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='name',
            name='difficulty',
            field=models.CharField(blank=True, choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('hard', 'Hard')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='name',
            name='length',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='name',
            name='syllables',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='name',
            name='tag',
            field=models.ManyToManyField(related_name='names', to='api.nametag'),
        ),
        migrations.AlterField(
            model_name='namecategory',
            name='name',
            field=models.CharField(choices=[('health_and_wellness', 'Health_And_Wellness'), ('tech', 'Tech')], max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='nametag',
            name='name',
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AddField(
            model_name='usecase',
            name='domain_name',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='use_cases_domain', to='api.name'),
        ),
        migrations.AddField(
            model_name='name',
            name='suggested_usecase',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suggested_for', to='api.usecase'),
        ),
        migrations.AlterField(
            model_name='name',
            name='use_cases',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='domain_use_case', to='api.usecase'),
        ),
        migrations.AddField(
            model_name='name',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='names', to='api.namecategory'),
        ),
        migrations.AlterUniqueTogether(
            name='usecase',
            unique_together={('domain_name', 'order')},
        ),
        migrations.DeleteModel(
            name='UseCases',
        ),
    ]
