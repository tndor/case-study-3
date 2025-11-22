resource "kubernetes_deployment" "frontend" {
  metadata {
    name = "hr-frontend"
  }
  spec {
    replicas = 2
    selector {
      match_labels = {
        app = "hr-frontend"
      }
    }
    template {
      metadata {
        labels = {
          app = "hr-frontend"
        }
      }
      spec {
        container {
          name  = "frontend"
          image = "${data.terraform_remote_state.platform.outputs.ecr_frontend_url}:${var.image_tag}"
          
          port {
            container_port = 80
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "frontend_svc" {
  metadata {
    name = "hr-frontend-service"
  }
  spec {
    selector = {
      app = "hr-frontend"
    }
    type = "LoadBalancer"
    port {
      port        = 80
      target_port = 80
    }
  }
}