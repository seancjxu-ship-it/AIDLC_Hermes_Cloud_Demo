# AIDLC Hermes Cloud Demo

> Idioma: **Português (Brasil)** | [English / 中文](README.md)

Uma estrutura executável de fábrica de software AIDLC na Huawei Cloud. A solução conecta um repositório Git do cliente a um Orquestrador no estilo Hermes, Workers especializados por função, Skills OpenSpec/AIDLC, ModelArts Studio MaaS GLM-5.2, DCS Redis, SWR e CCE.

O objetivo não é apresentar um produto completo de programação. A demonstração mostra como abrir o ciclo de engenharia de ponta a ponta, reutilizar práticas AIDLC e consumir o MaaS da Huawei Cloud durante desenvolvimento e revisão.

## O que é executado de forma real

1. Leitura do requisito e dos artefatos OpenSpec diretamente do Git.
2. Criação, pelo Orquestrador, de um grafo de tarefas com controles de aprovação.
3. O Dev Agent chama o GLM-5.2, altera o código-fonte, executa verificações, cria o commit e envia uma branch de funcionalidade.
4. Os Agents de QA e Review executam testes determinísticos, compilação, varredura de segredos e revisão assistida por modelo.
5. O Deploy Agent cria um Job Kaniko, publica a imagem no SWR, resolve o digest real, implanta um Preview específico da execução no CCE e executa smoke tests.
6. O sistema cria um Pull Request e fecha um Pacote de Evidências com data e hora. A decisão de merge continua sendo humana.

## Arquitetura de execução

- `aidlc-api`: API REST, Basic Auth, console, visualização de eventos/evidências e proxy reverso autenticado para o Preview.
- `hermes-orchestrator`: carregamento de Skills, DAG de tarefas, transições de estado, roteamento e decisão final.
- `hermes-sf-dev`: alteração assistida por GLM, verificações locais, commit e push no Git.
- `hermes-sf-qa`: testes determinísticos do repositório e evidências de aceitação.
- `hermes-sf-review`: compilação, varredura de segredos, revisão dos arquivos alterados e controle de política.
- `hermes-sf-deploy`: Kaniko, SWR, Preview no CCE fixado por digest, smoke tests e Pull Request.
- `DCS Redis`: estado das execuções, filas, eventos, evidências e histórico.

A região `sa-brazil-1` hospeda os planos de execução e dados. A região `ap-southeast-1`, em Hong Kong, hospeda o MaaS GLM-5.2.

## Contrato de entrada do cliente

O cliente deve preparar:

- URL do repositório Git e branch base.
- Token fine-grained do GitHub com **Contents: Read and write** e **Pull requests: Read and write**.
- Arquivo de requisito, por exemplo `demo/GITHUB_ISSUE.md`.
- `sdd/spec.md`, `sdd/design.md`, `sdd/tasks.yaml` e os testes pertencentes ao repositório.
- Skills opcionais do cliente em `.hermes/skills/`.
- Política de aprovação humana para merge e liberação.

A demonstração atual não recebe requisitos livres diretamente pela interface. O requisito deve estar no Git para ser versionado e auditável.

## API

- `GET /health` — saúde da plataforma.
- `GET /api/architecture` — arquitetura implantada.
- `GET /api/dashboard` — histórico, taxa de sucesso, uso de tokens, duração e contagem de eventos.
- `POST /api/runs` — inicia uma execução AIDLC completa.
- `GET /api/runs/{run_id}` — estado e decisão final.
- `GET /api/runs/{run_id}/events` — eventos internos com data e hora.
- `GET /api/runs/{run_id}/evidence` — Pacote de Evidências estruturado.
- `GET /preview/{run_id}/{path}` — proxy autenticado para o Preview específico da execução.

Exemplo:

```json
{
  "repository": "https://github.com/<usuario>/AIDLC_Simple_Order_Demo",
  "base_branch": "main",
  "requirement_file": "demo/GITHUB_ISSUE.md",
  "execution_mode": "live",
  "skill_profile": "openspec-core+aidlc-demo",
  "model": "glm-5.2"
}
```

## Implantação e destruição com um comando

O pacote cria uma VPC, sub-rede, grupo de segurança, cluster CCE, worker CCE/ECS, EIPs, DCS Redis e repositórios privados no SWR. Em seguida, constrói a imagem da plataforma, envia-a ao SWR e instala os seis Pods com Helm.

Pré-requisitos: Windows PowerShell e acesso de saída à internet. O comando prepara automaticamente Terraform, kubectl, Helm, KooCLI e Docker Desktop.

Execute na raiz do repositório:

```powershell
git clone https://github.com/seancjxu-ship-it/AIDLC_Hermes_Cloud_Demo.git
Set-Location ".\AIDLC_Hermes_Cloud_Demo"
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1"
```

O script solicita de forma interativa o repositório da aplicação do usuário, Huawei Cloud AK/SK, MaaS API Key e o token GitHub do próprio usuário.

Login inicial da demonstração: `demo / huawei123`.

> **Importante:** restrinja o acesso ao Console com `-AllowedConsoleCidr` e altere a credencial padrão antes de qualquer demonstração compartilhada. O ambiente não deve ser exposto publicamente com a senha padrão.

O script de destruição exige o registro local da implantação e a confirmação explícita `DESTROY`. Ele remove workloads de Preview, namespace, tags de imagem no SWR e os recursos gerenciados pelo mesmo estado Terraform.

Guia completo: [Implantação com um comando — pt-BR](docs/IMPLANTACAO_UM_COMANDO_PT_BR.md).

## Documentação em português

- [Guia do cliente e roteiro da demonstração](docs/GUIA_DO_CLIENTE_PT_BR.md)
- [Implantação e destruição com um comando](docs/IMPLANTACAO_UM_COMANDO_PT_BR.md)
- [Catálogo de Skills e mapeamento por etapa](docs/CATALOGO_DE_SKILLS_PT_BR.md)
- [Infraestrutura Terraform](infra/terraform/README_PT_BR.md)
- [Projeto técnico detalhado — English / 中文](docs/AIDLC_DETAILED_DESIGN_CN_EN.md)

## Desenvolvimento local

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
```

```powershell
docker compose up --build
```

## Limites da demonstração

Este repositório foi criado para uma demonstração de baixo custo: um worker CCE e Redis de nó único. Ele não inclui alta disponibilidade multi-AZ, backup, recuperação de desastre ou integração de identidade em nível de produção.

Antes de uso em produção, projete pelo menos:

- identidade corporativa e controle de acesso baseado em função;
- gestão e rotação de segredos;
- alta disponibilidade, backup e recuperação de desastre;
- observabilidade, retenção de logs e auditoria;
- isolamento de rede e regras de saída;
- políticas de custo, capacidade e ciclo de vida dos recursos.

