# Catálogo de Skills AI-DLC e mapeamento por etapa

> [Voltar ao README em português](../README_PT_BR.md) | [English / 中文](SKILLS_CATALOG_CN_EN.md)

Este documento explica as Skills incluídas na demonstração, onde são usadas, o que consomem e quais evidências produzem.

## Como as Skills são usadas

O Hermes Orchestrator seleciona as Skills de acordo com o grafo de tarefas e entrega a cada Worker somente o contexto necessário. As Skills OpenSpec governam requisitos e artefatos de mudança; as Skills AIDLC governam execução, controles de qualidade, entrega em nuvem e evidências.

```text
Requisito
  -> Explorar e propor
  -> Especificação, projeto e tarefas
  -> Desenvolvimento
  -> QA
  -> Revisão e segurança
  -> Build Kaniko -> SWR -> Preview CCE
  -> PR + Evidências + Aprovação humana
```

## Catálogo completo

| Skill | Origem | Etapa e executor | Entrada principal | Saída ou controle |
|---|---|---|---|---|
| `openspec-explore` | OpenSpec | Descoberta; Hermes | Ideia de negócio, problema e restrições | Escopo e decisões esclarecidos; sem alteração de código |
| `openspec-propose` | OpenSpec | Requisitos e planejamento; Hermes | Requisito confirmado | Proposta, especificação, projeto e tarefas |
| `openspec-update-change` | OpenSpec | Planejamento da mudança; Hermes | Mudança OpenSpec existente e novas decisões | Artefatos de planejamento atualizados e coerentes; sem código |
| `openspec-apply-change` | OpenSpec | Desenvolvimento; Dev Worker | Especificação, projeto, tarefas e repositório aprovados | Alterações das tarefas implementadas |
| `openspec-sync-specs` | OpenSpec | Governança da especificação; Hermes | Especificações delta aceitas | Especificações principais sincronizadas |
| `openspec-archive-change` | OpenSpec | Encerramento; Hermes | Mudança concluída e aprovada | Mudança OpenSpec arquivada |
| `aidlc-orchestration` | Plataforma da demonstração | Orquestração ponta a ponta; Hermes | Solicitação de execução e registro de Skills | Grafo Dev → QA → Review → Deploy, controles e decisão final |
| `aidlc-python-development` | Plataforma da demonstração | Desenvolvimento; Dev Worker | Repositório, tarefa, testes e contexto GLM-5.2 | Alterações de código, testes locais aprovados, commit e branch |
| `aidlc-test-execution` | Plataforma da demonstração | Verificação; QA Worker | Commit exato da funcionalidade e testes do repositório | Resultados determinísticos e controle PASS/FAIL |
| `aidlc-code-review` | Plataforma da demonstração | Revisão de código; Review Worker | Especificação, projeto, diff e compilação | Achados da revisão e controle de aprovação |
| `aidlc-security-review` | Plataforma da demonstração | Revisão de segurança; Review Worker | Arquivos alterados e conteúdo-fonte | Varredura de segredos, achados de segurança e PASS/FAIL |
| `aidlc-swr-delivery` | Plataforma da demonstração | Entrega; Deploy Worker | Repositório, branch, commit exato, Dockerfile e Secret SWR | Job Kaniko, tag e digest SWR, Preview CCE e smoke tests |
| `aidlc-evidence-collector` | Plataforma da demonstração | Evidência e auditoria; Hermes | Eventos e saídas dos Workers de toda a execução | Pacote de Evidências com data/hora e decisão final rastreável |

## Mapeamento em tempo de execução

| Etapa | Pod ou componente | Skills carregadas | Evidências visíveis |
|---|---|---|---|
| Receber solicitação e construir o grafo | `aidlc-api`, `hermes-orchestrator` | `aidlc-orchestration` e Skills OpenSpec aplicáveis | Run ID, contexto do requisito e eventos de despacho |
| Alterar e versionar o código | `hermes-sf-dev` | `openspec-apply-change`, `aidlc-python-development` | Teste inicialmente falho, teste corrigido, arquivos, branch e commit |
| Controle determinístico de QA | `hermes-sf-qa` | `aidlc-test-execution` | Comando de teste, código de saída e PASS/FAIL |
| Controles de revisão e segurança | `hermes-sf-review` | `aidlc-code-review`, `aidlc-security-review` | Compilação, ocorrências de segredos e revisão do modelo |
| Build, publicação e Preview | `hermes-sf-deploy`, Kaniko e Pods de Preview da execução | `aidlc-swr-delivery` | Job, tag, digest, Deployment, Service, Pod, imageID e smoke tests |
| PR e evidência final | `hermes-orchestrator` | `aidlc-evidence-collector` | URL do Pull Request, decisão final e Pacote de Evidências |

## Detalhes da Skill de entrega

A etapa de entrega é real; não é apenas uma simulação de manifesto:

1. O Kaniko obtém o commit exato da branch de funcionalidade.
2. O Kaniko constrói e publica `swr.sa-brazil-1.myhuaweicloud.com/aidlc-demo/order-demo:<prefixo-do-commit>`.
3. A plataforma extrai o digest SHA-256 real do registro.
4. O CCE implanta `image@sha256:<digest>`, tornando o Preview imutável e rastreável.
5. O Deploy Worker verifica saúde, cancelamento de pedido e repetição idempotente.
6. O Hermes registra todos os resultados antes de permitir a criação do PR e a exposição do Preview.

## Adaptação para um cliente

O cliente pode criar uma Skill em `.hermes/skills/<nome-da-skill>/SKILL.md` e registrá-la no mapeamento entre etapa e Skill.

Uma integração de produção deve definir:

- evento ou condição de acionamento;
- entradas obrigatórias;
- ferramentas permitidas;
- controle determinístico;
- esquema da saída;
- campos de evidência e retenção;
- responsável pela aprovação e pela manutenção.

Skills são instruções de execução, não credenciais. Tokens GitHub, Huawei Cloud AK/SK, chaves MaaS e credenciais SWR devem permanecer em Kubernetes Secrets e nunca podem ser escritos em arquivos de Skill ou prompts.

