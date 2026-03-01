# Organizador de prateleiras da farmácia

Aplicação web em **Python + Flask** (interface em português) para controlar produtos vencidos e pré-vencidos por seção.

## Funcionalidades

- Cadastro e login de usuários.
- Cada usuário possui sua seção principal (ex.: Prateleira 1, Prateleira 2).
- Cadastro de produtos com:
  - nome;
  - data de validade;
  - foto tirada na hora (upload pelo celular);
  - opção de controle de pré-vencido;
  - data de início de pré-vencido;
  - data para retirar da prateleira;
  - seção do produto.
- Painel de alertas em tempo real (atualização automática a cada 10 segundos).
- Lista completa com status automático: `OK`, `Pré-vencido` e `Vencido`.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse: `http://localhost:5000`

## Observações

- Troque a chave `SECRET_KEY` antes de publicar em produção.
- Banco padrão: SQLite (`farmacia.db`).
