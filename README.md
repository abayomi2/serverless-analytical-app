# **Serverless Analytical Web App with AWS CDK**

## **Overview**

This project demonstrates the deployment of a containerized Python Flask web application to **AWS Fargate** using the **AWS Cloud Development Kit (CDK)** for Infrastructure as Code (IaC). The application serves as a mock analytical tool, showcasing a modern DevOps approach to building, deploying, and managing cloud-native applications.

The primary goal is to showcase expertise in **cloud infrastructure implementation**, **DevOps practices**, **CI/CD** (to be implemented), **containerization**, and **serverless architectures** on AWS.

## **Features Demonstrated (So Far)**

- **Infrastructure as Code (IaC):** AWS CDK (Python) defines and provisions all AWS resources.
- **Containerization:** Python Flask app containerized using Docker.
- **AWS Fargate:** Serverless compute for containers hosting the app.
- **Application Load Balancer (ALB):** Distributes traffic to Fargate tasks.
- **Amazon ECR:** Stores Docker image via CDK’s `from_asset`.
- **Amazon VPC:** Custom VPC setup.
- **AWS IAM:** Roles and permissions via CDK.
- **Scalable Architecture:** Resilient and cloud-native design.

## **Architecture**

The Flask backend is containerized with Docker and deployed as a **Fargate service** within a **custom VPC**, fronted by an **ALB**. All infrastructure is managed by **AWS CDK**.

### **AWS Services Used**

- Amazon ECS (Fargate)
- Application Load Balancer (ALB)
- Amazon ECR
- Amazon VPC
- AWS IAM
- AWS CloudFormation (via CDK)
- Amazon CloudWatch

### **Diagram (Mermaid Syntax)**

---

## **Project Structure**

```
serverless-analytical-app/
├── .github/
│   └── workflows/
│       └── main.yml          # CI/CD deployment workflow
├── application/              # Source for the Analytical App
│   ├── app.py
│   └── requirements.txt
├── reporting_app/            # Source for the Reporting App
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── infrastructure/           # AWS CDK IaC code
│   ├── app.py
│   ├── infrastructure_stack.py # Defines all cloud resources
│   └── requirements.txt
├── Dockerfile                # Dockerfile for the Analytical App
└── README.md                 # This file

```

---

## **Prerequisites**

- Python (3.9+)
- Node.js (Latest LTS recommended)
- AWS CDK Toolkit (`npm install -g aws-cdk`)
- AWS CLI (configured)
- Docker
- Git

---

## **Setup and Local Development**

### **Clone Repository**

```bash
git clone <your-repository-url>
cd serverless-analytical-app
```

### **Create Virtual Environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### **Install Flask App Dependencies**

```bash
pip install -r application/requirements.txt
```

### **Run Flask Locally**

```bash
cd application
python app.py
```

> Access via: http://127.0.0.1:5000

---

### **Run Docker Locally**

```bash
cd .. # Project root
docker build -t stockland-app .
docker run -p 5001:8000 --rm stockland-app
```

> Access via: http://127.0.0.1:5001

---

## **Cloud Deployment with AWS CDK**

### **Activate Environment**

```bash
source .venv/bin/activate
```

### **Install CDK Dependencies**

```bash
cd infrastructure
pip install -r requirements.txt
```

### **Configure AWS**

```bash
aws configure
```

> Enter Access Key, Secret, Region (e.g., `us-east-1`), and output format.

---

### **CDK Bootstrap (One-Time)**

```bash
cdk bootstrap aws://ACCOUNT_ID/REGION
# Example:
cdk bootstrap aws://123456789012/us-east-1
```

---

### **Synthesize CloudFormation Template**

```bash
cdk synth
```

---

### **Deploy to AWS**

```bash
cdk deploy
```

> Approve IAM changes if prompted.

---

### **Access Deployed App**

After deployment, CDK outputs the ALB DNS:

```text
http://<your-load-balancer-dns>
```

---

### **Tear Down Infrastructure**

```bash
cdk destroy
```

---

## **Key Files**

- `Dockerfile`: Flask image build and Gunicorn runner.
- `application/app.py`: Main Flask app with endpoints, defining API endpoints and serving mock analytical data.
- `infrastructure/infrastructure_stack.py`: CDK-defined AWS infra.
- `infrastructure/app.py`: CDK app entry point.
- `infrastructure/cdk.json`: CDK execution config.

---

## **Future Enhancements**

### **Phase 5: Add PostgreSQL Database**

- Integrate AWS RDS PostgreSQL.
- Connect Flask to RDS.

