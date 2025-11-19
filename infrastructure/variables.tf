variable "aws_access_key" {
  description = "The AWS access key."
  type        = string
}

variable "aws_secret_key" {
  description = "The AWS secret key."
  type        = string
}

variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
}  

variable "vpc_cidr" {
  description = "The CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}