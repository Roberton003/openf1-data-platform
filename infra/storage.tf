# GCS bucket for Terraform state backend
resource "google_storage_bucket" "terraform_state" {
  name          = var.state_bucket
  location      = var.region
  force_destroy = false
  storage_class = "STANDARD"
  versioning {
    enabled = true
  }
}
