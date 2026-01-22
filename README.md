# TP CloudMemo Challenge (Kubernetes)

Déploiement d’une application **Flask stateless** + **Redis stateful** sur un cluster Kubernetes (kubeadm) avec **2 environnements isolés** : `team-blue` et `team-green`.

## Architecture

- **Ansible** : serveur d’automatisation (déploiement kubeadm + déploiement manifests)
- **Control-plane** : nœud master Kubernetes
- **Worker** : nœud worker Kubernetes

## Pré-requis

- 3 VMs : `ansible`, `controle-plane`, `worker`
- Ubuntu 24.04 
- Accès SSH depuis `ansible` vers `controle-plane` et `worker`
- Cluster Kubernetes installé via kubeadm + CNI (Calico)
- `kubectl` fonctionnel sur le control-plane

## Arborescence du repo

<pre>
TP-CloudMemo/
├─ ansible/
│  ├─ inventories/
│  │  └─ hosts.yml
│  └─ playbooks/
│     ├─ 01-installation_K8S_CP_W.yml
│     ├─ 02-controlplane-init.yml
│     ├─ 03-worker-join.yml
├─ app/ (optionnel)
├─ resources/
│  ├─ docker-compose.yml
│  ├─ app.py
│  └─ requirements.txt
└─ docs/
</pre>


## 1) Déploiement du cluster Kubernetes (Ansible)

Depuis le serveur **ansible** :

```bash
cd /tp-cloudmemo/TP-CloudMemo/ansible

# Installation des prérequis Kubernetes + containerd + kubeadm sur control-plane et worker
ansible-playbook -i inventories/hosts.yml playbooks/01-installation_K8S_CP_W.yml

# Initialisation du control-plane + installation CNI
ansible-playbook -i inventories/hosts.yml playbooks/02-controlplane-init.yml

# Join du worker
ansible-playbook -i inventories/hosts.yml playbooks/03-worker-join.yml

#Vérification sur le control-plane :

kubectl get nodes -o wide
kubectl get pods -A

#2) Ingress NGINX (sur control-plane)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/cloud/deploy.yaml
kubectl get pods -n ingress-nginx

#3) Stockage (PVC Redis)

Utilisation d'une storage class manuelle pour stocker les données de REDIS de manière persistantes sur le worker

#4) Déploiement applicatif (Kubernetes)

Création des différents fichiers YAML sur le control plane afin de déployer les applications requises :

01_namespace.yml  02_pv.yml  03_redis.yml  04_cloudmemo.yml  05_ingress.yml  06_network-policies.yml

kubectl get pods -n team-blue
kubectl get pods -n team-green
kubectl get pvc -A
kubectl get ingress -A
```

## Étape 4 – Network Policies (Sécurité Réseau)

### Objectif
Isoler deux environnements Kubernetes (**team-blue** et **team-green**) afin d’empêcher toute communication réseau non autorisée entre leurs applications et bases de données.

---

### Principe
Dans chaque namespace :
- Tout le trafic est bloqué par défaut (Ingress + Egress).
- Seules les communications suivantes sont autorisées :
  - Ingress Controller → Application CloudMemo (TCP 5000)
  - Application CloudMemo → Redis du même namespace (TCP 6379)
  - Accès DNS vers CoreDNS

---

### Vérification des policies
```bash
kubectl get netpol -n team-blue
kubectl get netpol -n team-green
```

---

### Test de sécurité (scénario d’attaque)
```bash
kubectl -n team-blue set env deployment/cloudmemo REDIS_HOST=redis.team-green.svc.cluster.local
kubectl -n team-blue rollout restart deployment/cloudmemo
```

```bash
kubectl -n team-blue exec deploy/cloudmemo -- python3 - <<'PY'
import socket
s=socket.socket(); s.settimeout(2)
try:
    s.connect(("redis.team-green.svc.cluster.local",6379))
    print("Connexion autorisée (non attendu)")
except Exception as e:
    print("Connexion bloquée (attendu):", e)
PY
```

---

### Résultat attendu
- DNS fonctionnel
- Connexion Redis inter-namespace bloquée
- Données isolées entre `team-blue` et `team-green`

✅ Sécurité réseau validée.


✅ attendu : échec (timeout/refused), si les NetworkPolicies sont correctes.

Notes

Redis est déployé en StatefulSet avec PVC.

L’application CloudMemo est stateless (Deployment).

Ingress NGINX sert de point d’entrée HTTP.

Les NetworkPolicies assurent l’isolation inter-namespace.


---

## 2) Commit + push du README
Toujours dans le repo :

```bash
cd /tp-cloudmemo/TP-CloudMemo
git status
git add README.md
git commit -m "Add README with deployment steps and validation tests"
git push


