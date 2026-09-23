# Guia do cliente e roteiro da demonstração

> [Voltar ao README em português](../README_PT_BR.md)

Este guia apresenta a demonstração AIDLC Hermes Cloud para clientes no Brasil. Ele explica o valor da solução, os dados necessários, o roteiro recomendado e os limites que devem ficar claros durante a conversa.

## 1. Mensagem principal

A demonstração mostra uma fábrica de software orientada por especificações e evidências:

```text
Requisito versionado
  -> Planejamento e controles
  -> Desenvolvimento assistido por modelo
  -> QA determinístico
  -> Revisão de código e segurança
  -> Build e Preview rastreáveis
  -> Pull Request
  -> Aprovação humana para merge
```

O modelo auxilia a engenharia, mas não substitui os controles. Testes, compilação, varredura de segredos, políticas e aprovação humana permanecem visíveis.

## 2. O que o cliente deve fornecer

- Um fork ou repositório GitHub de aplicação.
- Uma branch base, normalmente `main`.
- Um requisito versionado, por exemplo `demo/GITHUB_ISSUE.md`.
- Artefatos `sdd/spec.md`, `sdd/design.md` e `sdd/tasks.yaml`.
- Testes executáveis pertencentes ao repositório.
- Token fine-grained do próprio cliente, limitado ao repositório escolhido.
- Política de aprovação para Pull Request, merge e liberação.

Para implantação, também são necessários Huawei Cloud AK/SK com escopo adequado e uma API Key do MaaS GLM-5.2 em Hong Kong.

## 3. Checklist antes da reunião

- [ ] O Console está restrito ao CIDR público da reunião ou da rede do cliente.
- [ ] A senha padrão foi substituída ou o ambiente será removido imediatamente após a demonstração.
- [ ] Nenhuma credencial aparece no Git, nos requisitos, em Skills ou em capturas de tela.
- [ ] O fork do cliente contém os arquivos SDD e testes necessários.
- [ ] O token GitHub possui somente **Contents: Read and write** e **Pull requests: Read and write** no fork.
- [ ] Cotas e permissões de `sa-brazil-1` foram verificadas.
- [ ] A conectividade com MaaS em `ap-southeast-1` foi validada e aprovada pelo cliente.
- [ ] O estado da plataforma foi verificado com `scripts\cloud\status.ps1`.
- [ ] Existe um plano de destruição e um responsável pelos custos do ambiente.

## 4. Roteiro recomendado

### Etapa A — Contexto e arquitetura

1. Abra o Console.
2. Explique que execução e dados operacionais estão no Brasil, enquanto o modelo GLM-5.2 é consumido em Hong Kong.
3. Mostre API, Orchestrator, Workers especializados, Redis, SWR e CCE.
4. Reforce que a demonstração usa um ambiente reduzido e não representa uma topologia de produção.

### Etapa B — Requisito e rastreabilidade

1. Abra o requisito no repositório do cliente.
2. Mostre `sdd/spec.md`, `sdd/design.md` e `sdd/tasks.yaml`.
3. Explique que a entrada fica versionada, revisável e auditável.
4. Mostre as Skills selecionadas para cada etapa.

### Etapa C — Criar a execução

Use o Console ou a API:

```http
POST /api/runs
Content-Type: application/json
```

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

Nunca coloque tokens, AK/SK ou API Keys no corpo da solicitação.

### Etapa D — Acompanhar os controles

Mostre, na ordem:

1. tarefa e decisão do Dev Worker;
2. arquivos alterados, branch e commit;
3. comando de testes e resultado do QA;
4. compilação, varredura de segredos e revisão;
5. build Kaniko e publicação no SWR;
6. digest SHA-256 da imagem;
7. Preview no CCE e smoke tests;
8. Pull Request e decisão final.

Explique a semântica dos controles:

- **PASS:** a condição foi atendida e a execução pode avançar.
- **FAIL:** a condição obrigatória não foi atendida; a entrega é bloqueada.
- **Aprovação humana:** merge e liberação continuam sob responsabilidade de uma pessoa autorizada.

### Etapa E — Evidências

Abra:

```text
GET /api/runs/{run_id}/events
GET /api/runs/{run_id}/evidence
```

O Pacote de Evidências deve permitir relacionar requisito, tarefa, commit, testes, revisão, imagem, Preview, PR e decisão final.

### Etapa F — Encerramento

1. Confirme que o merge não ocorreu automaticamente.
2. Discuta quais controles e Skills o cliente deseja adaptar.
3. Registre requisitos de identidade, rede, retenção, observabilidade e conformidade.
4. Destrua o ambiente se ele não precisar permanecer ativo.

## 5. Perguntas frequentes

### O Agent pode alterar qualquer repositório?

Não. O token GitHub deve ser fine-grained, limitado ao repositório selecionado e às permissões necessárias. O cliente continua controlando branch, Pull Request e merge.

### O modelo decide sozinho se o código vai para produção?

Não. O fluxo combina assistência do modelo com verificações determinísticas e aprovação humana. A demonstração cria um Preview e um Pull Request; o merge é uma decisão humana.

### Onde ficam os dados?

Execução, Redis, imagens e workloads da demonstração ficam em `sa-brazil-1`. As solicitações de inferência do GLM-5.2 usam o MaaS em `ap-southeast-1`. O cliente deve validar esse fluxo de dados antes de uso com informações sensíveis.

### O ambiente é pronto para produção?

Não. O ambiente de demonstração usa um worker CCE e Redis de nó único e não inclui alta disponibilidade multi-AZ, backup, recuperação de desastre ou identidade corporativa em nível de produção.

### É possível adicionar controles específicos do cliente?

Sim. Uma nova Skill pode ser criada em `.hermes/skills/<nome-da-skill>/SKILL.md` e associada à etapa apropriada. Ela deve definir entradas, ferramentas permitidas, saída, controle determinístico e evidências.

## 6. Segurança e governança

- Use menor privilégio para GitHub e Huawei Cloud.
- Mantenha credenciais em Kubernetes Secrets ou em um gerenciador de segredos aprovado.
- Nunca grave segredos em prompts, Skills, requisitos ou logs.
- Restrinja o Console com `-AllowedConsoleCidr`.
- Troque credenciais padrão antes de compartilhar o ambiente.
- Revise os dados enviados ao MaaS e aplique a política de classificação do cliente.
- Defina retenção e descarte para eventos, evidências, imagens e estados Terraform.
- Preserve a aprovação humana para merge e liberação.

## 7. Próximos passos para produção

Uma evolução de produção deve tratar separadamente:

1. identidade corporativa, SSO e RBAC;
2. cofre e rotação automática de segredos;
3. rede privada, controle de saída e proteção de APIs;
4. alta disponibilidade, backup e recuperação de desastre;
5. observabilidade, alertas e integração com SOC/SIEM;
6. políticas de modelo, privacidade e residência de dados;
7. isolamento entre equipes, projetos e ambientes;
8. governança de Skills e versionamento de controles;
9. FinOps, cotas e desligamento automático;
10. processo formal de mudança, merge e liberação.

## 8. Documentos relacionados

- [Implantação com um comando](IMPLANTACAO_UM_COMANDO_PT_BR.md)
- [Catálogo de Skills](CATALOGO_DE_SKILLS_PT_BR.md)
- [Infraestrutura Terraform](../infra/terraform/README_PT_BR.md)
- [Projeto técnico detalhado — English / 中文](AIDLC_DETAILED_DESIGN_CN_EN.md)

