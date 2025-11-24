# Deploy Prometheus Stack via Helm
resource "helm_release" "prometheus_stack" {
  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  version          = "51.0.0"

  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "2d" # Keep data for only 2 days to save storage
  }
  set {
    name  = "prometheus.prometheusSpec.resources.requests.memory"
    value = "200Mi"
  }
}