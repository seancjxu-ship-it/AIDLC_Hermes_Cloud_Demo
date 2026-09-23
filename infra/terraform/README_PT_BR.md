# Infraestrutura Terraform

> [Voltar ao README em português](../../README_PT_BR.md) | [English / 中文](README_CN_EN.md)

Este módulo cria os recursos mínimos da Huawei Cloud necessários para a demonstração em `sa-brazil-1`:

- VPC e sub-rede;
- grupo de segurança;
- dois EIPs;
- um cluster CCE;
- um worker CCE/ECS e seu armazenamento EVS;
- uma instância DCS Redis;
- dois repositórios privados SWR.

O MaaS permanece em Hong Kong e é consumido por um endpoint compatível com OpenAI. A MaaS API Key não é gerenciada pelo Terraform; ela é injetada no Kubernetes durante a implantação da aplicação.

## Uso recomendado

Para a implantação completa, use os scripts na raiz do repositório:

```powershell
.\scripts\cloud\deploy.ps1
.\scripts\cloud\status.ps1
.\scripts\cloud\destroy.ps1
```

Para a experiência guiada que também prepara ferramentas e Docker Desktop, use:

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1"
```

Consulte o [guia de implantação em português](../../docs/IMPLANTACAO_UM_COMANDO_PT_BR.md).

## Estado e informações sensíveis

O estado Terraform contém senhas geradas para o nó e para o Redis. O arquivo é excluído pelo `.gitignore`, mas continua sendo informação sensível.

- Proteja a estação que executa a implantação.
- Não envie o estado por e-mail ou ferramentas públicas de colaboração.
- Não faça commit do estado, planos salvos ou arquivos de credenciais.
- Para produção, use um backend remoto criptografado, com controle de acesso, bloqueio e auditoria.
- Preserve o mesmo estado até a destruição dos recursos ser concluída.

## Regiões e fluxo de dados

- Recursos de execução e dados da demonstração: `sa-brazil-1`.
- Inferência GLM-5.2 via ModelArts Studio MaaS: `ap-southeast-1`.

Antes de usar dados sensíveis, o cliente deve aprovar o fluxo entre regiões, as políticas de retenção e o conteúdo enviado ao modelo.

## Limites

O módulo representa uma topologia de demonstração de baixo custo. Ele não implementa alta disponibilidade multi-AZ, backup, recuperação de desastre ou integração corporativa de identidade.

