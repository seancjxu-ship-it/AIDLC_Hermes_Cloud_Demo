output "region" {
  value       = var.region
  description = "Deployment region / 部署区域"
}

output "cluster_id" {
  value       = huaweicloud_cce_cluster.demo.id
  description = "CCE cluster ID / CCE 集群 ID"
}

output "cluster_name" {
  value       = huaweicloud_cce_cluster.demo.name
  description = "CCE cluster name / CCE 集群名称"
}

output "kube_config_raw" {
  value       = huaweicloud_cce_cluster.demo.kube_config_raw
  description = "Temporary deployment kubeconfig; never commit it. / 临时部署 kubeconfig，禁止提交。"
  sensitive   = true
}

output "node_public_ip" {
  value       = huaweicloud_cce_node.demo.public_ip
  description = "Public IP used by the demo console / Demo Console 使用的公网 IP"
}

output "node_server_id" {
  value       = huaweicloud_cce_node.demo.server_id
  description = "Underlying ECS server ID / 底层 ECS ID"
}

output "redis_url" {
  value       = "redis://:${random_password.redis.result}@${huaweicloud_dcs_instance.redis.domain_name}:${huaweicloud_dcs_instance.redis.port}/0"
  description = "Password-bearing Redis URL consumed by Kubernetes / Kubernetes 使用的含密码 Redis URL"
  sensitive   = true
}

output "swr_registry" {
  value       = "swr.${var.region}.myhuaweicloud.com"
  description = "SWR registry host / SWR Registry 地址"
}

output "platform_image_repository" {
  value       = "swr.${var.region}.myhuaweicloud.com/${var.swr_organization}/${var.platform_repository}"
  description = "AIDLC platform repository / AIDLC 平台镜像仓库"
}

output "application_image_repository" {
  value       = "swr.${var.region}.myhuaweicloud.com/${var.swr_organization}/${var.application_repository}"
  description = "Application image repository / 应用镜像仓库"
}

output "console_url" {
  value       = "http://${huaweicloud_cce_node.demo.public_ip}:${var.console_node_port}"
  description = "Demo console URL after Helm installation / Helm 安装完成后的 Demo Console 地址"
}
