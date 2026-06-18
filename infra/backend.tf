# Terraform state backend — GCS with versioning and locking
# Prerequisite: gsutil mb -l us-central1 gs://openf1-terraform-state
terraform {
  backend "gcs" {
    bucket = "openf1-terraform-state"
    prefix = "terraform/state"
  }
}
