    # -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Configuração da VM de Banco de Dados (MySQL)
  config.vm.define "db" do |db|
    db.vm.box = "bento/ubuntu-22.04"
    db.vm.hostname = "execspace-db"
    
    # Configuração de rede privada
    db.vm.network "private_network", ip: "192.168.56.10"
    
    # Recursos da VM
    db.vm.provider "vmware_desktop" do |v|
      v.vmx["memsize"] = "2048"
      v.vmx["numvcpus"] = "1"
    end
    
    # Sincronizar pasta do banco de dados
    db.vm.synced_folder "./database", "/home/vagrant/database"
    
    # Provisionamento
    db.vm.provision "shell", path: "provisioning/db_setup.sh"
  end
  
  # Configuração da VM de Aplicação (ExecSpace)
  config.vm.define "app" do |app|
    app.vm.box = "bento/ubuntu-22.04"
    app.vm.hostname = "execspace-app"
    
    # Configuração de rede privada
    app.vm.network "private_network", ip: "192.168.56.11"
    
    # Expor porta da aplicação para o host
    app.vm.network "forwarded_port", guest: 8000, host: 8000, host_ip: "0.0.0.0"
    
    # Recursos da VM
    app.vm.provider "vmware_desktop" do |v|
      v.vmx["memsize"] = "4096"
      v.vmx["numvcpus"] = "2"
    end
    
    # Sincronizar código da aplicação
    app.vm.synced_folder "./app", "/home/vagrant/app"
    
    # Provisionamento
    app.vm.provision "shell", path: "provisioning/app_setup.sh"
  end
end

