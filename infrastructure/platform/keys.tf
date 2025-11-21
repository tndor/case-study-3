# 1. Generate a secure private key (RSA 4096 bits)
resource "tls_private_key" "my_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# 2. Upload the Public Key to AWS
resource "aws_key_pair" "deployer_key" {
  key_name   = "innovatech-key"
  public_key = tls_private_key.my_key.public_key_openssh
}

# 3. Save the Private Key to my computer (so I can use it!)
resource "local_file" "private_key_pem" {
  content  = tls_private_key.my_key.private_key_pem
  filename = "${path.module}/innovatech-key.pem"
  
  # On Mac/Linux, this sets permissions so only I can read it (required for SSH)
  file_permission = "0400" 
}