locals {
  tags = {
    application = "aidlc-hermes-demo"
    managed_by  = "terraform"
    purpose     = "customer-demo"
  }
}

resource "huaweicloud_vpc" "demo" {
  name = "${var.prefix}-vpc"
  cidr = var.vpc_cidr
  tags = local.tags
}

resource "huaweicloud_vpc_subnet" "demo" {
  name          = "${var.prefix}-subnet"
  cidr          = var.subnet_cidr
  gateway_ip    = var.subnet_gateway
  vpc_id        = huaweicloud_vpc.demo.id
  primary_dns   = "100.125.1.250"
  secondary_dns = "100.125.21.250"
}

resource "huaweicloud_networking_secgroup" "cce" {
  name        = "${var.prefix}-cce-sg"
  description = "AIDLC demo CCE worker security group / AIDLC Demo CCE Worker 安全组"
}

resource "huaweicloud_networking_secgroup_rule" "vpc_internal" {
  security_group_id = huaweicloud_networking_secgroup.cce.id
  direction         = "ingress"
  ethertype         = "IPv4"
  remote_ip_prefix  = var.vpc_cidr
  description       = "CCE and DCS communication inside the demo VPC"
}

resource "huaweicloud_networking_secgroup_rule" "console" {
  security_group_id = huaweicloud_networking_secgroup.cce.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = var.console_node_port
  port_range_max    = var.console_node_port
  remote_ip_prefix  = var.allowed_console_cidr
  description       = "AIDLC demo console / AIDLC Demo 控制台"
}

resource "huaweicloud_vpc_eip" "cluster" {
  name = "${var.prefix}-cluster-eip"
  publicip {
    type = var.eip_type
  }
  bandwidth {
    name        = "${var.prefix}-cluster-bandwidth"
    size        = var.eip_bandwidth_mbps
    share_type  = "PER"
    charge_mode = "traffic"
  }
  tags = local.tags
}

resource "huaweicloud_vpc_eip" "node" {
  name = "${var.prefix}-node-eip"
  publicip {
    type = var.eip_type
  }
  bandwidth {
    name        = "${var.prefix}-node-bandwidth"
    size        = var.eip_bandwidth_mbps
    share_type  = "PER"
    charge_mode = "traffic"
  }
  tags = local.tags
}

resource "huaweicloud_cce_cluster" "demo" {
  name                   = "${var.prefix}-cce"
  cluster_type           = "VirtualMachine"
  flavor_id              = var.cluster_flavor
  vpc_id                 = huaweicloud_vpc.demo.id
  subnet_id              = huaweicloud_vpc_subnet.demo.id
  security_group_id      = huaweicloud_networking_secgroup.cce.id
  container_network_type = "overlay_l2"
  container_network_cidr = "172.16.0.0/16"
  service_network_cidr   = "10.247.0.0/16"
  authentication_mode    = "rbac"
  eip                    = huaweicloud_vpc_eip.cluster.address
  description            = "Single-node CCE cluster for the AIDLC customer demo"
}

resource "random_password" "node" {
  length           = 20
  special          = true
  override_special = "!@#-_"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

resource "huaweicloud_cce_node" "demo" {
  cluster_id        = huaweicloud_cce_cluster.demo.id
  name              = "${var.prefix}-worker"
  flavor_id         = var.node_flavor
  availability_zone = var.availability_zone
  subnet_id         = huaweicloud_vpc_subnet.demo.id
  os                = var.node_os
  password          = random_password.node.result
  eip_id            = huaweicloud_vpc_eip.node.id
  runtime           = "containerd"

  root_volume {
    size       = 40
    volumetype = "GPSSD"
  }

  data_volumes {
    size       = 100
    volumetype = "GPSSD"
  }

  tags = local.tags
}

resource "random_password" "redis" {
  length           = 24
  special          = true
  override_special = "-_"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

data "huaweicloud_dcs_flavors" "single" {
  cache_mode = "single"
  capacity   = 0.125
}

locals {
  dcs_billable_flavors = [
    for candidate in data.huaweicloud_dcs_flavors.single.flavors :
    candidate
    if contains(candidate.charging_modes, "Hourly") && !strcontains(candidate.name, ".free.")
  ]
  dcs_flavor_name = length(local.dcs_billable_flavors) > 0 ? local.dcs_billable_flavors[0].name : data.huaweicloud_dcs_flavors.single.flavors[0].name
}

resource "huaweicloud_dcs_instance" "redis" {
  name               = "${var.prefix}-redis"
  engine             = "Redis"
  engine_version     = "6.0"
  capacity           = data.huaweicloud_dcs_flavors.single.capacity
  flavor             = local.dcs_flavor_name
  availability_zones = [var.availability_zone]
  password           = random_password.redis.result
  vpc_id             = huaweicloud_vpc.demo.id
  subnet_id          = huaweicloud_vpc_subnet.demo.id
  security_group_id  = huaweicloud_networking_secgroup.cce.id
  ssl_enable         = false
  charging_mode      = "postPaid"
  description        = "AIDLC run state, event stream and evidence store"
  tags               = local.tags
}

resource "huaweicloud_swr_organization" "demo" {
  name = var.swr_organization
}

resource "huaweicloud_swr_repository" "platform" {
  organization = huaweicloud_swr_organization.demo.name
  name         = var.platform_repository
  description  = "AIDLC Hermes platform image / AIDLC Hermes 平台镜像"
  category     = "framework_app"
  is_public    = false
}

resource "huaweicloud_swr_repository" "application" {
  organization = huaweicloud_swr_organization.demo.name
  name         = var.application_repository
  description  = "Images built by the AIDLC Deploy Worker / AIDLC Deploy Worker 构建的镜像"
  category     = "app_server"
  is_public    = false
}
