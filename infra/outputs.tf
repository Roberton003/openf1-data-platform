output "state_bucket" {
  description = "GCS bucket for Terraform state"
  value       = google_storage_bucket.terraform_state.name
}

output "state_bucket_url" {
  description = "Full GCS URL for the state bucket"
  value       = google_storage_bucket.terraform_state.url
}

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.dashboard.uri
}
