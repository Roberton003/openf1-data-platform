# Terraform state backend — GCS with versioning and locking
#
# Bootstrap (run once, before first terraform init):
#   gsutil mb -l us-central1 gs://openf1-terraform-state
#   gsutil versioning set on gs://openf1-terraform-state
#
# After bootstrap:
#   terraform init && terraform plan && terraform apply
#
# The google_storage_bucket.terraform_state resource in storage.tf
# manages the same bucket after first apply. The chicken-egg between
# backend requiring the bucket and Terraform managing it is resolved
# by the one-time manual bootstrap.
terraform {
  backend "gcs" {
    bucket = "openf1-terraform-state"
    prefix = "terraform/state"
  }
}
