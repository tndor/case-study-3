# Define local subnet configurations
locals {
    public_subnet_configuration = {
        public_1 = {
            name       = "public_subnet-1"
            cidr_block = "10.0.1.0/24"
            az         = "${var.aws_region}a"
        }
        public_2 = {
            name       = "public_subnet-2"
            cidr_block = "10.0.2.0/24"
            az         = "${var.aws_region}b"
        }
    }

    private_subnet_configuration = {
        private_1 = {
            name       = "private_subnet-1"
            cidr_block = "10.0.10.0/24"
            az         = "${var.aws_region}a"
        }
        private_2 = {
            name       = "private_subnet-2"
            cidr_block = "10.0.20.0/24"
            az         = "${var.aws_region}b"
        }
    }
}

# Create a VPC
resource "aws_vpc" "main" {
    cidr_block = var.vpc_cidr
    
    tags = {
        Name = "main_vpc"
    }
}

# Create an Internet Gateway
resource "aws_internet_gateway" "gw" {
    vpc_id = aws_vpc.main.id

    tags = {
        Name = "main_internet_gateway"
    }
}

# Create a NAT Gateway
resource "aws_eip" "nat" {
    domain = "vpc"

    tags = {
        Name = "nat_eip"
    }
}

resource "aws_nat_gateway" "nat" {
    allocation_id = aws_eip.nat.id
    subnet_id     = aws_subnet.public["public_1"].id

    tags = {
        Name = "main_nat_gateway"
    }
}

# Create Public and Private Subnets
resource "aws_subnet" "public" {
for_each = local.public_subnet_configuration
    vpc_id            = aws_vpc.main.id
    cidr_block        = each.value.cidr_block
    map_public_ip_on_launch = true
    availability_zone = each.value.az
    tags = {
        Name = each.value.name
    }
}

resource "aws_subnet" "private" {
for_each = local.private_subnet_configuration
    vpc_id            = aws_vpc.main.id
    cidr_block        = each.value.cidr_block
    availability_zone = each.value.az
    tags = {
        Name = each.value.name
    }
}

# Create Route Tables
resource "aws_route_table" "public" {
    vpc_id = aws_vpc.main.id

    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.gw.id
    }
    tags = {
        Name = "public_route_table"
    }
}

resource "aws_route_table" "private" {
    vpc_id = aws_vpc.main.id

    route {
        cidr_block     = "0.0.0.0/0"
        nat_gateway_id = aws_nat_gateway.nat.id
    }
    tags = {
        Name = "private_route_table"
    }
}

# Associate Subnets with Route Tables
resource "aws_route_table_association" "public" {
for_each = aws_subnet.public
    subnet_id      = each.value.id
    route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
for_each = aws_subnet.private
    subnet_id      = each.value.id
    route_table_id = aws_route_table.private.id
}