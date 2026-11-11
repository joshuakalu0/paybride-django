from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PayBridgeSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_email", models.EmailField(max_length=254)),
                ("gateway", models.CharField(choices=[("paystack", "Paystack"), ("flutterwave", "Flutterwave"), ("stripe", "Stripe")], max_length=32)),
                ("gateway_subscription_id", models.CharField(max_length=255, unique=True)),
                ("plan_id", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("ACTIVE", "Active"), ("TRIALING", "Trialing"), ("PAST_DUE", "Past due"), ("CANCELLED", "Cancelled"), ("INCOMPLETE", "Incomplete")], default="PENDING", max_length=24)),
                ("trial_end", models.DateTimeField(blank=True, null=True)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("cancel_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PayBridgeTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=255, unique=True)),
                ("gateway", models.CharField(choices=[("paystack", "Paystack"), ("flutterwave", "Flutterwave"), ("stripe", "Stripe")], max_length=32)),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("currency", models.CharField(default="NGN", max_length=8)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("SUCCESS", "Success"), ("FAILED", "Failed"), ("REFUNDED", "Refunded")], default="PENDING", max_length=16)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("webhook_payload", models.JSONField(blank=True, null=True)),
                ("webhook_received_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="paybridgesubscription",
            index=models.Index(fields=["gateway", "status"], name="paybridge_d_gateway_ae4edf_idx"),
        ),
        migrations.AddIndex(
            model_name="paybridgesubscription",
            index=models.Index(fields=["customer_email", "status"], name="paybridge_d_custome_2d1776_idx"),
        ),
        migrations.AddIndex(
            model_name="paybridgetransaction",
            index=models.Index(fields=["gateway", "status", "created_at"], name="paybridge_d_gateway_57bec2_idx"),
        ),
        migrations.AddIndex(
            model_name="paybridgetransaction",
            index=models.Index(fields=["email", "created_at"], name="paybridge_d_email_72ac8d_idx"),
        ),
    ]
