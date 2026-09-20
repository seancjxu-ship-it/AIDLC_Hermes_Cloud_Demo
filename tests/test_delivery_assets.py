from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeliveryAssetsTest(unittest.TestCase):
    def test_one_click_entrypoints_exist(self):
        for relative_path in (
            "scripts/cloud/deploy.ps1",
            "scripts/cloud/status.ps1",
            "scripts/cloud/destroy.ps1",
            "infra/terraform/main.tf",
            "deploy/helm/aidlc-factory/Chart.yaml",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_helm_chart_uses_release_namespace(self):
        manifest = (ROOT / "deploy/helm/aidlc-factory/templates/runtime.yaml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("namespace: aidlc-demo", manifest)
        self.assertIn(".Release.Namespace", manifest)

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


if __name__ == "__main__":
    unittest.main()

