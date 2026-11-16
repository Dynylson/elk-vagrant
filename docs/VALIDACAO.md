# Validação do laboratório

Validações locais realizadas em **16/11/2026**, em anfitrião Fedora x86_64, usando Docker Engine 29.9.3 e Docker Compose 5.7.1. As imagens dos três serviços são da versão 8.19.12.

## Verificações executadas

- `bash -n provision/setup.sh scripts/start.sh`: sintaxe dos scripts aceita.
- `python3 -m compileall -q scripts`: scripts Python compilados.
- `docker compose config --quiet`: configuração Compose aceita.
- Vagrant 2.4.9, distribuição oficial com SHA-256 conferido: `vagrant validate --ignore-provider` executado em contêiner Ubuntu 24.04, com resultado `Vagrantfile validated successfully`.
- `bash scripts/start.sh`: Elasticsearch e Kibana disponíveis, template configurado e Logstash processando o arquivo.
- `python3 scripts/bootstrap.py verify`: exatamente 120 documentos, com 80 respostas HTTP 200, 10 HTTP 201, 10 HTTP 404 e 20 HTTP 500.
- Verificação dos campos obrigatórios nos 120 documentos e dos tipos numéricos em um documento retornado.
- Importação bem-sucedida de seis objetos no Kibana: um data view, quatro visualizações e um dashboard.
- Exportação dos objetos pela API do próprio Kibana e reimportação do arquivo resultante, preservando os metadados de migração.
- Reexecução completa de `scripts/start.sh`, mantendo os mesmos 120 documentos.
- Remoção e recriação dos contêineres com `docker compose down` e `scripts/start.sh`, preservando os volumes e os 120 eventos.

As APIs foram utilizadas para validar dados e objetos do Kibana. Uma inspeção posterior pelo navegador confirmou os quatro painéis renderizados, com captura real em [screenshots/kibana-dashboard.png](screenshots/kibana-dashboard.png).

Essa inspeção identificou uma configuração ausente em `categoryAxes[].scale` nos dois gráficos de barras. O editor isolado reproduziu o erro `Cannot read properties of undefined (reading 'defaultYExtents')`. Após incluir a escala horizontal, a verificação dos quatro elementos `visualizationLoader` passou de dois para quatro com `data-render-complete="true"`. A captura usa o período das últimas duas horas para mostrar a distribuição dos eventos. A validação HTTP dos 120 eventos também foi repetida com sucesso.

## Limite da validação do Vagrant

**A criação e o provisionamento da VM com `vagrant up --provider=virtualbox` ainda não foram executados neste ambiente**, pois VirtualBox não está instalado no anfitrião. A execução de `vagrant validate --ignore-provider` valida a configuração geral, mas não testa o provedor, a inicialização da VM, o encaminhamento das portas nem a instalação de pacotes pelo script de provisionamento dentro dela.

A existência da box `bento/ubuntu-24.04`, versão `202510.26.0`, e do provedor VirtualBox foi consultada na API do Vagrant Cloud.

Portanto, os testes locais comprovam a integração dos serviços com Docker e a sintaxe/configuração geral dos arquivos. A validação completa da entrega Vagrant requer executar os passos abaixo em uma máquina com os pré-requisitos do README.

## Verificação completa em uma máquina com VirtualBox

```bash
git clone https://github.com/Dynylson/elk-vagrant.git
cd elk-vagrant
vagrant validate
vagrant up --provider=virtualbox
vagrant ssh -c 'cd /opt/elk-vagrant && sudo python3 scripts/bootstrap.py verify'
vagrant provision
vagrant halt
vagrant up
vagrant ssh -c 'cd /opt/elk-vagrant && sudo python3 scripts/bootstrap.py verify'
```

Abrir o dashboard no endereço indicado no README, conferir os quatro painéis e localizar os 20 erros com `status_code: 500` no Discover, usando o intervalo de tempo dos dados gerados. Por fim, `vagrant destroy -f` remove a VM e seus dados.

## Integração contínua

O workflow `validate.yml` repete a validação do Vagrantfile sem provedor, as verificações de sintaxe, a ingestão com Docker, a reexecução e o teste de persistência em runner Ubuntu. **O workflow também não inicia uma VM com VirtualBox.** O resultado de cada execução pode ser consultado na aba Actions do repositório.
