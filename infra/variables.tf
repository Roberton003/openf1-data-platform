variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "state_bucket" {
  description = "GCS bucket for Terraform state"
  type        = string
  default     = "openf1-terraform-state"
}
