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
├── .venv/                    # Python virtual environment
├── application/              # Flask app code
│   ├── app.py                # Main Flask logic
│   └── requirements.txt      # Flask dependencies
├── infrastructure/           # AWS CDK IaC code
│   ├── app.py                # CDK entry point
│   ├── cdk.json              # CDK configuration
│   ├── infrastructure_stack.py # CDK stack definition
│   └── requirements.txt      # CDK Python dependencies
├── .dockerignore             # Docker ignore file
├── .gitignore                # Git ignore file
├── Dockerfile                # Builds Flask Docker image
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

