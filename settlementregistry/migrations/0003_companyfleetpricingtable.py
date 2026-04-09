from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("settlementregistry", "0002_globalsettlementconfig"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyFleetPricingTable",
            fields=[
                ("pricing_table_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company_id", models.UUIDField()),
                ("fleet_id", models.UUIDField()),
                ("box_sale_unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("box_purchase_unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("overtime_fee", models.DecimalField(decimal_places=2, max_digits=12)),
            ],
            options={
                "ordering": ("pricing_table_id",),
            },
        ),
        migrations.AddConstraint(
            model_name="companyfleetpricingtable",
            constraint=models.UniqueConstraint(
                fields=("company_id", "fleet_id"),
                name="unique_company_fleet_pricing_table",
            ),
        ),
    ]
