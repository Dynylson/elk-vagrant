#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive

trap 'echo "Provisionamento interrompido. Consulte a saída acima e execute vagrant provision para tentar novamente." >&2' ERR

if [[ $(id -u) -ne 0 ]]; then
  echo "Este script deve ser executado como root dentro da VM, pelo Vagrant." >&2
  exit 1
fi
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
  echo "Sistema esperado: Ubuntu 24.04. Não execute este provisionamento na máquina anfitriã." >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl python3 rsync
install -m 0755 -d /etc/apt/keyrings
curl --fail --silent --show-error --retry 3 https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

echo 'vm.max_map_count=1048576' > /etc/sysctl.d/99-elk-lab.conf
sysctl -p /etc/sysctl.d/99-elk-lab.conf

install -d -m 0755 /opt/elk-vagrant
rsync -a --exclude=.git --exclude=.vagrant --exclude=.runtime --exclude=.env /vagrant/ /opt/elk-vagrant/
cd /opt/elk-vagrant
cat > .env <<'EOF'
# Os encaminhamentos do Vagrant ficam limitados ao localhost do anfitrião.
BIND_ADDRESS=0.0.0.0
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
EOF
bash scripts/start.sh