### **Phase 6: Implement CI/CD Pipeline**

- Automate test, build, and deploy with GitHub Actions.
### ⚙️ CI/CD Pipeline (GitHub Actions)
🔁 Trigger
Automatically runs on push to main branch.

### 🔐 Authentication
- Uses OIDC to assume IAM role.
- No AWS secrets stored in GitHub.

## 📋 Steps
Checkout repository
Setup Node.js and Python
Authenticate to AWS via OIDC
Install dependencies
Build and deploy using cdk synth + cdk deploy

### 🛡️ Setup for CI/CD
1. Create OIDC Provider in AWS IAM
URL: https://token.actions.githubusercontent.com

Audience: sts.amazonaws.com

2. Create IAM Role for GitHub Actions
Trusts the OIDC provider

# Permissions:

- sts:AssumeRole
- iam:PassRole
- Admin or least-privileged access for CDK resources

### 3. GitHub Repository Secrets
# Add the following secrets:

- AWS_ACCOUNT_ID
- AWS_REGION
- AWS_OIDC_ROLE_NAME

# 🔑 Key Files
- `.github/workflows/main.yml` — GitHub Actions pipeline
- `Dockerfile` — Flask Docker build
- `application/app.py` — Flask backend logic
- `infrastructure/infrastructure_stack.py` — CDK stack logic

### Serverless Multi-Service Web App with AWS CDK
- * Overview
This project demonstrates a multi-service architecture on AWS, featuring two independent Python Flask applications deployed as containers on AWS Fargate. The entire infrastructure is defined using the AWS Cloud Development Kit (CDK) for Infrastructure as Code (IaC).

The architecture includes:

An Analytical App providing core API functionalities.

A Reporting App that provides summary data.

Both services are served by a single, shared Application Load Balancer (ALB) using path-based routing. They connect to a shared AWS RDS PostgreSQL database with credentials securely managed by AWS Secrets Manager. The entire deployment process is automated via a CI/CD pipeline using GitHub Actions.

This project showcases expertise in designing and managing scalable microservice-style architectures, advanced cloud networking, IaC, CI/CD automation, and secure data management.

Features Implemented
Infrastructure as Code (IaC): AWS CDK (Python) defines all AWS resources.

Containerization: Two separate Python Flask apps, each containerized with Docker.

AWS Fargate: Serverless compute hosting both microservices.

Shared Application Load Balancer (ALB): Uses path-based routing (/api/*, /reporting/*, etc.) to direct traffic to the correct backend service from a single endpoint.

Amazon RDS for PostgreSQL: A single managed database instance shared securely by both services.

AWS Secrets Manager: Securely stores and manages the shared database credentials.

Amazon VPC: A custom VPC for secure networking of all resources.

AWS IAM & OIDC: Granular IAM roles per service and secure, keyless OIDC authentication for the CI/CD pipeline.

Continuous Integration/Continuous Deployment (CI/CD): An automated GitHub Actions pipeline deploys all infrastructure and application updates.

### Architecture
This multi-service architecture uses a shared Application Load Balancer to act as a single ingress point. The listener on the ALB inspects the URL path of incoming requests and forwards them to the appropriate backend Fargate service based on a set of priority-based rules. For example, requests to /api/* are routed to the Analytical App, while requests to /reporting/* are routed to the Reporting App. This is a cost-effective and common pattern for microservices. Both services run in private subnets and connect securely to the shared RDS instance, fetching credentials from Secrets Manager at runtime.

### Setup and Deployment
Setup and deployment steps remain similar, but the outcome is now two services running behind one load balancer. The CI/CD pipeline handles the deployment of both applications and the shared infrastructure.

Why use ["/reporting", "/reporting/*"] in the ALB Listener Rule?
When configuring path-based routing, it's important to be explicit.

The "/reporting/*" pattern matches any request that has something after /reporting/, like /reporting/property-summary.

However, it does not match a request to the base path /reporting itself.

By providing a list of patterns, ["/reporting", "/reporting/*"], we configure the ALB listener rule to match both the exact path and any sub-paths, ensuring all requests intended for the reporting service are routed correctly. This was a key fix to ensure the service's base URL was accessible.

Future Enhancements
Advanced CI/CD: Implement PR validation workflows with linting, unit tests, and security scanning.

Observability: Create service-specific CloudWatch Dashboards and alarms.

Security Hardening: Refine IAM permissions to strict least privilege and integrate AWS WAF.

Database Migrations: Integrate a tool like Alembic to manage schema changes in an automated fashion, which becomes critical in a multi-service, shared-database environment.