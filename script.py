import subprocess
import os
import time
import configparser

config = configparser.ConfigParser()
config.read('dockerhub_config.ini') 

dockerhub_username = config['dockerhub']['username']
dockerhub_password = config['dockerhub']['password']

cln = subprocess.run(["git", "clone", "https://github.com/SATYAsasini/kubercool-kids.git"])

if cln.returncode != 0:
    print("Error Cloning")
    print("Error message:", cln.stderr)
    

os.chdir("kubercool-kids")


if os.path.exists("index.html"):
  lang = "html" 
elif os.path.exists("index.php"):
  lang = "php"
else:
  print("No index file found")
  exit(1)

with open("Dockerfile", "w") as f:
  if lang == "html":
    f.write("FROM nginx\nCOPY . /usr/share/nginx/html") 
  elif lang == "php":
    f.write("FROM php:7.4-fpm\nCOPY . /var/www/html")



build = subprocess.run(["sudo", "docker", "build", "-t", f"myapp:{lang}", "."]) #build
if build.returncode != 0:
    print("Error in Build")
    print("Error message:", build.stderr)



depl = subprocess.run(["kubectl", "create", "deployment", "myapp", f"--image=myapp:{lang}"]) #create dep
if depl.returncode != 0:
    print("Error ")
    print("Error message:", depl.stderr)


expose = subprocess.run(["kubectl", "expose", "deployment", "myapp", "--type=NodePort", "--port=32000"]) #expose
if expose.returncode != 0:
    print("Error executing command")
    print("Error message:", expose.stderr)


try:
    subprocess.run(["sudo", "docker", "tag", f"myapp:{lang}", f"irawal007/myapp:{lang}"], check=True)
    print("Docker image tagged successfully")
except subprocess.CalledProcessError as e:
    print("Error tagging Docker image:", e.stderr)
    exit(1)

subprocess.run(["sudo", "docker", "login", "-u", dockerhub_username, "-p", dockerhub_password])

try:
    subprocess.run(["sudo", "docker", "push", f"irawal007/myapp:{lang}"], check=True)
    print("Docker image pushed to Docker Hub successfully")
except subprocess.CalledProcessError as e:
    print("Error pushing Docker image to Docker Hub:", e.stderr)
    exit(1)

with open("ingress.yaml", "w") as f:
  f.write(f"""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app-service
                port:
                  number: 80
  """)


with open("deployment.yaml", "w") as fl:
  fl.write(f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: irawal007/myapp:latest
        resources:
         limits:
          memory: "25Mi"
          cpu: "25m"
        ports:
        - containerPort: 80
  """)

subprocess.run(["kubectl", "apply", "-f", "ingress.yaml"])
subprocess.run(["kubectl", "apply", "-f", "deployment.yaml"])


while True:

  subprocess.run(["git", "pull", "origin", "main"])

  if os.path.exists("index.html") and lang != "html":
    lang = "html"
    subprocess.run(["docker", "build", "-t", f"myapp:{lang}", "."]) 

  if os.path.exists("index.php") and lang != "php":
    lang = "php"
    subprocess.run(["docker", "build", "-t", f"myapp:{lang}", "."])

  subprocess.run(["kubectl", "rollout", "restart", "deployment", "myapp"])  

  time.sleep(60)