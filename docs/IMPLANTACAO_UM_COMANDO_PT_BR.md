# Implantação e destruição com um comando

> [Voltar ao README em português](../README_PT_BR.md) | [English / 中文](ONE_CLICK_DEPLOYMENT_CN_EN.md)

Este guia foi mantido propositalmente direto. O comando de implantação prepara as ferramentas da estação de trabalho, cria os recursos na Huawei Cloud e implanta toda a demonstração AIDLC.

## Antes de começar

Você precisa apenas de:

- Windows 10/11 com Windows PowerShell 5.1 ou PowerShell 7.
- Acesso de saída à internet.
- Conta Huawei Cloud com permissões e cotas para criar VPC, EIP, CCE, ECS/EVS, DCS e SWR em `sa-brazil-1`.
- Uma API Key do ModelArts Studio MaaS GLM-5.2 em Hong Kong.
- Seu próprio repositório de aplicação no GitHub e um token fine-grained.

Não é necessário instalar manualmente Terraform, kubectl, Helm, KooCLI ou Docker Desktop.

## 1. Clonar o repositório da estrutura

Abra o PowerShell e confirme se o Git está disponível:

```powershell
git --version
```

Se o Git não for encontrado, instale-o e abra novamente o PowerShell:

```powershell
winget install --id Git.Git -e --source winget
```

Clone a estrutura em um caminho local curto:

```powershell
New-Item -ItemType Directory -Path "C:\aidlc" -Force | Out-Null
Set-Location "C:\aidlc"
git clone https://github.com/seancjxu-ship-it/AIDLC_Hermes_Cloud_Demo.git
Set-Location "C:\aidlc\AIDLC_Hermes_Cloud_Demo"
```

O repositório da estrutura é público; esta operação de clone não exige token do GitHub.

Se o repositório já existir localmente, atualize-o em vez de cloná-lo novamente:

```powershell
Set-Location "C:\aidlc\AIDLC_Hermes_Cloud_Demo"
git pull --ff-only
```

## 2. Preparar a entrada GitHub do cliente

O repositório acima contém o programa de implantação. O repositório da aplicação é outro repositório, no qual os Agents farão alterações.

