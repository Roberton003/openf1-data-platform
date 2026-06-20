# GCS bucket for Terraform state backend
#
# Managed by Terraform after bootstrap (see backend.tf).
# Lifecycle rules prevent accidental deletion — state loss is unrecoverable.
resource "google_storage_bucket" "terraform_state" {
  name                        = var.state_bucket
  location                    = var.region
  force_destroy               = false
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}
