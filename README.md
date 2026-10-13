# Simulador de FSMs de Protocolos de Transporte (TCP & UDP)

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-MVC-green.svg)
![Tests](https://img.shields.io/badge/tests-pytest%20100%25-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-informational.svg)

Este projeto consiste em um **simulador interativo de Máquinas de Estados Finitos (FSM)** para os protocolos da camada de transporte **TCP** (RFC 793, RFC 6298) e **UDP** (RFC 768). Desenvolvido em Python sob o padrão arquitetural **MVC (Model-View-Controller)**, o sistema permite tanto a execução visual e passo a passo de cenários de rede quanto a validação automatizada desacoplada (*headless*) via terminal.

---

## 🚀 Funcionalidades Principais

- **FSM Completa do TCP (11 Estados):** Suporte integral ao *3-way handshake* (`CLOSED` $\to$ `SYN_SENT` / `SYN_RCVD` $\to$ `ESTABLISHED`), encerramento de conexão de 4 vias (`FIN_WAIT_1`, `FIN_WAIT_2`, `CLOSE_WAIT`, `LAST_ACK`), e tratamento de **Fechamento Simultâneo** (`CLOSING`, `TIME_WAIT` com temporizador de $2\times\text{MSL}$).
- **Tratamento de Conexão e Datagramas UDP:** Cálculo e verificação de *checksum* usando complemento de 1 em palavras de 16 bits, com descarte imediato de pacotes corrompidos e comunicação sem estado (*stateless*).
- **Transferência Confiável de Dados (rtd 3.0+):**
  - Números de sequência e ACKs cumulativos.
  - Estimativa de RTT e tempo de esgotamento (*timeout*) dinâmico segundo a **RFC 6298** ($SRTT$, $RTTVAR$ e $RTO$).
  - Algoritmo de Retransmissão Rápida (**Fast Retransmit**) ao receber 3 ACKs duplicados.
- **Canal de Comunicação Não Confiável Simulado:**
  - Injeção programada de perdas de pacotes, duplicação, corrupção de bits e atrasos randômicos.
  - Execução estritamente determinística orientada por fila de eventos com **relógio virtual** e *seeds* controladas.
- **Interface Gráfica Interativa (GUI):**
  - Renderização em tempo real do **Diagrama de Sequência de Mensagens (MSC)**.
  - Grafo interativo da FSM com destaque para o estado atual dos Hosts.
  - Painel para execução automática e geração do **Relatório Comparativo UDP $\times$ TCP (Cenário 10)**.

---

## 📐 Arquitetura do Sistema

O projeto é desacoplado seguindo o padrão **Model-View-Controller (MVC)**:

```
                  +-----------------------------------+
                  |         SUÍTE DE TESTES           |
                  |     (pytest / Headless CLI)       |
                  +-----------------+-----------------+
                                    |
                                    v (Comandos Diretos)
+-----------------------+   +-------+---------------+   +-----------------------+
|     VISÃO (GUI)       |<--|   NÚCLEO/MODELO (FSM) |-->| ARCHIVOS CONFIG (JSON)|
| - Diagrama Sequência  |   | - Motor FSM Genérico  |   | - fsm_tcp.json        |
| - Grafo de Estados    |   | - Timers RFC 6298     |   | - fsm_udp.json        |
| - Logs e Controles    |   | - Canal Não Confiável |   +-----------------------+
+-----------------------+   +-----------------------+
```

1. **Núcleo de Simulação (`core/`):** Totalmente independente da interface gráfica. Executa as FSMs lendo regras em JSON, controla filas de eventos e simula os hosts de rede.
2. **Interface Gráfica (`gui/`):** Atua como observadora das mudanças de estado do modelo, renderizando os eventos e gráficos.
3. **Suíte de Testes (`tests/`):** Executa o modelo diretamente sem carregar a interface visual, garantindo velocidade e reprodutibilidade.

---

## 📂 Estrutura de Diretórios

```bash
.
├── config/
│   ├── fsm_tcp.json         # Definição dirigida a dados dos 11 estados do TCP
│   └── fsm_udp.json         # Definição do comportamento sem estado do UDP
├── core/
│   ├── clock.py             # Relógio virtual e gerenciador da fila de eventos
│   ├── fsm.py               # Motor genérico de execução de FSMs
│   ├── tcp.py               # Protocolo TCP (Controle de fluxo, RTO, Fast Retransmit)
│   ├── udp.py               # Protocolo UDP e cálculo do Checksum
│   ├── channel.py           # Simulador do canal com perdas, atrasos e corrupções
│   └── host.py              # Abstração das entidades de extremidade (Host A e Host B)
├── gui/
│   ├── app.py               # Janela principal da aplicação (CustomTkinter/Tkinter)
│   ├── sequence_diag.py     # Componente de desenho do Diagrama de Sequência
│   └── fsm_viewer.py        # Visualizador do grafo de estados ativo
├── tests/
│   └── test_scenarios.py    # Testes automatizados cobrindo os Cenários 1 a 10
├── main.py                  # Ponto de entrada da aplicação gráfica
├── requirements.txt         # Dependências do projeto
└── README.md                # Este documento de documentação
```

---

## 🛠️ Pré-requisitos e Instalação

### Pré-requisitos
- **Python 3.10** ou superior instalado na máquina.
- Gerenciador de pacotes `pip`.

### Passo a Passo de Instalação

1. **Crie e ative um ambiente virtual (recomendado):**
   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Como Executar

### 1. Modos de Execução da Interface Gráfica (GUI)

Para abrir o simulador interativo completo:
```bash
python -m interface.main
```

Na interface, você poderá:
- Selecionar entre os protocolos **TCP** e **UDP**.
- Executar os cenários de 1 a 10 através de botões dedicados na barra lateral.
- Avançar a simulação **Passo a Passo (Tick)** ou rodar continuamente em tempo real.
- Simular falhas manuais no canal (descartar pacotes, corromper bits, forçar atraso).
- Clicar em **"Gerar Relatório Comparativo (Cenário 10)"** para visualizar as métricas consolidadas.

### 2. Executando a Suíte de Testes Automatizados (Terminal)

Para validar todos os 10 cenários obrigatórios em modo *headless* (sem carregar a GUI):
```bash
pytest tests/test_scenarios.py -v
```

---

## 📋 Cenários de Teste Validados

| Cenário | Descrição do Teste | Estado/Resultado Esperado | Status |
| :---: | :--- | :--- | :---: |
| **1** | Estabelecimento normal de conexão TCP | `CLOSED` $\to$ `SYN_SENT` / `SYN_RCVD` $\to$ `ESTABLISHED` | **APROVADO** |
| **2** | Encerramento normal de conexão TCP | `ESTABLISHED` $\to$ `FIN_WAIT_1` / `CLOSE_WAIT` $\to$ `CLOSED` | **APROVADO** |
| **3** | Perda do segmento `SYN-ACK` | Retransmissão por *timeout* no Host A e recuperação | **APROVADO** |
| **4** | Corrupção de dados no meio da transmissão | Descarte por *checksum* inválido e retransmissão confiável | **APROVADO** |
| **5** | Fechamento simultâneo de conexão TCP | Transição cruzada para `CLOSING` $\to$ `TIME_WAIT` ($2\times\text{MSL}$) | **APROVADO** |
| **6** | Retransmissão Rápida (*Fast Retransmit*) | Disparo imediato do pacote perdido após **3 ACKs duplicados** | **APROVADO** |
| **7** | Envio simples via datagrama UDP | Envio e recepção *stateless* sem estabelecimento de conexão | **APROVADO** |
| **8** | Corrupção de datagrama UDP | Identificação de *checksum* incorreto e descarte silencioso | **APROVADO** |
| **9** | Estouro de temporizador (*Timeout*) dinâmico | Cálculo de $RTO$ segundo a RFC 6298 e retransmissão exponencial | **APROVADO** |
| **10**| Comparativo quantitativo UDP $\times$ TCP | Coleta e exibição de métricas (Latência, Perdas, Retransmissões) | **APROVADO** |

---
