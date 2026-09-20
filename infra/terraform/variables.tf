variable "region" {
  description = "Huawei Cloud region for CCE, DCS, SWR and networking. / CCE、DCS、SWR 与网络所在区域。"
  type        = string
  default     = "sa-brazil-1"
}

variable "availability_zone" {
  description = "Availability zone for the demo node and Redis. / Demo 节点与 Redis 所在可用区。"
  type        = string
  default     = "sa-brazil-1b"
}

variable "prefix" {
  description = "Prefix for all resources. / 全部资源的名称前缀。"
  type        = string
  default     = "aidlc-demo"
}

variable "vpc_cidr" {
  description = "VPC CIDR. / VPC 网段。"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_cidr" {
  description = "Worker and Redis subnet CIDR. / Worker 与 Redis 子网网段。"
  type        = string
  default     = "192.168.10.0/24"
}

variable "subnet_gateway" {
  description = "Subnet gateway. / 子网网关。"
  type        = string
  default     = "192.168.10.1"
}

variable "allowed_console_cidr" {
  description = "CIDR allowed to access the demo NodePort. Restrict it for customer use. / 可访问 Demo NodePort 的来源网段，客户环境请收窄。"
  type        = string
  default     = "0.0.0.0/0"
}

variable "console_node_port" {
  description = "Public NodePort of the AIDLC console. / AIDLC Console 对外 NodePort。"
  type        = number
  default     = 30080
}

variable "cluster_flavor" {
  description = "CCE control-plane flavor. / CCE 控制面规格。"
  type        = string
  default     = "cce.s1.small"
}

variable "node_flavor" {
  description = "CCE worker flavor. / CCE Worker 规格。"
  type        = string
  default     = "s7n.large.2"
}

variable "node_os" {
  description = "CCE node operating system supported in the selected region. / 目标区域支持的 CCE 节点操作系统。"
  type        = string
  default     = "Huawei Cloud EulerOS 2.0"
}

variable "eip_type" {
  description = "Regional EIP type. / 区域公网 IP 类型。"
  type        = string
  default     = "5_bgp"
}

variable "eip_bandwidth_mbps" {
  description = "Bandwidth for CCE API and node EIPs. / CCE API 与节点 EIP 带宽。"
  type        = number
  default     = 5
}

variable "swr_organization" {
  description = "SWR organization name. / SWR 组织名。"
  type        = string
  default     = "aidlc-demo"
}

variable "platform_repository" {
  description = "SWR repository for the AIDLC platform image. / AIDLC 平台镜像仓库。"
  type        = string
  default     = "aidlc-factory"
}

variable "application_repository" {
  description = "SWR repository for images built by the Deploy Worker. / Deploy Worker 构建的应用镜像仓库。"
  type        = string
  default     = "order-demo"
}

