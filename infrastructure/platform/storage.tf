
resource "aws_dynamodb_table" "employees" {
  name         = "Innovatech_Employees"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "username"

  attribute {
    name = "username"
    type = "S"
  }

  tags = {
    Name = "employees-dynamodb-table"
  }
}

# Create ECR repository for backend application
resource "aws_ecr_repository" "backend" {
  name = "innovatech-backend"

  tags = {
    Name = "innovatech-backend"
  }
}

resource "aws_ecr_repository" "frontend" {
  name = "innovatech-frontend"

  tags = {
    Name = "innovatech-frontend"
  }
}