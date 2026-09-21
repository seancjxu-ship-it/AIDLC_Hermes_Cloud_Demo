from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeliveryAssetsTest(unittest.TestCase):
    def test_one_click_entrypoints_exist(self):
        for relative_path in (
            "deploy-demo.ps1",
            "scripts/cloud/deploy.ps1",
            "scripts/cloud/preflight.ps1",
            "scripts/cloud/bootstrap-tools.ps1",
            "scripts/cloud/status.ps1",
            "scripts/cloud/destroy.ps1",
            "infra/terraform/main.tf",
            "deploy/helm/aidlc-factory/Chart.yaml",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_one_click_deploy_prepares_workstation(self):
        launcher = (ROOT / "deploy-demo.ps1").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts/cloud/deploy.ps1").read_text(encoding="utf-8")
        preflight = (ROOT / "scripts/cloud/preflight.ps1").read_text(encoding="utf-8")
        bootstrap = (ROOT / "scripts/cloud/bootstrap-tools.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn('"scripts\\cloud\\deploy.ps1"', launcher)
        self.assertIn("@PSBoundParameters", launcher)
        self.assertIn('"preflight.ps1"', deploy)
        self.assertIn("Docker%20Desktop%20Installer.exe", preflight)
        self.assertIn("Install-DockerDesktopForCurrentUser", preflight)
        self.assertIn("huaweicloud-cli-windows-amd64.zip", bootstrap)
        self.assertIn('"hcloud.exe"', bootstrap)

    def test_terraform_credentials_use_provider_environment_names(self):
        common = (ROOT / "scripts/cloud/common.ps1").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts/cloud/deploy.ps1").read_text(encoding="utf-8")
        destroy = (ROOT / "scripts/cloud/destroy.ps1").read_text(encoding="utf-8")

        for variable_name in (
            "HW_ACCESS_KEY",
            "HW_SECRET_KEY",
            "HW_REGION_NAME",
            "HUAWEICLOUD_ACCESS_KEY",
            "HUAWEICLOUD_SECRET_KEY",
            "HUAWEICLOUD_REGION",
        ):
            self.assertIn(variable_name, common)
        self.assertIn("Set-HuaweiCloudCredentialEnvironment", deploy)
        self.assertIn("Set-HuaweiCloudCredentialEnvironment", destroy)
        self.assertIn('EnvironmentAliases @("HUAWEICLOUD_SECRET_KEY")', deploy)
        self.assertIn('EnvironmentAliases @("HUAWEICLOUD_SECRET_KEY")', destroy)

    def test_helm_chart_uses_release_namespace(self):
        manifest = (ROOT / "deploy/helm/aidlc-factory/templates/runtime.yaml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("namespace: aidlc-demo", manifest)
        self.assertIn(".Release.Namespace", manifest)
        self.assertNotIn("kind: Namespace", manifest)

    def test_secrets_and_state_are_gitignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (".env", "terraform.tfstate*", ".terraform/", ".aidlc-deployment.json"):
            self.assertIn(pattern, ignored)

    def test_terraform_covers_required_demo_resources(self):
        terraform = (ROOT / "infra/terraform/main.tf").read_text(encoding="utf-8")
        for resource_type in (
            "huaweicloud_vpc",
            "huaweicloud_cce_cluster",
            "huaweicloud_cce_node",
            "huaweicloud_dcs_instance",
            "huaweicloud_swr_repository",
        ):
            self.assertIn(resource_type, terraform)
        self.assertIn('!strcontains(candidate.name, ".free.")', terraform)
        self.assertIn("flavor             = local.dcs_flavor_name", terraform)


if __name__ == "__main__":
    unittest.main()
