resource "aws_security_group" "ad" {
  name        = "innovatech-ad-sg"
  description = "Allow RDP and LDAP from Home"
  vpc_id      = aws_vpc.main.id

  # Allow RDP (Remote Desktop) from your home
  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow LDAP (Active Directory) from your home
  ingress {
    from_port   = 389
    to_port     = 389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 389
    to_port     = 389
    protocol    = "tcp"
    security_groups = [aws_eks_cluster.eks.vpc_config[0].cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "domain_controller" {
  ami           = "ami-032c954118df38cd0" 
  instance_type = "t3.medium"
  key_name      = aws_key_pair.deployer_key.key_name
  
  # Must be a PUBLIC subnet so you can reach it from home
  subnet_id                   = aws_subnet.public["public_1"].id
  vpc_security_group_ids      = [aws_security_group.ad.id]
  associate_public_ip_address = true

  user_data = templatefile("${path.module}/templates/setup_ad.ps1.tftpl", {
    ad_domain   = var.ad_domain
    ad_netbios  = var.ad_netbios
    ad_password = var.ad_password
    ad_user = var.ad_user
  })

  tags = {
    Name = "Innovatech-DC"
  }
}
