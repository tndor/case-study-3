output "dc_public_ip" {
  value = aws_instance.domain_controller.public_ip
}

output "ecr_backend_url" {
  value = aws_ecr_repository.app.repository_url
}