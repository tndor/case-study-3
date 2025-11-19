
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