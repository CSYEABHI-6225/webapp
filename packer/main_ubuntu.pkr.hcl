packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.1, <2.0.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

variable "region" {
  type    = string
}

variable "aws_access_key" {
  type      = string
  sensitive = true
}

variable "aws_secret_key" {
  type      = string
  sensitive = true
}

variable "instance_type" {
  type    = string
}

variable "ami_name" {
  type    = string
}

variable "ssh_keypair" {
  type    = string
}

source "amazon-ebs" "ubuntu" {
  ami_name = "${replace(var.ami_name, "/[^a-zA-Z0-9-]/", "")}-${formatdate("YYYYMMDDHHmmss", timestamp())}"
  instance_type    = var.instance_type
  region           = var.region
  ssh_username     = "ubuntu"
  ssh_timeout      = "15m"
  ssh_interface    = "public_ip"
  access_key       = var.aws_access_key
  secret_key       = var.aws_secret_key

  source_ami_filter {
    filters = {
      name                = "ubuntu/images/*ubuntu-jammy-22.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    owners      = ["099720109477"]
    most_recent = true
  }
}
build {
  sources = ["source.amazon-ebs.ubuntu"]

  provisioner "file" {
  source      = "./webapp"  // Replace with the actual full path
  destination = "/tmp/webapp"
}

  provisioner "file"{
    source    = "./webapp/.env"
    destination = "/tmp/webapp/.env"
  }

 provisioner "shell" {
  scripts = [
    "${path.root}/scripts/install_dependencies.sh",
    "${path.root}/scripts/install_mysql.sh",
    "${path.root}/scripts/create_user.sh",
    "${path.root}/scripts/setup_python_venv.sh",
    "${path.root}/scripts/config_systemd.sh"
  ]
}
}
