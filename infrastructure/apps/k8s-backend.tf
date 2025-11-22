resource "kubernetes_secret" "backend_secrets" {
  metadata {
    name = "hr-backend-secrets"
  }
  data = {
    AWS_ACCESS_KEY_ID     = var.aws_access_key
    AWS_SECRET_ACCESS_KEY = var.aws_secret_key
    AD_PASSWORD           = var.ad_password
  }
}

resource "kubernetes_config_map" "backend_config" {
  metadata {
    name = "hr-backend-config"
  }
  data = {
    AWS_REGION   = var.aws_region
    DYNAMO_TABLE = "Innovatech_Employees"
    AD_DOMAIN    = var.ad_domain
    AD_USER      = var.ad_user
    AD_SERVER_IP = data.terraform_remote_state.platform.outputs.windows_private_ip
  }
}

resource "kubernetes_deployment" "backend" {
  metadata {
    name = "hr-backend"
  }
  spec {
    replicas = 2
    selector {
      match_labels = {
        app = "hr-backend"
      }
    }
    template {
      metadata {
        labels = {
          app = "hr-backend"
        }
      }
      spec {
        container {
          name = "backend"
          # Reading ECR URL from Layer 1
          image = "${data.terraform_remote_state.platform.outputs.ecr_backend_url}:${var.image_tag}"

          env_from {
            config_map_ref {
              name = kubernetes_config_map.backend_config.metadata[0].name
            }
          }

          env {
            name = "AWS_ACCESS_KEY_ID"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secrets.metadata[0].name
                key  = "AWS_ACCESS_KEY_ID"
              }
            }
          }

          env {
            name = "AWS_SECRET_ACCESS_KEY"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secrets.metadata[0].name
                key  = "AWS_SECRET_ACCESS_KEY"
              }
            }
          }

          env {
            name = "AD_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secrets.metadata[0].name
                key  = "AD_PASSWORD"
              }
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "backend_svc" {
  metadata {
    name = "hr-backend-service"
  }
  spec {
    selector = {
      app = "hr-backend"
    }
    type = "LoadBalancer"
    port {
      port        = 80
      target_port = 5000
    }
  }
}