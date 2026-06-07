terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_cloud_run_v2_service" "dashboard" {
  name     = "openf1-dashboard"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/openf1-dashboard:latest"
      ports {
        container_port = 8501
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
    }
  }
}

# Allow unauthenticated invocations so the dashboard is public
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.dashboard.location
  project  = google_cloud_run_v2_service.dashboard.project
  service  = google_cloud_run_v2_service.dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