1. Abra [AIDLC_Simple_Order_Demo](https://github.com/seancjxu-ship-it/AIDLC_Simple_Order_Demo) no navegador.
2. Clique em **Fork** e crie uma cópia na conta GitHub do usuário que fará a implantação.
3. Anote a URL do fork, por exemplo `https://github.com/<usuario>/AIDLC_Simple_Order_Demo`.
4. No GitHub, abra **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**.
5. Em **Resource owner**, selecione o usuário da implantação; escolha **Only select repositories** e selecione o fork criado.
6. Defina **Contents: Read and write** e **Pull requests: Read and write**; gere o token e armazene-o com segurança.

O token pertence ao usuário que realiza a implantação e deve ser limitado ao fork desse usuário. Nunca use nem compartilhe o token do proprietário do repositório original.

## 3. Implantar com um comando

Na raiz do repositório, execute:

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1"
```

O comando solicita estes valores:

| Entrada | Valor esperado |
|---|---|
| Repositório da aplicação do cliente | URL do fork do próprio usuário, por exemplo `https://github.com/<usuario>/AIDLC_Simple_Order_Demo` |
| Huawei Cloud AK/SK | Credenciais com as permissões necessárias na região do Brasil |
| MaaS API Key | API Key do GLM-5.2 em Hong Kong |
| GitHub Token | Token do próprio usuário, limitado ao repositório da aplicação |

O token GitHub deve conceder **Contents: Read and write** e **Pull requests: Read and write** no repositório da aplicação.

Exemplo da sequência de entrada; substitua todos os valores entre `< >`:

```text
Customer application GitHub repository URL:
https://github.com/<usuario>/AIDLC_Simple_Order_Demo

Huawei Cloud Access Key:
<sua-huawei-cloud-ak>

Huawei Cloud Secret Key:
<sua-huawei-cloud-sk>

ModelArts MaaS API Key (Hong Kong GLM-5.2):
<sua-maas-api-key>

GitHub Token:
<seu-token-fine-grained>
```

As entradas SK, MaaS API Key e GitHub Token ficam ocultas durante a digitação. Elas são injetadas no ambiente de implantação, mas não são gravadas no repositório Git.

## O que o comando faz automaticamente

1. Baixa Terraform, kubectl, Helm e Huawei Cloud KooCLI para o diretório `.tools`, ignorado pelo Git.
2. Quando necessário, baixa e instala Docker Desktop para o usuário atual, inicia o aplicativo e aguarda o Docker Engine.
3. Cria VPC, sub-rede, grupo de segurança, EIPs, CCE, um worker/ECS, DCS Redis e repositórios privados SWR no Brasil.
4. Constrói a imagem da plataforma AIDLC e envia-a ao SWR.
5. Implanta os Pods API, Orchestrator, Dev, QA, Review e Deploy usando Helm.
6. Verifica todos os Pods e o endpoint público de saúde.

Na primeira instalação, o Docker Desktop pode exibir termos de licença, configuração do WSL 2, aprovação de administrador ou solicitação de reinicialização do Windows. Conclua a ação mostrada pelo sistema e execute o mesmo comando novamente após a reinicialização, se necessário.

## Resultado esperado

A saída final informa:

- URL do Console: `http://<eip-do-no>:30080`
- Login inicial: `demo / huawei123`
- Região de execução: Brasil `sa-brazil-1`
- MaaS: Hong Kong `ap-southeast-1`, modelo `glm-5.2`

> **Segurança:** o login padrão existe somente para a demonstração. Restrinja o Console ao IP público do cliente e altere a credencial antes de compartilhar o ambiente.

## Verificar o estado

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\status.ps1"
```

Verifique, no mínimo:

- Pods da plataforma em estado saudável;
- endpoint `/health` acessível;
- URL do Console restrita ao CIDR planejado;
- conectividade com Redis, SWR e MaaS;
- ausência de credenciais nos arquivos rastreados pelo Git.

## Destruir a demonstração

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\destroy.ps1"
```

Digite `DESTROY` quando solicitado. O comando remove workloads de Preview, namespace Kubernetes, tags de imagem no SWR e todos os recursos da demonstração gerenciados pelo Terraform.

O script depende do registro local da implantação e do mesmo estado Terraform. Proteja e preserve a estação de trabalho até a destruição ser concluída.

## Parâmetros opcionais

Informar diretamente o fork do usuário:

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1" -RepositoryUrl "https://github.com/<usuario>/AIDLC_Simple_Order_Demo"
```

Restringir o Console ao IP público do cliente:

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1" -AllowedConsoleCidr "203.0.113.10/32"
```

Em estações corporativas gerenciadas, a equipe de TI pode instalar o Docker Desktop previamente e desativar a instalação automática:

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1" -SkipDockerDesktopInstall
```

## Solução de problemas

### Git ou GitHub

- Confirme a URL do fork e a branch `main`.
- Confirme que o token pertence ao usuário da implantação e tem acesso somente ao fork necessário.
- Verifique as permissões **Contents** e **Pull requests**.

### Huawei Cloud

- Verifique as cotas de EIP, ECS/EVS, CCE e DCS em `sa-brazil-1`.
- Confirme que AK/SK possuem as permissões exigidas.
- Use `scripts\cloud\status.ps1` para coletar o estado antes de repetir a implantação.

### Docker Desktop

- Conclua a configuração do WSL 2 e reinicie o Windows quando solicitado.
- Confirme que o Docker Engine está em execução antes de repetir o comando.

### MaaS

- Confirme que a API Key pertence ao serviço GLM-5.2 em `ap-southeast-1`.
- Não inclua a API Key em logs, capturas de tela ou chamados de suporte.

## Limites da demonstração

Este é um ambiente de baixo custo com um worker CCE e Redis de nó único. Não inclui alta disponibilidade multi-AZ, backup, recuperação de desastre ou integração de identidade em nível de produção.

