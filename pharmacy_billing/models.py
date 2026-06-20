# Pharmacy billing has been unified into the billing app. Pharmacy invoices and
# payments are now billing.Invoice / billing.Payment rows with
# source_app="pharmacy" (see pharmacy.billing_utils and migration
# pharmacy.0027_unify_pharmacy_billing). This app is kept only to preserve the
# migration history; it defines no models.
