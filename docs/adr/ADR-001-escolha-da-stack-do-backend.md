# ADR-001 — Escolha da stack inicial do backend

- **Data:** 2026-10-15

## Contexto

O projeto é um protótipo acadêmico de gestão de filas e atendimento presencial. A entrega deve demonstrar uma fatia vertical do sistema, incluindo uma operação que altere estado, uma consulta, persistência, um fluxo de erro e uma dependência externa substituível.

O sistema também possui requisitos que influenciam a escolha tecnológica, como resposta rápida nas operações de emissão e chamada de senhas, acesso simultâneo por usuários, atendentes e totens, documentação da API e possibilidade de evolução sem dependências desnecessárias.

## Problema e forças envolvidas

É necessário escolher uma stack inicial que:

- permita entregar o protótipo no tempo disponível;
- ofereça uma API HTTP clara para diferentes tipos de cliente;
- facilite validação de entrada, documentação e testes automatizados;
- tenha complexidade operacional proporcional ao escopo acadêmico;
- permita organizar as regras de negócio sem acoplá-las ao framework web;
- não antecipe decisões ainda abertas, como banco de dados e serviço de notificações.

A stack, isoladamente, não garante disponibilidade, desempenho, segurança ou consistência. Esses atributos dependerão também da arquitetura interna, da persistência, da implantação e dos testes que forem adotados nas próximas decisões.

## Alternativas consideradas

### 1. Python com FastAPI e Uvicorn

O FastAPI fornece roteamento HTTP, validação baseada em tipos e documentação OpenAPI interativa. O Uvicorn executa a aplicação seguindo o padrão ASGI. Python permite implementar o protótipo com pouco código de infraestrutura e possui bibliotecas para persistência, testes e integrações externas.

Como custos, a equipe deverá definir limites claros entre a API e as regras de negócio. Sem essa separação, decoradores, modelos do framework e detalhes HTTP podem se espalhar pelo domínio. Operações bloqueantes também exigirão cuidado para não comprometer a concorrência do servidor.

### 2. Python com Flask

Flask oferece uma base simples e flexível, além de um ecossistema consolidado. Entretanto, validação de dados, documentação OpenAPI e parte da estrutura necessária dependeriam de bibliotecas adicionais ou de implementação manual. Para este protótipo, isso aumenta a quantidade de decisões e configuração sem benefício claro.

### 3. Python com Django e Django REST Framework

Django oferece ORM, migrações, autenticação e painel administrativo integrados. Essa alternativa seria interessante para um sistema com forte necessidade de operações administrativas e um modelo de persistência já definido. No estágio atual, porém, ela introduziria mais estrutura e decisões acopladas antes de o domínio e a persistência estarem modelados.

### 4. TypeScript com Node.js e NestJS

NestJS oferece tipagem, injeção de dependências e uma organização modular explícita. Também é adequado para APIs e comunicação assíncrona. A alternativa, contudo, exigiria substituir a base Python já implementada e adotar um conjunto maior de convenções e ferramentas. O custo de mudança não se justifica para a fatia vertical prevista.

## Decisão

Adotar a seguinte stack inicial para o backend:

- **Python 3.11 ou superior** como linguagem e ambiente de execução;
- **FastAPI 0.115 ou superior, abaixo da versão 1**, para a interface HTTP e a geração da documentação OpenAPI;
- **Uvicorn 0.30 ou superior, abaixo da versão 1**, como servidor ASGI;
- **setuptools** como ferramenta de build e empacotamento;
- **layout `src`**, com o pacote da aplicação em `src/gestao_filas`.

O FastAPI deve permanecer na camada de entrada HTTP. As regras de negócio e os casos de uso não devem depender diretamente de requisições, respostas ou decoradores do framework. A integração com persistência e notificações deverá ocorrer por interfaces substituíveis, definidas em decisões posteriores.

Esta decisão não seleciona banco de dados, ORM, mecanismo de autenticação, canal de notificação, frontend ou estratégia de implantação.

## Consequências positivas

- A base existente pode ser evoluída sem migração de linguagem ou framework.
- A documentação interativa da API facilita o desenvolvimento e a demonstração do protótipo.
- Tipos e validação de entrada reduzem código repetitivo na fronteira HTTP.
- O baixo volume de configuração inicial favorece a entrega de uma fatia vertical.
- O padrão ASGI permite trabalhar com operações assíncronas quando elas forem necessárias.
- O layout `src` reduz o risco de importar acidentalmente código fora do pacote instalado.

## Consequências negativas, custos e riscos

- A equipe precisará definir e manter a separação entre camada HTTP, casos de uso, domínio e infraestrutura; o framework não impõe essa separação.
- A faixa ampla de versões das dependências pode produzir diferenças entre ambientes enquanto não existir um arquivo de resolução ou travamento de versões.
- Bibliotecas síncronas ou tarefas demoradas executadas no processo da API podem reduzir sua capacidade de atender requisições concorrentes.
- Recursos como persistência, migrações, autenticação e processamento de notificações precisarão de bibliotecas e decisões adicionais.
- A documentação OpenAPI descreve o contrato HTTP, mas não comprova o atendimento dos requisitos de desempenho, disponibilidade, consistência ou segurança.

## Critérios para revisar a decisão

Esta decisão deverá ser reavaliada se:

- a equipe não conseguir manter as regras de negócio independentes do FastAPI;
- medições representativas demonstrarem que a stack não atende aos tempos de resposta ou à concorrência necessária;
- o sistema passar a exigir recursos integrados que tornem outra plataforma significativamente mais simples;
- uma nova restrição institucional impedir o uso ou a operação de Python/ASGI.

Uma eventual troca do framework deve afetar principalmente a camada de entrada HTTP. Casos de uso, regras de prioridade e interfaces de persistência e notificação deverão permanecer estáveis, desde que a separação definida neste ADR seja respeitada.

## Situação na entrega do protótipo

A decisão original permanece como registro da stack inicial. O layout `src`
evoluiu para `gestao_filas`, `gestao_senhas` e `gestao_compartilhada`.
Persistência e notificações foram detalhadas no [ADR-003](ADR-003-postgresql-persistencia.md)
e no [ADR-004](ADR-004-notificacoes.md). React/Vite/TypeScript, Nginx e Docker
Compose foram acrescentados à entrega, sem substituir o backend escolhido.
A configuração atual e seus limites estão no [README](../../README.md).
