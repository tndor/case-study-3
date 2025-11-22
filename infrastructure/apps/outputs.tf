output "backend_url" {
  value = kubernetes_service.backend_svc.status.0.load_balancer.0.ingress.0.hostname
}

output "frontend_url" {
  value = kubernetes_service.frontend_svc.status.0.load_balancer.0.ingress.0.hostname
}