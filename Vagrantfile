# frozen_string_literal: true

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.box_version = "202510.26.0"
  config.vm.box_architecture = "amd64"
  config.vm.hostname = "elk-lab"

  # O rsync evita depender do compartilhamento de pastas/Guest Additions.
  config.vm.synced_folder ".", "/vagrant", type: "rsync",
    rsync__exclude: [".git/", ".vagrant/", ".runtime/", ".env"]

  config.vm.network "forwarded_port", guest: 5601, host: 5601,
    host_ip: "127.0.0.1", auto_correct: false
  config.vm.network "forwarded_port", guest: 9200, host: 9200,
    host_ip: "127.0.0.1", auto_correct: false

  config.vm.provider "virtualbox" do |vb|
    vb.name = "elk-vagrant"
    vb.memory = 6144
    vb.cpus = 2
  end

  config.vm.provision "shell", path: "provision/setup.sh"
  config.vm.post_up_message = <<~MESSAGE
    Kibana: http://localhost:5601
    Dashboard: http://localhost:5601/app/dashboards#/view/elk-lab-dashboard
    Elasticsearch: http://localhost:9200
    Laboratório local sem autenticação. Não exponha as portas à rede.
  MESSAGE
end
