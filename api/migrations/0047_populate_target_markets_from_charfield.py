# api/migrations/0047_populate_target_markets_from_charfield.py

from django.db import migrations

def forwards_populate_m2m(apps, schema_editor):
    """
    Reads the old `target_market` CharField, splits the comma-separated strings
    into individual TargetMarket objects, and creates the M2M links.
    """
    UseCase = apps.get_model("api", "UseCase")
    TargetMarket = apps.get_model("api", "TargetMarket")
    db_alias = schema_editor.connection.alias

    for uc in UseCase.objects.using(db_alias).exclude(target_market__exact='').iterator():
        # Get the messy, comma-separated string from the original CharField
        comma_separated_string = uc.target_market
        
        # Split the string into a list of clean, individual names
        individual_names = [name.strip().title() for name in comma_separated_string.split(',') if name.strip()]

        for clean_name in individual_names:
            # Safely create or fetch the clean TargetMarket object
            market_obj, created = TargetMarket.objects.using(db_alias).get_or_create(name=clean_name)
            
            # Add the relationship to the new ManyToManyField
            uc.target_markets.add(market_obj)

def backwards_noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0046_add_target_market_m2m'), # Depends on the schema change
    ]
    operations = [
        migrations.RunPython(forwards_populate_m2m, backwards_noop),
    ]