# Read the state from the Platform folder
data "terraform_remote_state" "platform" {
  backend = "local"
  config = {
    path = "../platform/terraform.tfstate"
  }
}

# Configure Kubernetes using Layer 1 credentials
provider "kubernetes" {
  host                   = data.terraform_remote_state.platform.outputs.cluster_endpoint
  cluster_ca_certificate = base64decode(data.terraform_remote_state.platform.outputs.cluster_certificate_authority_data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    args        = ["eks", "get-token", "--cluster-name", data.terraform_remote_state.platform.outputs.cluster_name]
    command     = "aws"
  }
}

variable "image_tag" { type = string }